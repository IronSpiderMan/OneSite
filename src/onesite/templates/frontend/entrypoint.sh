#!/bin/sh
# 用环境变量生成运行时配置和 Nginx 配置，再启动 Nginx

set -eu

# Docker Compose 中后端服务默认名为 backend。只替换 DOMAIN，避免 envsubst
# 把 $uri、$host 等 Nginx 运行时变量替换为空字符串。
DOMAIN="${DOMAIN:-backend}"
export DOMAIN
envsubst '${DOMAIN}' \
  < /etc/nginx/templates/default.conf.template \
  > /etc/nginx/conf.d/default.conf

cat > /usr/share/nginx/html/config.js <<EOF
window.__ENV__ = {
  DOMAIN: "${DOMAIN}",
  API_URL: "${API_URL:-http://localhost:8000/api/v1}",
  NODE_ENV: "${NODE_ENV:-production}",
  BUILD_VERSION: "${BUILD_VERSION:-}",
  LOGO_LINK: "${LOGO_LINK:-/dashboard}",
  PROJECT_NAME: "${PROJECT_NAME:-OneSite}",
  PROJECT_LOGO: "${PROJECT_LOGO:-}"
};
EOF

exec nginx -g "daemon off;"
