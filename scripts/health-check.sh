#!/bin/bash
# 健康检查脚本 - 部署后自动验证

set -e

HEALTH_URL="${HEALTH_URL:-http://localhost:5000}"
TIMEOUT="${TIMEOUT:-60}"
INTERVAL="${INTERVAL:-2}"

echo "开始健康检查..."
echo "目标服务: $HEALTH_URL"
echo "超时时间: ${TIMEOUT}s"
echo "检查间隔: ${INTERVAL}s"

# 检查 liveness
echo ""
echo "=== Liveness 检查 ==="
elapsed=0
while [ $elapsed -lt $TIMEOUT ]; do
    response=$(curl -sf -w "\n%{http_code}" "$HEALTH_URL/health/liveness" 2>/dev/null || echo "000")
    status_code=$(echo "$response" | tail -n1)

    if [ "$status_code" = "200" ]; then
        echo "Liveness: OK (${elapsed}s)"
        break
    fi

    echo "等待 Liveness 恢复... (${elapsed}s) status=$status_code"
    sleep $INTERVAL
    elapsed=$((elapsed + INTERVAL))
done

if [ $elapsed -ge $TIMEOUT ]; then
    echo "Liveness 检查超时!"
    exit 1
fi

# 检查 readiness
echo ""
echo "=== Readiness 检查 ==="
elapsed=0
while [ $elapsed -lt $TIMEOUT ]; do
    response=$(curl -sf -w "\n%{http_code}" "$HEALTH_URL/health/readiness" 2>/dev/null || echo "000")
    status_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')

    if [ "$status_code" = "200" ]; then
        echo "Readiness: OK (${elapsed}s)"
        echo "详情: $body"
        break
    fi

    echo "等待 Readiness 恢复... (${elapsed}s) status=$status_code"
    sleep $INTERVAL
    elapsed=$((elapsed + INTERVAL))
done

if [ $elapsed -ge $TIMEOUT ]; then
    echo "Readiness 检查超时!"
    exit 1
fi

# 检查详细健康信息
echo ""
echo "=== 详细健康信息 ==="
curl -sf "$HEALTH_URL/health/details" | python3 -m json.tool 2>/dev/null || echo "无法获取详细信息"

echo ""
echo "健康检查完成!"