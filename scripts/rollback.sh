#!/bin/bash
# 回滚脚本 - 一键回滚到上一版本

set -e

NAMESPACE="${NAMESPACE:-default}"
DEPLOYMENT_NAME="${DEPLOYMENT_NAME:-xcagi}"
REVISION="${1:-1}"

echo "开始回滚 $DEPLOYMENT_NAME 到修订版本 $REVISION..."

# 获取历史版本
echo "可用历史版本:"
kubectl rollout history deployment/$DEPLOYMENT_NAME -n $NAMESPACE

# 执行回滚
echo "执行回滚..."
kubectl rollout undo deployment/$DEPLOYMENT_NAME -n $NAMESPACE --to-revision=$REVISION

# 等待回滚完成
echo "等待回滚完成..."
kubectl rollout status deployment/$DEPLOYMENT_NAME -n $NAMESPACE --timeout=300s

# 验证健康状态
echo "验证服务健康状态..."
HEALTH_URL="${HEALTH_URL:-http://localhost:5000/health/liveness}"
if command -v curl &> /dev/null; then
    curl -sf "$HEALTH_URL" || {
        echo "健康检查失败!"
        exit 1
    }
fi

echo "回滚完成!"
kubectl get pods -n $NAMESPACE -l app=$DEPLOYMENT_NAME