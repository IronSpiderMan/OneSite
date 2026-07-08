#!/bin/sh
# 用环境变量覆盖 config.js，再启动 Nginx

cat > /usr/share/nginx/html/config.js <<EOF
window.__ENV__ = {
  DOMAIN: "${DOMAIN:-}",
  API_URL: "${API_URL:-http://localhost:8000/api/v1}",
  NODE_ENV: "${NODE_ENV:-production}",
  BUILD_VERSION: "${BUILD_VERSION:-}",
  LOGO_LINK: "${LOGO_LINK:-/dashboard}",
  PROJECT_NAME: "${PROJECT_NAME:-OneSite}",
  PROJECT_LOGO: "${PROJECT_LOGO:-}"
};
EOF

exec nginx -g "daemon off;"