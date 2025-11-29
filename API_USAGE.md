# API 使用说明

## 带单员配置说明

### TRADER_CONFIG 格式

在 `.env` 文件中的 `TRADER_CONFIG` 配置格式：

```bash
TRADER_CONFIG=trader1|1438413966714994699|35E22983F436F55B|带单员1
```

**格式说明**：`带单员ID|Discord频道ID|OKX带单员uniqueCode|带单员名称`

**各部分含义**：
- `trader1`: **带单员ID** - 系统内部使用的唯一标识符，用于识别不同的带单员
- `1438413966714994699`: **Discord频道ID** - 要监控的Discord频道ID
- `35E22983F436F55B`: **OKX带单员uniqueCode** - 从OKX带单员主页链接中提取（例如：https://www.okx.com/zh-hans/copy-trading/account/35E22983F436F55B）
- `带单员1`: **带单员名称** - 在前端显示的名称

**多个带单员配置**（用分号分隔）：
```bash
TRADER_CONFIG=trader1|频道1|code1|带单员1;trader2|频道2|code2|带单员2
```

## API 端点

### 1. 获取交易单列表

**端点**: `GET /api/trades`

**参数**:
- `channel_id` (可选): 通过Discord频道ID过滤
- `trader_id` (可选): 通过带单员ID过滤（例如: `trader1`）

**示例**:
```bash
# 获取所有交易单
GET /api/trades

# 获取特定频道的交易单
GET /api/trades?channel_id=1438413966714994699

# 获取特定带单员的所有交易单
GET /api/trades?trader_id=trader1

# 组合查询
GET /api/trades?trader_id=trader1&channel_id=1438413966714994699
```

**响应**:
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "trader_id": "trader1",
      "channel_id": "1438413966714994699",
      "channel_name": "带单员1",
      "symbol": "BTC-USDT-SWAP",
      "side": "long",
      "entry_price": 50000.0,
      "take_profit": 52000.0,
      "stop_loss": 48000.0,
      "current_price": 51000.0,
      "status": "浮盈",
      "pnl_points": 1000.0,
      "pnl_percent": 2.0,
      "confidence": 0.9,
      "created_at": 1234567890,
      "created_at_str": "2024-01-01 12:00:00"
    }
  ]
}
```

### 2. 获取单个交易单详细信息

**端点**: `GET /api/trades/{trade_id}`

**示例**:
```bash
GET /api/trades/1
```

**响应**:
```json
{
  "success": true,
  "data": {
    "id": 1,
    "trader_id": "trader1",
    "channel_id": "1438413966714994699",
    "channel_name": "带单员1",
    "symbol": "BTC-USDT-SWAP",
    "side": "long",
    "entry_price": 50000.0,
    "take_profit": 52000.0,
    "stop_loss": 48000.0,
    "current_price": 51000.0,
    "status": "浮盈",
    "pnl_points": 1000.0,
    "pnl_percent": 2.0,
    "confidence": 0.9,
    "created_at": 1234567890,
    "created_at_str": "2024-01-01 12:00:00"
  },
  "updates": [
    {
      "id": 1,
      "text": "更新信息",
      "status": "浮盈",
      "pnl_points": 1000.0,
      "created_at": 1234567890,
      "created_at_str": "2024-01-01 12:00:00"
    }
  ]
}
```

### 3. 获取带单员列表

**端点**: `GET /api/traders`

**响应**:
```json
{
  "success": true,
  "data": [
    {
      "id": "trader1",
      "name": "带单员1",
      "channel_id": "1438413966714994699",
      "channel_name": "带单员1",
      "unique_code": "35E22983F436F55B"
    }
  ]
}
```

### 4. 获取实时价格

**端点**: `GET /api/prices`

**响应**:
```json
{
  "success": true,
  "data": {
    "BTC-USDT-SWAP": 50000.0,
    "ETH-USDT-SWAP": 3000.0
  }
}
```

## 认证

所有API都需要Bearer Token认证：

```bash
Authorization: Bearer <your_token>
```

获取token：先调用 `POST /api/auth/login` 登录接口。

## 使用示例

### 获取trader1的所有交易单

```bash
curl -X GET "http://localhost:8000/api/trades?trader_id=trader1" \
  -H "Authorization: Bearer <your_token>"
```

### 获取特定交易单的详细信息

```bash
curl -X GET "http://localhost:8000/api/trades/1" \
  -H "Authorization: Bearer <your_token>"
```

## 数据说明

### 交易单状态

- `未进场`: 尚未开仓
- `浮盈`: 当前盈利（显示盈亏点数）
- `浮亏`: 当前亏损（显示盈亏点数）
- `已止盈`: 触发止盈
- `已止损`: 触发止损
- `带单主动止盈`: 带单员手动平仓（盈利）
- `带单主动止损`: 带单员手动平仓（亏损）

### 数据来源

- **进场价格、止盈、止损**: 优先使用OKX API返回的实际数据
- **当前价格**: 从OKX实时价格API获取
- **状态计算**: 结合实时币价和OKX API持仓数据自动计算


