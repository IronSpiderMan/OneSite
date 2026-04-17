# Build stage
FROM node:18-alpine as build

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine

# Install envsubst for runtime config
RUN apk add --no-cache gettext

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.template.conf /etc/nginx/templates/default.conf.template
COPY nginx.template.conf /etc/nginx/conf.d/default.conf
COPY config.js.template /usr/share/nginx/html/config.js.template
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh


EXPOSE 80

#ENTRYPOINT ["/docker-entrypoint.d/env.sh"]
ENTRYPOINT ["/entrypoint.sh"]

