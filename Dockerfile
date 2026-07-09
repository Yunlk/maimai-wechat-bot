FROM python:3.12-slim

LABEL org.opencontainers.image.title="maimaiDX WeBot"
LABEL org.opencontainers.image.description="舞萌DX 查分机器人，企业微信智能机器人长连接模式"

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

# Playwright 浏览器国内下载太慢，跳过（仅 qq 头像功能用到，不影响核心查分）
RUN echo "Skip playwright browser install"

# 复制应用代码
COPY . .

# 创建数据目录
RUN mkdir -p /app/logs /app/static/data \
    /app/static/mai/plate_version /app/static/mai/plate_table /app/static/mai/rating_table

# 长连接模式，无需暴露端口（WebSocket 向外连接）
CMD ["python", "-m", "app.main"]
