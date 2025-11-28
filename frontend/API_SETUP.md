# API 配置说明

## 环境变量配置

前端通过环境变量 `NEXT_PUBLIC_API_BASE_URL` 配置后端 API 地址。

### 开发环境

在项目根目录创建 `.env.local` 文件（已添加到 .gitignore）：

```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### 生产环境

在生产环境部署时，设置环境变量：

```bash
NEXT_PUBLIC_API_BASE_URL=https://your-backend-api.com
```

## API 端点

前端期望后端提供以下 API 端点：

### 1. GET /api/trades
获取交易单列表

**查询参数：**
- `channel_id` (可选): 频道 ID，用于筛选特定频道的交易单

**响应格式：**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "channel_id": "123456789",
      "channel_name": "BTC-USDT信号",
      "symbol": "BTC-USDT-SWAP",
      "side": "long",
      "entry_price": 45000.5,
      "take_profit": 46000.0,
      "stop_loss": 44000.0,
      "current_price": 45200.0,
      "status": "浮盈",
      "pnl_points": 199.5,
      "pnl_percent": 0.44,
      "created_at": 1704067200,
      "created_at_str": "2024-01-01 12:00:00",
      "updated_at": 1704067500
    }
  ]
}
```

### 2. GET /api/trades/{id}
获取单个交易单详情

**响应格式：**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "channel_id": "123456789",
    "channel_name": "BTC-USDT信号",
    "symbol": "BTC-USDT-SWAP",
    "side": "long",
    "entry_price": 45000.5,
    "take_profit": 46000.0,
    "stop_loss": 44000.0,
    "current_price": 45200.0,
    "status": "浮盈",
    "pnl_points": 199.5,
    "pnl_percent": 0.44,
    "created_at": 1704067200,
    "updates": [
      {
        "id": 1,
        "text": "部分止盈",
        "status": "部分止盈",
        "pnl_points": 150.0,
        "created_at": 1704067300,
        "created_at_str": "2024-01-01 12:01:40"
      }
    ]
  }
}
```

### 3. GET /api/prices
获取实时价格

**响应格式：**
```json
{
  "success": true,
  "data": {
    "BTC-USDT-SWAP": 45200.0,
    "ETH-USDT-SWAP": 2500.5
  }
}
```

### 4. GET /api/traders
获取交易员列表

**响应格式：**
```json
{
  "success": true,
  "data": [
    {
      "id": "trader-1",
      "name": "老王",
      "avatar": "https://...",
      "channel_id": "123456789",
      "channel_name": "老王-BTC专精"
    }
  ]
}
```

### 5. GET /api/channels/status
获取频道状态（可选）

**响应格式：**
```json
{
  "success": true,
  "data": [
    {
      "channel_id": "123456789",
      "channel_name": "BTC-USDT信号",
      "last_state": "浮盈",
      "last_pnl_points": 199.5,
      "updated_at": 1704067500
    }
  ]
}
```

## 错误处理

所有 API 端点应返回统一的错误格式：

```json
{
  "success": false,
  "error": "错误消息",
  "message": "错误消息（可选）"
}
```

HTTP 状态码：
- `200`: 成功
- `400`: 请求参数错误
- `404`: 资源不存在
- `500`: 服务器错误

## CORS 配置

如果前端和后端运行在不同的域名/端口，后端需要配置 CORS：

```python
# Flask 示例
from flask_cors import CORS
CORS(app, resources={r"/api/*": {"origins": "*"}})

# FastAPI 示例
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应限制为具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 测试连接

启动前端后，打开浏览器控制台，如果看到以下错误，说明后端 API 未连接：

```
获取交易单失败: Failed to fetch
```

请检查：
1. 后端服务是否运行
2. `NEXT_PUBLIC_API_BASE_URL` 是否正确
3. 后端 CORS 配置是否正确
4. 网络连接是否正常

