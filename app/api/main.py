"""
FastAPI 后端服务
提供交易数据API和用户认证API
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List, Dict
import sqlite3
import hashlib
import secrets
import time
from datetime import datetime, timedelta
import os

from app.config.settings import get_settings
from app.config.trader_config import TraderConfig
from app.services.okx.state_cache import OKXStateCache
from app.services.membership.store import MembershipStore

app = FastAPI(title="交易监控API", version="1.0.0")

# CORS配置
# 从环境变量读取允许的源，如果没有则使用默认值
import os
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:3001").split(",")
# 清理空格
cors_origins = [origin.strip() for origin in cors_origins if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 安全配置
security = HTTPBearer()
settings = get_settings()
trader_config = TraderConfig()
store = MembershipStore()
okx_cache = OKXStateCache()
okx_cache.start()

# 用户认证相关
USER_DB_PATH = os.path.join(os.path.dirname(store.db_path), "users.db")

def init_user_db():
    """初始化用户数据库"""
    # 确保数据库目录存在
    db_dir = os.path.dirname(USER_DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    con = sqlite3.connect(USER_DB_PATH)
    try:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'user',
                note TEXT,
                created_at INTEGER,
                updated_at INTEGER
            )
            """
        )
        # 添加role字段（如果表已存在但没有该字段）
        try:
            con.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
            # 为现有用户设置默认角色
            con.execute("UPDATE users SET role='user' WHERE role IS NULL")
            con.commit()
        except sqlite3.OperationalError:
            # 字段已存在，但确保所有用户都有 role
            con.execute("UPDATE users SET role='user' WHERE role IS NULL")
            con.commit()
        # 添加note字段（如果表已存在但没有该字段）
        try:
            con.execute("ALTER TABLE users ADD COLUMN note TEXT")
            con.commit()
        except sqlite3.OperationalError:
            pass  # 字段已存在
        
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                expires_at INTEGER NOT NULL,
                created_at INTEGER,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )
        con.commit()
    finally:
        con.close()

# 初始化数据库
init_user_db()

# 密码哈希
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash

# 请求/响应模型
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    success: bool
    token: Optional[str] = None
    message: Optional[str] = None
    role: Optional[str] = None

class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class TradeResponse(BaseModel):
    id: int
    trader_id: Optional[str]
    channel_id: str
    channel_name: str
    symbol: str
    side: str
    entry_price: float
    take_profit: float
    stop_loss: float
    current_price: Optional[float]
    status: str
    pnl_points: Optional[float]
    pnl_percent: Optional[float]
    confidence: Optional[float]
    created_at: int
    created_at_str: str
    exited_pnl_points: Optional[float] = None  # 已出局部分的盈亏（用于部分出局）
    remaining_pnl_points: Optional[float] = None  # 剩余部分的盈亏（用于部分出局）

class TradesResponse(BaseModel):
    success: bool
    data: List[TradeResponse]

class TradeDetailResponse(BaseModel):
    success: bool
    data: TradeResponse
    updates: List[Dict] = []

# 认证依赖
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    con = sqlite3.connect(USER_DB_PATH)
    try:
        cur = con.execute(
            "SELECT user_id, expires_at FROM sessions WHERE token=?",
            (token,)
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="无效的token")
        user_id, expires_at = row
        if expires_at < int(time.time()):
            raise HTTPException(status_code=401, detail="token已过期")
        return user_id
    finally:
        con.close()

