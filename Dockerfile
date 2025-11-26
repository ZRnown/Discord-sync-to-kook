FROM python:3.12-slim AS builder

WORKDIR /app

# 复制依赖文件
COPY requirements.txt ./

# 安装依赖到虚拟环境，减少镜像大小
RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir -r requirements.txt && \
    find /opt/venv -name "*.pyc" -delete && \
    find /opt/venv -name "__pycache__" -delete

# 使用更小的运行时镜像
FROM python:3.12-slim

WORKDIR /app

# 从构建阶段复制虚拟环境
COPY --from=builder /opt/venv /opt/venv

# 设置环境变量使用虚拟环境
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 复制项目代码（仅必要部分）
COPY app ./app
COPY requirements.txt ./requirements.txt

# 创建下载目录与基础依赖
RUN mkdir -p downloads/images downloads/videos && \
    apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 默认启动应用
CMD ["python", "-m", "app.main"]