#!/bin/bash
set -x
set -e

ZAP_HOST="localhost"
ZAP_PORT="8090"
REPORT_DIR="$1"
TEMPLATE_DIR="$2"
TEMPLATE_FILE="$3"
SAFE_FILENAME="$4"
ZAP_TARGET_URL="$5"


[ -z "$ZAP_TARGET_URL" ] && { echo "ERRO: URL não fornecida" >&2; exit 1; }

CONTEXT_NAME="temp_context_$(date +%s)"
curl -s "http://$ZAP_HOST:$ZAP_PORT/JSON/context/action/newContext/?apikey=$ZAP_API_KEY&contextName=$CONTEXT_NAME"
curl -s "http://$ZAP_HOST:$ZAP_PORT/JSON/context/action/includeInContext/?apikey=$ZAP_API_KEY&contextName=$CONTEXT_NAME&regex=${ZAP_TARGET_URL//./\\.}.*"

mkdir -p "$REPORT_DIR"
REPORT_JSON="$REPORT_DIR/$SAFE_FILENAME.json"
echo "$REPORT_JSON"

echo "1. Executando spider na URL..."
SPIDER_ID=$(curl -s "http://$ZAP_HOST:$ZAP_PORT/JSON/spider/action/scan/?apikey=$ZAP_API_KEY&url=$ZAP_TARGET_URL&contextName=$CONTEXT_NAME" | jq -r '.scan')

[ -z "$SPIDER_ID" ] || [ "$SPIDER_ID" = "null" ] && {
    echo "Falha ao iniciar spider. Resposta:"
    curl -s "http://$ZAP_HOST:$ZAP_PORT/JSON/spider/action/scan/?apikey=$ZAP_API_KEY&url=$ZAP_TARGET_URL&contextName=$CONTEXT_NAME" | jq .
    exit 1
}

echo "Spider ID: $SPIDER_ID"
while :; do
    SPIDER_STATUS=$(curl -s "http://$ZAP_HOST:$ZAP_PORT/JSON/spider/view/status/?apikey=$ZAP_API_KEY&scanId=$SPIDER_ID" | jq -r '.status')
    echo "Progresso do spider: $SPIDER_STATUS%"
    [ "$SPIDER_STATUS" -eq 100 ] && break
    sleep 5
done

echo "2. Iniciando scan ativo..."
SCAN_ID=$(curl -s "http://$ZAP_HOST:$ZAP_PORT/JSON/ascan/action/scan/?apikey=$ZAP_API_KEY&url=$ZAP_TARGET_URL&contextName=$CONTEXT_NAME" | jq -r '.scan')

[ -z "$SCAN_ID" ] || [ "$SCAN_ID" = "null" ] && {
    echo "Falha ao iniciar scan. Resposta:"
    curl -s "http://$ZAP_HOST:$ZAP_PORT/JSON/ascan/action/scan/?apikey=$ZAP_API_KEY&url=$ZAP_TARGET_URL&contextName=$CONTEXT_NAME" | jq .
    exit 1
}

echo "Scan ID: $SCAN_ID"
START_TIME=$(date +%s)
while :; do
    CURRENT_TIME=$(date +%s)
    ELAPSED_TIME=$((CURRENT_TIME - START_TIME))
    
    FORMATTED_TIME=$(printf "%02d:%02d:%02d" $((ELAPSED_TIME/3600)) $((ELAPSED_TIME%3600/60)) $((ELAPSED_TIME%60)))
    
    SCAN_STATUS=$(curl -s "http://$ZAP_HOST:$ZAP_PORT/JSON/ascan/view/status/?apikey=$ZAP_API_KEY&scanId=$SCAN_ID" | jq -r '.status')
    echo "Progresso: $SCAN_STATUS% | Tempo decorrido: $FORMATTED_TIME"
    
    [ "$SCAN_STATUS" -eq 100 ] && break
    sleep 10
done

echo "3. Gerando relatório..."
curl -s "http://$ZAP_HOST:$ZAP_PORT/OTHER/core/other/jsonreport/?apikey=$ZAP_API_KEY" > "$REPORT_JSON"

[ -s "$REPORT_JSON" ] && {
    echo "Relatório gerado em $REPORT_JSON"
    curl -s "http://$ZAP_HOST:$ZAP_PORT/JSON/context/action/removeContext/?apikey=$ZAP_API_KEY&contextName=$CONTEXT_NAME"

    echo "Gerando relatório HTML..."
    python3 /app/services/render.py "$REPORT_JSON" "$TEMPLATE_DIR/$TEMPLATE_FILE" "$REPORT_DIR/$SAFE_FILENAME.html"
} || {
    echo "Falha ao gerar relatório JSON" >&2
    exit 1
}