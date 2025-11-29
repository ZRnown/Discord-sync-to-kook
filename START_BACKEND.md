# 启动后端API服务

## 方法1：使用启动脚本（推荐）

```bash
python3 start_api.py
```

## 方法2：直接使用uvicorn

```bash
cd /Users/wanghaixin/Development/DiscordBotWork/Discord-sync-to-kook
python3 -m uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload
```

## 验证服务是否启动

访问以下地址确认服务正常运行：
- API文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/api/trades (需要登录)

## 注意事项

1. 确保Discord机器人已启动（用于提取交易信息）
2. 确保数据库文件存在（`./data/membership.db`）
3. 前端需要后端API运行在 `http://localhost:8000`

