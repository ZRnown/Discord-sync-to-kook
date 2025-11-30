#!/bin/bash
# 启动后端 API 服务

cd "$(dirname "$0")"

# 检查端口是否被占用
if lsof -ti:8000 > /dev/null 2>&1; then
    echo "⚠️  端口 8000 已被占用"
    echo "正在运行的进程:"
    lsof -ti:8000 | xargs ps -p 2>/dev/null || echo "无法获取进程信息"
    echo ""
    read -p "是否要终止占用端口的进程? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "正在终止进程..."
        lsof -ti:8000 | xargs kill -9 2>/dev/null
        sleep 2
        echo "✅ 进程已终止"
    else
        echo "❌ 请手动终止占用端口的进程，或修改端口配置"
        exit 1
    fi
fi

echo "🚀 启动后端 API 服务..."
echo "📍 服务地址: http://localhost:8000"
echo "📚 API 文档: http://localhost:8000/docs"
echo ""
echo "按 Ctrl+C 停止服务"
echo ""

# 启动服务 - 使用正确的模块路径
python3 -m uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload

