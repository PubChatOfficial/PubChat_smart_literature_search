FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 先复制 requirements.txt 并安装依赖
COPY backend/celery_worker/requirements.txt /app/requirements.txt
COPY common_utils/requirements.txt /app/common_utils/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt -r /app/common_utils/requirements.txt

# 拷贝源码
COPY backend/celery_worker /app/celery_worker
COPY common_utils /app/common_utils

# 设置 PYTHONPATH
# Use task_queue to avoid collision with python 'celery' package
ENV PYTHONPATH=/app
