# 后端API启动说明

## 问题
前端报错 `ECONNREFUSED`，说明后端API服务没有运行。

## 解决方案

### 1. 启动后端API服务

**方法1：使用启动脚本（推荐）**
```bash
python3 start_api.py
```

**方法2：直接使用uvicorn**
```bash
python3 -m uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. 验证服务是否启动

访问以下地址确认服务正常运行：
- API文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/api/trades (需要登录)

### 3. 数据流程说明

1. **Discord机器人** → 提取交易信息 → 保存到数据库
2. **后端API** → 从数据库读取 → 返回给前端
3. **前端** → 接收数据 → 使用当前币价计算状态和盈亏

### 4. 注意事项

- 后端API需要运行在 `http://localhost:8000`
- 前端会自动从后端获取数据
- 前端会根据当前币价实时计算状态和盈亏
- 不需要OKX获取带单员API，只需要获取币价用于计算

### 5. 启动顺序

1. 先启动Discord机器人：`python3 -m app.main`
2. 再启动后端API：`python3 start_api.py`
3. 最后启动前端：`cd frontend && npm run dev`

