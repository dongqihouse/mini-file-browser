FROM python:3.11-slim

LABEL maintainer="File Browser"
LABEL description="Simple file browser for internal network"

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FILE_STORAGE_PATH=/data \
    HOST=0.0.0.0 \
    PORT=9100

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY src/ .

# 创建数据目录
RUN mkdir -p /data

# 暴露端口
EXPOSE 9100

# 创建非root用户运行应用
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app /data
USER appuser

# 使用gunicorn运行
CMD ["gunicorn", "--bind", "0.0.0.0:9100", "--workers", "4", "--threads", "2", "app:app"]
