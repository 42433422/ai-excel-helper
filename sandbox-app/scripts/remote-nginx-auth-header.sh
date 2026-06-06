#!/usr/bin/env bash
# 在服务器上执行：为 /sandbox/ 反代补上 Authorization 转发（按需插入一行）。
set -euo pipefail
CONF=/etc/nginx/conf.d/xiu-ci.com.conf
if grep -q 'location /sandbox/' "$CONF" && grep -A25 'location /sandbox/' "$CONF" | grep -q 'proxy_set_header Authorization'; then
  echo "[ok] Authorization already present under /sandbox/"
  exit 0
fi
awk '
  /location \/sandbox\/ \{/ { in_sandbox=1 }
  in_sandbox && /proxy_set_header X-Forwarded-Proto \$scheme;/ {
    print
    print "        proxy_set_header Authorization $http_authorization;"
    next
  }
  in_sandbox && /^    \}/ { in_sandbox=0 }
  { print }
' "$CONF" > /tmp/xiu-ng.conf.$$
mv /tmp/xiu-ng.conf.$$ "$CONF"
nginx -t
systemctl reload nginx
echo "[ok] nginx patched + reloaded"
