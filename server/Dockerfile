# 后端镜像：FastAPI + Uvicorn
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONUTF8=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 先装依赖，利用层缓存。用清华 PyPI 镜像（国内网络更稳；境外可删 -i 改回官方源）
COPY requirements.txt .
RUN pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# 拷贝应用代码（.dockerignore 已排除 storage/.env 等）
COPY . .

EXPOSE 8000

# 启动前先跑数据库迁移（既有库自动补建缺表），再启服务
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
