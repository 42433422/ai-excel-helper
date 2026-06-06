# MODstore 生产部署：单 upstream 巡检

与 [`xiu-ci-single-modstore-upstream.md`](../../../成都修茈科技有限公司/MODstore_deploy/docs/runbooks/xiu-ci-single-modstore-upstream.md) 配套，供 FHD 发布前核对。

## 必须满足

| 项 | 说明 |
|----|------|
| 唯一 API 进程 | 公网 `xiu-ci.com` 的 `/api/`、`/v1/` 只反代到 **一套** modstore（推荐 systemd `:9999`） |
| 无 Docker 8765 并行 | 避免身份码、JWT、摘要跨实例不一致 |
| nginx 与 Vite base 一致 | 根路径部署用 [`nginx-xiu-ci-root.conf`](../../../成都修茈科技有限公司/nginx-xiu-ci-root.conf) + `VITE_PUBLIC_BASE=/` |
| FHD 环境变量 | `XCAGI_MARKET_BASE_URL=https://xiu-ci.com`（或内网直达地址），与 Android `MODSTORE_BASE_URL` 同源 |

## 快速巡检命令（服务器）

```bash
# 应只有一个 modstore 监听（示例端口 9999）
ss -lntp | grep -E '9999|8765'

# 健康检查
curl -sS -o /dev/null -w "%{http_code}" https://xiu-ci.com/api/auth/me
```

## 相关契约

- [AUTH_MARKET_CONTRACT.md](./AUTH_MARKET_CONTRACT.md)
- [MOBILE_ANDROID.md](./MOBILE_ANDROID.md)
