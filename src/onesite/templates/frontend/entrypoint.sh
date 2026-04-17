#!/bin/sh
# 用环境变量覆盖 config.js，再启动 Nginx

cat > /usr/share/nginx/html/config.js <<EOF
window.__ENV__ = {
  API_URL: "${API_URL:-http://localhost:8000/api/v1}"
};
EOF

exec nginx -g "daemon off;"