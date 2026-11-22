# ---------- 阶段 1：构建 Vue 前端 ----------
FROM node:20-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
ENV NODE_OPTIONS=--max-old-space-size=1536
RUN npm run build

# ---------- 阶段 2：Python 服务 ----------
FROM python:3.12-slim
WORKDIR /app

# 先装依赖，利用 Docker 层缓存
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制后端代码
COPY . .

# 把上一步构建好的 Vue 产物放进最终镜像
COPY --from=frontend /app/frontend/dist ./frontend/dist

# 启动 Web 服务（FastAPI）。PORT 由平台注入，默认 8000
CMD uvicorn api:app --host 0.0.0.0 --port ${PORT:-8000}
