#!/bin/sh
set -e

# Substitute environment variables in config.js
envsubst '${API_URL} ${WS_URL}' < /usr/share/nginx/html/config.js.template > /usr/share/nginx/html/config.js

# Also set in nginx env for potential use
env | grep -E '^(API_URL|WS_URL)=' >> /etc/environment 2>/dev/null || true
