FROM python:3.9-slim-bullseye

USER root
WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get update && apt-get install -y \
    jq \
    curl \
    dos2unix \
    wget \
    openjdk-17-jre-headless \
    && rm -rf /var/lib/apt/lists/* 

ENV ZAP_VERSION=2.16.1
RUN wget -q -O /tmp/zap.tar.gz "https://github.com/zaproxy/zaproxy/releases/download/v${ZAP_VERSION}/ZAP_${ZAP_VERSION}_Linux.tar.gz" && \
    tar -xzf /tmp/zap.tar.gz -C /opt && \
    rm /tmp/zap.tar.gz && \
    mv /opt/ZAP_* /opt/zap && \
    ln -sf /opt/zap/zap.sh /usr/local/bin/zap.sh && \
    chmod +x /usr/local/bin/zap.sh

COPY . .

RUN ls -la scripts/run-zap.sh && \
    pwd && \
    dos2unix scripts/run-zap.sh && \
    chmod +x scripts/run-zap.sh && \
    chmod +x services/render.py && \
    mkdir -p /app/reports /app/.ZAP && \
    chmod -R 777 /app/reports

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_APP=src.app:app \
    FLASK_ENV=development \
    ZAP_HOME=/app/.ZAP

EXPOSE 8080
EXPOSE 8090

CMD ["sh", "-c", "/usr/local/bin/zap.sh -daemon -port 8090 -host 0.0.0.0 -config api.disablekey=true -dir /app/.ZAP & gunicorn --bind 0.0.0.0:8080 src.app:app"]