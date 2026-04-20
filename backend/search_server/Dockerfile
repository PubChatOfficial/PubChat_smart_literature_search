FROM python:3.11-slim

WORKDIR /app

COPY backend/search_server/requirements.txt /app/requirements.txt
COPY common_utils/requirements.txt /app/common_requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt -r /app/common_requirements.txt

# 2. 复制源码 (生产环境用，开发环境会被 Volume 覆盖)
COPY common_utils /app/common_utils
COPY backend/search_server /app/backend/search_server