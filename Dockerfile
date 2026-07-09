FROM python:3.12-slim

LABEL org.opencontainers.image.title="maimaiDX WeChat Bot"
LABEL org.opencontainers.image.description="舞萌DX 微信查分机器人，基于Gewechat"

# 换阿里云 Debian 源（国内加速）
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先装依赖（利用 Docker 缓存）
COPY requirements.txt .
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt

# 安装 Playwright Chromium
RUN python -m playwright install chromium --with-deps 2>/dev/null || \
    python -m playwright install chromium 2>/dev/null || \
    echo "Playwright 浏览器安装跳过（非核心功能）"

# 复制应用代码
COPY . .

# 创建数据目录
RUN mkdir -p /app/logs /app/static/data \
    /app/static/mai/plate_version /app/static/mai/plate_table /app/static/mai/rating_table

EXPOSE 8080

# 启动时先初始化静态资源（占位），然后启动服务
CMD ["sh", "-c", "python -m uvicorn app.main:app --host 0.0.0.0 --port ${WEBHOOK_PORT:-8080}"]
