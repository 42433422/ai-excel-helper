# 构建上下文应为 FHD 仓库根目录：
#   docker build -f sandbox-app/Dockerfile -t xcagi-mod-sandbox .
FROM python:3.11-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    SANDBOX_HOST=0.0.0.0 \
    SANDBOX_PORT=5099 \
    LAN_GUARD_ENABLED=0 \
    XCAGI_NEURO_INTENT=0

COPY XCAGI/requirements.txt /tmp/xcagi-requirements.txt
RUN pip install --no-cache-dir -r /tmp/xcagi-requirements.txt

COPY app /app/app
COPY sandbox-app /app/sandbox-app
COPY mods /app/mods
COPY templates/vue-dist /app/templates/vue-dist
COPY resources /app/resources

WORKDIR /app/sandbox-app

RUN mkdir -p /app/sandbox-app/data/runtime

EXPOSE 5099

CMD ["python", "sandbox_run.py"]
