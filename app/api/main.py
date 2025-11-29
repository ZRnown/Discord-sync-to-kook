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
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
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
                created_at INTEGER,
                updated_at INTEGER
            )
            """
        )
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

# API路由
@app.post("/api/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """用户登录"""
    con = sqlite3.connect(USER_DB_PATH)
    try:
        cur = con.execute(
            "SELECT id, password_hash FROM users WHERE username=?",
            (request.username,)
        )
        row = cur.fetchone()
        if not row:
            return LoginResponse(success=False, message="用户名或密码错误")
        
        user_id, password_hash = row
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
        
        return LoginResponse(success=True, token=token)
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
            
            # 获取带单员信息
            trader = trader_config.get_trader_by_id(trader_id) if trader_id else None
            channel_name = trader['name'] if trader else ch_id
            
            # 如果没有状态，计算默认状态
            if not status:
                status = "未进场"
            
            # 如果交易已结束，不再更新价格和重新计算（保持最终状态）
            if is_ended:
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
                    pnl_points=float(pnl_points) if pnl_points else None,
                    pnl_percent=float(pnl_percent) if pnl_percent else None,
                    confidence=float(confidence) if confidence else None,
                    created_at=created_at,
                    created_at_str=created_at_str
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

