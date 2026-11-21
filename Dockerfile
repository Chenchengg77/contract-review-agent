FROM python:3.12-slim

WORKDIR /app

# 先装依赖，利用 Docker 层缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 再复制代码
COPY . .

# 启动 Web 服务（FastAPI）。PORT 由平台注入，默认 8000
CMD uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000}
