#!/usr/bin/env python3
"""
启动 FastAPI 后端服务
"""
import uvicorn
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    print("=" * 60)
    print("启动 FastAPI 后端服务...")
    print("API 文档: http://localhost:8000/docs")
    print("API 地址: http://localhost:8000")
    print("=" * 60)
    uvicorn.run(
        "app.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