async def get_current_user_with_role(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """获取当前用户信息（包括角色）"""
    token = credentials.credentials
    con = sqlite3.connect(USER_DB_PATH)
    try:
        cur = con.execute(
            """
            SELECT s.user_id, s.expires_at, u.role
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.token=?
            """,
            (token,)
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="无效的token")
        user_id, expires_at, role = row
        if expires_at < int(time.time()):
            raise HTTPException(status_code=401, detail="token已过期")
        return {"user_id": user_id, "role": role}
    finally:
        con.close()

async def require_admin(user_info: dict = Depends(get_current_user_with_role)):
    """要求管理员权限"""
    if user_info["role"] != "admin":
        raise HTTPException(status_code=403, detail="需要管理员权限")
    return user_info

# API路由
@app.post("/api/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """用户登录"""
    con = sqlite3.connect(USER_DB_PATH)
    try:
        # 先尝试查询包含 role 字段
        cur = con.execute(
            "SELECT id, password_hash, COALESCE(role, 'user') as role FROM users WHERE username=?",
            (request.username,)
        )
        row = cur.fetchone()
        if not row:
            return LoginResponse(success=False, message="用户名或密码错误")
        
        user_id, password_hash, role = row
        
        # 如果 role 为 None，设置为默认值 'user'
        if role is None:
            role = 'user'
            # 更新数据库中的 role 字段
            con.execute(
                "UPDATE users SET role=? WHERE id=?",
                (role, user_id)
            )
            con.commit()
        
        if not verify_password(request.password, password_hash):
            return LoginResponse(success=False, message="用户名或密码错误")
        
        # 生成token
        token = secrets.token_urlsafe(32)
        expires_at = int(time.time()) + 7 * 24 * 3600  # 7天有效期
        now = int(time.time())
        
        con.execute(
            "INSERT INTO sessions(token, user_id, expires_at, created_at) VALUES(?,?,?,?)",
            (token, user_id, expires_at, now)
        )
        con.commit()
        
        return LoginResponse(success=True, token=token, role=role or 'user')
    except Exception as e:
        print(f"[Login] 登录异常: {e}")
        import traceback
        traceback.print_exc()
        return LoginResponse(success=False, message=f"登录失败: {str(e)}")
    finally:
        con.close()

@app.post("/api/auth/logout")
async def logout(user_id: int = Depends(get_current_user)):
    """用户登出"""
    # 这里可以删除token，但为了简单，我们只返回成功
    return {"success": True, "message": "登出成功"}

@app.post("/api/auth/change-password")
async def change_password(request: ChangePasswordRequest, user_id: int = Depends(get_current_user)):
    """修改密码"""
    con = sqlite3.connect(USER_DB_PATH)
    try:
        cur = con.execute(
            "SELECT password_hash FROM users WHERE id=?",
            (user_id,)
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        old_password_hash = row[0]
        if not verify_password(request.old_password, old_password_hash):
            raise HTTPException(status_code=400, detail="原密码错误")
        
        new_password_hash = hash_password(request.new_password)
        now = int(time.time())
        con.execute(
            "UPDATE users SET password_hash=?, updated_at=? WHERE id=?",
            (new_password_hash, now, user_id)
        )
        con.commit()
        
        return {"success": True, "message": "密码修改成功"}
    finally:
        con.close()

@app.get("/api/trades", response_model=TradesResponse)
async def get_trades(
    channel_id: Optional[str] = None, 
    trader_id: Optional[str] = None,
    user_id: int = Depends(get_current_user)
):
    """获取交易单列表
    
    参数:
    - channel_id: 通过Discord频道ID过滤
    - trader_id: 通过带单员ID过滤（例如: trader1）
    """
    con = sqlite3.connect(store.db_path)
    try:
        # 确保表存在
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS trades (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trader_id TEXT,
                source_message_id TEXT,
                channel_id TEXT,
                user_id TEXT,
                symbol TEXT,
                side TEXT,
                entry_price REAL,
                take_profit REAL,
                stop_loss REAL,
                confidence REAL,
                created_at INTEGER
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS trade_status_detail (
                trade_id INTEGER PRIMARY KEY,
                status TEXT,
                pnl_points REAL,
                pnl_percent REAL,
                current_price REAL,
                updated_at INTEGER
            )
            """
        )
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS trade_updates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trader_id TEXT,
                trade_ref_id INTEGER,
                source_message_id TEXT,
                channel_id TEXT,
                user_id TEXT,
                text TEXT,
                pnl_points REAL,
                status TEXT,
                created_at INTEGER
            )
            """
        )
        con.commit()
        
        query = """
            SELECT t.id, t.trader_id, t.channel_id, t.symbol, t.side, 
                   t.entry_price, t.take_profit, t.stop_loss, t.confidence, t.created_at,
                   ts.status, ts.pnl_points, ts.pnl_percent, ts.current_price
            FROM trades t
            LEFT JOIN trade_status_detail ts ON t.id = ts.trade_id
        """
        params = []
        conditions = []
        if channel_id:
            conditions.append("t.channel_id = ?")
            params.append(channel_id)
        if trader_id:
            conditions.append("t.trader_id = ?")
            params.append(trader_id)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY t.created_at DESC"
        
        cur = con.execute(query, params)
        rows = cur.fetchall()
        
        trades = []
        for row in rows:
            (trade_id, trader_id, ch_id, symbol, side, entry_price, take_profit, 
             stop_loss, confidence, created_at, status, pnl_points, pnl_percent, current_price) = row
            
            # 检查是否有部分出局的更新记录
            partial_exit = con.execute(
                """
                SELECT status, pnl_points, created_at FROM trade_updates 
                WHERE trade_ref_id=? 
                AND (status LIKE '%部分%' OR status LIKE '%部分出局%')
                ORDER BY created_at DESC LIMIT 1
                """,
                (trade_id,)
            ).fetchone()
            
            # 检查是否有最新的更新状态（已止盈/止损等）
            latest_update = con.execute(
                """
                SELECT status, pnl_points FROM trade_updates 
                WHERE trade_ref_id=? 
                AND status IN ('已止盈', '已止损', '带单主动止盈', '带单主动止损')
                ORDER BY created_at DESC LIMIT 1
                """,
                (trade_id,)
            ).fetchone()
            
            # 判断交易是否已结束
            is_ended = False
            exited_pnl = None  # 已出局部分的盈亏
            if latest_update:
                status = latest_update[0]
                is_ended = True
                if latest_update[1]:
                    pnl_points = float(latest_update[1])
                    # 重新计算盈亏百分比（基于最终盈亏点数）
                    if entry_price and entry_price > 0:
                        pnl_percent = (pnl_points / entry_price) * 100
            elif status and status in ['已止盈', '已止损', '带单主动止盈', '带单主动止损']:
                is_ended = True
            elif partial_exit:
                # 部分出局：显示已出局部分的盈亏
                exited_pnl = float(partial_exit[1]) if partial_exit[1] else None
                # 状态保持为部分出局，但需要显示已出局和剩余部分的盈亏
                status = partial_exit[0]  # 使用部分出局的状态
            
            # 获取带单员信息
            trader = trader_config.get_trader_by_id(trader_id) if trader_id else None
            channel_name = trader['name'] if trader else ch_id
            
            # 如果没有状态，计算默认状态
            if not status:
                status = "未进场"
            
            # 如果是"待入场"状态，尝试获取当前价格用于显示，但不重新计算状态
            if status == "待入场":
                # 待入场状态：只获取价格用于显示，不计算盈亏
                if not current_price and symbol:
                    price = okx_cache.get_price(symbol)
                    if price:
                        current_price = float(price)
                # 待入场状态时，清空盈亏数据
                pnl_points = None
                pnl_percent = None
            # 如果交易已结束，不再更新价格和重新计算（保持最终状态）
            elif is_ended:
                # 已结束的交易，不再获取实时价格，使用已保存的最终价格
                # 如果trade_status_detail中有价格，使用它；否则使用entry_price作为显示
                if not current_price:
                    current_price = entry_price  # 使用进场价作为显示，不再实时更新
            elif not current_price and symbol:
                # 如果交易未结束，尝试从OKX获取当前价格用于计算
                price = okx_cache.get_price(symbol)
                if price:
                    current_price = float(price)
            
            created_at_str = datetime.fromtimestamp(created_at).strftime("%Y-%m-%d %H:%M:%S")
            
            try:
                    # 如果是"待入场"状态，不计算盈亏
                    if status == "待入场":
                        final_pnl_points = None
                        final_pnl_percent = None
                        exited_pnl_points = None
                        remaining_pnl_points = None
                    # 如果是部分出局，计算并显示已出局和剩余部分的盈亏
                    elif partial_exit and exited_pnl is not None:
                        # 如果是部分出局，pnl_points 是剩余部分的盈亏，需要加上已出局部分的盈亏
                        # 剩余部分的盈亏已经在 pnl_points 中
                        # 已出局部分的盈亏在 exited_pnl 中
                        # 总盈亏 = 已出局 + 剩余部分
                        remaining_pnl = float(pnl_points) if pnl_points else 0
                        total_pnl = exited_pnl + remaining_pnl
                        total_pnl_percent = (total_pnl / entry_price) * 100 if entry_price and entry_price > 0 else 0
                        
                        # 设置已出局和剩余部分的盈亏
                        exited_pnl_points = exited_pnl
                        remaining_pnl_points = remaining_pnl
                        
                        # 总盈亏显示在 pnl_points 中
                        final_pnl_points = total_pnl
                        final_pnl_percent = total_pnl_percent
                    else:
                        # 正常情况：使用数据库中的盈亏数据
                        final_pnl_points = pnl_points
                        final_pnl_percent = pnl_percent
                        exited_pnl_points = None
                        remaining_pnl_points = None
                    
                    trades.append(TradeResponse(
                        id=trade_id,
                        trader_id=trader_id,
                        channel_id=ch_id,
                        channel_name=channel_name,
                        symbol=symbol or "",
                        side=side or "",
                        entry_price=float(entry_price) if entry_price else 0,
                        take_profit=float(take_profit) if take_profit else 0,
                        stop_loss=float(stop_loss) if stop_loss else 0,
                        current_price=float(current_price) if current_price else None,
                        status=status or "未进场",
                        pnl_points=float(final_pnl_points) if final_pnl_points else None,
                        pnl_percent=float(final_pnl_percent) if final_pnl_percent else None,
                        confidence=float(confidence) if confidence else None,
                        created_at=created_at,
                        created_at_str=created_at_str,
                        exited_pnl_points=exited_pnl_points,
                        remaining_pnl_points=remaining_pnl_points
                    ))
            except Exception as e:
                print(f"处理交易单 {trade_id} 时出错: {e}")
                continue
        
        return TradesResponse(success=True, data=trades)
    except Exception as e:
        print(f"获取交易单列表异常: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取交易单列表失败: {str(e)}")
    finally:
        con.close()

@app.get("/api/traders")
async def get_traders(user_id: int = Depends(get_current_user)):
    """获取带单员列表"""
    traders = trader_config.get_all_traders()
    return {
        "success": True,
        "data": [
            {
                "id": t["id"],
                "name": t["name"],
                "channel_id": t["channel_id"],
                "channel_name": t["name"],
            }
            for t in traders
        ]
    }

@app.get("/api/trades/{trade_id}", response_model=TradeDetailResponse)
async def get_trade_detail(trade_id: int, user_id: int = Depends(get_current_user)):
    """获取单个交易单的详细信息（包括所有更新记录）"""
    con = sqlite3.connect(store.db_path)
    try:
        # 获取交易单基本信息
        cur = con.execute(
            """
            SELECT t.id, t.trader_id, t.channel_id, t.symbol, t.side, 
                   t.entry_price, t.take_profit, t.stop_loss, t.confidence, t.created_at,
                   ts.status, ts.pnl_points, ts.pnl_percent, ts.current_price
            FROM trades t
            LEFT JOIN trade_status_detail ts ON t.id = ts.trade_id
            WHERE t.id = ?
            """,
            (trade_id,)
        )
        row = cur.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="交易单不存在")
        
        (trade_id, trader_id, ch_id, symbol, side, entry_price, take_profit, 
         stop_loss, confidence, created_at, status, pnl_points, pnl_percent, current_price) = row
        
        # 获取所有更新记录
        updates_cur = con.execute(
            """
            SELECT id, text, status, pnl_points, created_at
            FROM trade_updates
            WHERE trade_ref_id = ?
            ORDER BY created_at DESC
            """,
            (trade_id,)
        )
        updates = []
        for update_row in updates_cur.fetchall():
            update_id, text, update_status, update_pnl, update_created_at = update_row
            updates.append({
                "id": update_id,
                "text": text or "",
                "status": update_status or "",
                "pnl_points": float(update_pnl) if update_pnl else None,
                "created_at": update_created_at,
                "created_at_str": datetime.fromtimestamp(update_created_at).strftime("%Y-%m-%d %H:%M:%S") if update_created_at else ""
            })
        
        # 获取带单员信息
        trader = trader_config.get_trader_by_id(trader_id) if trader_id else None
        channel_name = trader['name'] if trader else ch_id
        
        # 如果没有状态，计算默认状态
        if not status:
            status = "未进场"
        
        # 如果没有当前价格，尝试从OKX获取
        if not current_price and symbol:
            price = okx_cache.get_price(symbol)
            if price:
                current_price = float(price)
        
        created_at_str = datetime.fromtimestamp(created_at).strftime("%Y-%m-%d %H:%M:%S")
        
        trade_data = TradeResponse(
            id=trade_id,
            trader_id=trader_id,
            channel_id=ch_id,
            channel_name=channel_name,
            symbol=symbol or "",
            side=side or "",
            entry_price=float(entry_price) if entry_price else 0,
            take_profit=float(take_profit) if take_profit else 0,
            stop_loss=float(stop_loss) if stop_loss else 0,
            current_price=float(current_price) if current_price else None,
            status=status or "未进场",
            pnl_points=float(pnl_points) if pnl_points else None,
            pnl_percent=float(pnl_percent) if pnl_percent else None,
            confidence=float(confidence) if confidence else None,
            created_at=created_at,
            created_at_str=created_at_str
        )
        
        return TradeDetailResponse(success=True, data=trade_data, updates=updates)
    except HTTPException:
        raise
    except Exception as e:
        print(f"获取交易单详情异常: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取交易单详情失败: {str(e)}")
    finally:
        con.close()

@app.get("/api/prices")
async def get_prices(user_id: int = Depends(get_current_user)):
    """获取实时价格"""
    prices = {}
    for inst_id in settings.OKX_INST_IDS:
        price = okx_cache.get_price(inst_id)
        if price:
            prices[inst_id] = float(price)
    return {"success": True, "data": prices}

@app.delete("/api/trades/{trade_id}")
async def delete_trade(trade_id: int, user_info: dict = Depends(require_admin)):
    """删除指定的交易单（包括相关的更新记录和状态记录）- 仅管理员"""
    con = sqlite3.connect(store.db_path)
    try:
        # 检查交易单是否存在
        cur = con.execute("SELECT id FROM trades WHERE id=?", (trade_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="交易单不存在")
        
        # 删除相关的更新记录
        con.execute("DELETE FROM trade_updates WHERE trade_ref_id=?", (trade_id,))
        
        # 删除状态记录
        con.execute("DELETE FROM trade_status_detail WHERE trade_id=?", (trade_id,))
        
        # 删除交易单
        con.execute("DELETE FROM trades WHERE id=?", (trade_id,))
        
        con.commit()
        print(f'[API] ✅ 用户 {user_info["user_id"]} 删除了交易单 {trade_id}')
        return {"success": True, "message": "交易单已删除"}
    except HTTPException:
        raise
    except Exception as e:
        con.rollback()
        print(f'[API] ❌ 删除交易单失败: {e}')
        raise HTTPException(status_code=500, detail=f"删除交易单失败: {str(e)}")
    finally:
        con.close()

@app.post("/api/trades/{trade_id}/close")
async def close_trade(trade_id: int, user_info: dict = Depends(require_admin)):
    """手动结单：将活跃交易单标记为已结束 - 仅管理员"""
    con = sqlite3.connect(store.db_path)
    try:
        # 获取交易单信息
        cur = con.execute(
            """
            SELECT t.id, t.symbol, t.side, t.entry_price, t.take_profit, t.stop_loss,
                   ts.status, ts.current_price
            FROM trades t
            LEFT JOIN trade_status_detail ts ON t.id = ts.trade_id
            WHERE t.id = ?
            """,
            (trade_id,)
        )
        row = cur.fetchone()
        
        if not row:
            raise HTTPException(status_code=404, detail="交易单不存在")
        
        (trade_id, symbol, side, entry_price, take_profit, stop_loss, 
         current_status, current_price) = row
        
        # 检查是否已经结束
        ended_statuses = ['已止盈', '已止损', '带单主动止盈', '带单主动止损']
        if current_status and current_status in ended_statuses:
            raise HTTPException(status_code=400, detail="交易单已经结束，无法再次结单")
        
        # 获取当前价格
        if not current_price:
            # 从OKX缓存获取当前价格
            current_price = okx_cache.get_price(symbol)
            if not current_price:
                raise HTTPException(status_code=500, detail="无法获取当前价格，请稍后重试")
        
        # 计算盈亏
        if side == "long":
            pnl_points = current_price - entry_price
        else:  # short
            pnl_points = entry_price - current_price
        
        pnl_percent = (pnl_points / entry_price) * 100 if entry_price > 0 else 0
        
        # 根据盈亏判断状态
        if pnl_points >= 0:
            final_status = "带单主动止盈"
        else:
            final_status = "带单主动止损"
        
        now = int(time.time())
        
        # 更新交易状态
        con.execute(
            """
            INSERT INTO trade_status_detail(trade_id, status, pnl_points, pnl_percent, current_price, updated_at)
            VALUES(?,?,?,?,?,?)
            ON CONFLICT(trade_id) DO UPDATE SET
                status=excluded.status,
                pnl_points=excluded.pnl_points,
                pnl_percent=excluded.pnl_percent,
                current_price=excluded.current_price,
                updated_at=excluded.updated_at
            """,
            (trade_id, final_status, round(pnl_points, 2), round(pnl_percent, 2), current_price, now)
        )
        
        # 可选：在trade_updates表中记录手动结单操作
        con.execute(
            """
            INSERT INTO trade_updates(trader_id, trade_ref_id, channel_id, text, status, pnl_points, created_at)
            VALUES(?,?,?,?,?,?,?)
            """,
            (None, trade_id, None, f"手动结单 - {final_status}", final_status, round(pnl_points, 2), now)
        )
        
        con.commit()
        print(f'[API] ✅ 用户 {user_info["user_id"]} 手动结单 {trade_id}: {final_status}, 盈亏: {round(pnl_points, 2)}点')
        return {
            "success": True, 
            "message": f"交易单已结单: {final_status}",
            "status": final_status,
            "pnl_points": round(pnl_points, 2),
            "pnl_percent": round(pnl_percent, 2)
        }
    except HTTPException:
        raise
    except Exception as e:
        con.rollback()
        print(f'[API] ❌ 手动结单失败: {e}')
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"手动结单失败: {str(e)}")
    finally:
        con.close()

# 用户管理API（仅管理员）
class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = "user"  # 默认为普通用户
    note: Optional[str] = None

class UpdateUserRequest(BaseModel):
    username: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = None
    note: Optional[str] = None

class UserResponse(BaseModel):
    id: int
    username: str
    role: str
    note: Optional[str] = None
    created_at: int
    updated_at: Optional[int]

class BatchDeleteRequest(BaseModel):
    user_ids: List[int]

class UsersResponse(BaseModel):
    success: bool
    data: List[UserResponse]

@app.get("/api/users", response_model=UsersResponse)
async def get_users(user_info: dict = Depends(require_admin)):
    """获取所有用户列表 - 仅管理员"""
    con = sqlite3.connect(USER_DB_PATH)
    try:
        cur = con.execute(
            "SELECT id, username, role, note, created_at, updated_at FROM users ORDER BY id DESC"
        )
        users = []
        for row in cur.fetchall():
            user_id, username, role, note, created_at, updated_at = row
            users.append(UserResponse(
                id=user_id,
                username=username,
                role=role or "user",
                note=note,
                created_at=created_at or 0,
                updated_at=updated_at
            ))
        return UsersResponse(success=True, data=users)
    finally:
        con.close()

@app.post("/api/users", response_model=UserResponse)
async def create_user(request: CreateUserRequest, user_info: dict = Depends(require_admin)):
    """创建新用户 - 仅管理员"""
    if request.role not in ["admin", "user"]:
        raise HTTPException(status_code=400, detail="角色必须是 'admin' 或 'user'")
    
    con = sqlite3.connect(USER_DB_PATH)
    try:
        # 检查用户名是否已存在
        cur = con.execute("SELECT id FROM users WHERE username=?", (request.username,))
        if cur.fetchone():
            raise HTTPException(status_code=400, detail="用户名已存在")
        
        # 创建用户
        now = int(time.time())
        password_hash = hash_password(request.password)
        cur = con.execute(
            "INSERT INTO users(username, password_hash, role, note, created_at, updated_at) VALUES(?,?,?,?,?,?)",
            (request.username, password_hash, request.role, request.note, now, now)
        )
        con.commit()
        
        user_id = cur.lastrowid
        return UserResponse(
            id=user_id,
            username=request.username,
            role=request.role,
            note=request.note,
            created_at=now,
            updated_at=now
        )
    except HTTPException:
        raise
    except Exception as e:
        con.rollback()
        raise HTTPException(status_code=500, detail=f"创建用户失败: {str(e)}")
    finally:
        con.close()

@app.put("/api/users/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, request: UpdateUserRequest, user_info: dict = Depends(require_admin)):
    """更新用户信息 - 仅管理员"""
    if request.role and request.role not in ["admin", "user"]:
        raise HTTPException(status_code=400, detail="角色必须是 'admin' 或 'user'")
    
    con = sqlite3.connect(USER_DB_PATH)
    try:
        # 检查用户是否存在
        cur = con.execute("SELECT id, username, role FROM users WHERE id=?", (user_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 构建更新语句
        updates = []
        params = []
        
        if request.username:
            # 检查新用户名是否已被其他用户使用
            check_cur = con.execute("SELECT id FROM users WHERE username=? AND id!=?", (request.username, user_id))
            if check_cur.fetchone():
                raise HTTPException(status_code=400, detail="用户名已被使用")
            updates.append("username=?")
            params.append(request.username)
        
        if request.password:
            password_hash = hash_password(request.password)
            updates.append("password_hash=?")
            params.append(password_hash)
        
        if request.role:
            updates.append("role=?")
            params.append(request.role)
        
        if request.note is not None:  # 允许设置为空字符串
            updates.append("note=?")
            params.append(request.note)
        
        if not updates:
            raise HTTPException(status_code=400, detail="没有要更新的字段")
        
        updates.append("updated_at=?")
        params.append(int(time.time()))
        params.append(user_id)
        
        con.execute(
            f"UPDATE users SET {', '.join(updates)} WHERE id=?",
            params
        )
        con.commit()
        
        # 返回更新后的用户信息
        cur = con.execute("SELECT id, username, role, note, created_at, updated_at FROM users WHERE id=?", (user_id,))
        row = cur.fetchone()
        return UserResponse(
            id=row[0],
            username=row[1],
            role=row[2] or "user",
            note=row[3],
            created_at=row[4] or 0,
            updated_at=row[5]
        )
    except HTTPException:
        raise
    except Exception as e:
        con.rollback()
        raise HTTPException(status_code=500, detail=f"更新用户失败: {str(e)}")
    finally:
        con.close()

@app.delete("/api/users/{user_id}")
async def delete_user(user_id: int, user_info: dict = Depends(require_admin)):
    """删除用户 - 仅管理员"""
    # 不能删除自己
    if user_id == user_info["user_id"]:
        raise HTTPException(status_code=400, detail="不能删除自己的账户")
    
    con = sqlite3.connect(USER_DB_PATH)
    try:
        # 检查用户是否存在
        cur = con.execute("SELECT id FROM users WHERE id=?", (user_id,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="用户不存在")
        
        # 删除用户的所有会话
        con.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
        
        # 删除用户
        con.execute("DELETE FROM users WHERE id=?", (user_id,))
        con.commit()
        
        return {"success": True, "message": "用户已删除"}
    except HTTPException:
        raise
    except Exception as e:
        con.rollback()
        raise HTTPException(status_code=500, detail=f"删除用户失败: {str(e)}")
    finally:
        con.close()

@app.post("/api/users/batch-delete")
async def batch_delete_users(request: BatchDeleteRequest, user_info: dict = Depends(require_admin)):
    """批量删除用户 - 仅管理员"""
    if not request.user_ids:
        raise HTTPException(status_code=400, detail="请选择要删除的用户")
    
    # 不能删除自己
    if user_info["user_id"] in request.user_ids:
        raise HTTPException(status_code=400, detail="不能删除自己的账户")
    
    con = sqlite3.connect(USER_DB_PATH)
    try:
        # 检查所有用户是否存在
        placeholders = ",".join("?" * len(request.user_ids))
        cur = con.execute(f"SELECT id FROM users WHERE id IN ({placeholders})", request.user_ids)
        existing_ids = [row[0] for row in cur.fetchall()]
        
        if len(existing_ids) != len(request.user_ids):
            raise HTTPException(status_code=404, detail="部分用户不存在")
        
        # 删除用户的所有会话
        con.execute(f"DELETE FROM sessions WHERE user_id IN ({placeholders})", request.user_ids)
        
        # 删除用户
        con.execute(f"DELETE FROM users WHERE id IN ({placeholders})", request.user_ids)
        con.commit()
        
        return {"success": True, "message": f"已删除 {len(request.user_ids)} 个用户"}
    except HTTPException:
        raise
    except Exception as e:
        con.rollback()
        raise HTTPException(status_code=500, detail=f"批量删除用户失败: {str(e)}")
    finally:
        con.close()

@app.get("/api/users/{user_id}/password-info")
async def get_user_password_info(user_id: int, user_info: dict = Depends(require_admin)):
    """获取用户密码信息（用于显示提示）- 仅管理员"""
    con = sqlite3.connect(USER_DB_PATH)
    try:
        cur = con.execute(
            "SELECT password_hash FROM users WHERE id=?",
            (user_id,)
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        password_hash = row[0]
        # 返回密码哈希的前8位作为提示（不返回完整哈希）
        return {
            "success": True,
            "data": {
                "has_password": True,
                "password_hint": password_hash[:8] + "..." if password_hash else None
            }
        }
    finally:
        con.close()

@app.get("/api/auth/me")
async def get_current_user_info(user_info: dict = Depends(get_current_user_with_role)):
    """获取当前登录用户信息"""
    con = sqlite3.connect(USER_DB_PATH)
    try:
        cur = con.execute(
            "SELECT id, username, role, note, created_at FROM users WHERE id=?",
            (user_info["user_id"],)
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="用户不存在")
        
        return {
            "success": True,
            "data": {
                "id": row[0],
                "username": row[1],
                "role": row[2] or "user",
                "note": row[3],
                "created_at": row[4] or 0
            }
        }
    finally:
        con.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

