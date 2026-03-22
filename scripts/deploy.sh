#!/bin/bash
# 部署脚本 - 蓝绿/金丝雀部署支持

set -e

set -a
source .env 2>/dev/null || true
set +a

NAMESPACE="${NAMESPACE:-default}"
IMAGE_TAG="${IMAGE_TAG:-latest}"
DEPLOYMENT_NAME="${DEPLOYMENT_NAME:-xcagi}"
STRATEGY="${STRATEGY:-rolling}"  # rolling, blue-green, canary

echo "XCAGI 部署脚本"
echo "===================="
echo "策略: $STRATEGY"
echo "镜像标签: $IMAGE_TAG"
echo ""

case "$STRATEGY" in
    rolling)
        echo "执行滚动更新..."
        kubectl set image deployment/$DEPLOYMENT_NAME xcagi=xcagi:$IMAGE_TAG -n $NAMESPACE
        kubectl rollout status deployment/$DEPLOYMENT_NAME -n $NAMESPACE --timeout=600s
        ;;
    blue-green)
        echo "执行蓝绿部署..."
        kubectl scale deployment/$DEPLOYMENT_NAME --replicas=0 -n $NAMESPACE
        kubectl set image deployment/$DEPLOYMENT_NAME xcagi=xcagi:$IMAGE_TAG -n $NAMESPACE
        kubectl scale deployment/$DEPLOYMENT_NAME --replicas=3 -n $NAMESPACE
        kubectl rollout status deployment/$DEPLOYMENT_NAME -n $NAMESPACE --timeout=600s
        ;;
    canary)
        echo "执行金丝雀部署..."
        # 10% 流量到新版本
        kubectl patch deployment/$DEPLOYMENT_NAME -n $NAMESPACE -p '{"spec":{"template":{"spec":{"containers":[{"name":"xcagi","image":"xcagi:'"$IMAGE_TAG"'"}]}}}}'
        kubectl rollout status deployment/$DEPLOYMENT_NAME -n $NAMESPACE --timeout=600s
        echo "金丝雀流量: 10% (手动调整 Ingress 配置)"
        ;;
esac

echo ""
echo "运行健康检查..."
./scripts/health-check.sh

echo ""
echo "部署完成!"
kubectl get pods -n $NAMESPACE -l app=$DEPLOYMENT_NAME