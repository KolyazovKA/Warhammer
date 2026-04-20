# ── Stage 1: build React app ─────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

COPY src/frontend/frontend-proto/package*.json ./
RUN npm ci --legacy-peer-deps

COPY src/frontend/frontend-proto/ .
RUN npm run build

# ── Stage 2: serve with Nginx ─────────────────────────────────────────────────
FROM nginx:1.27-alpine AS runtime

# Drop default config
RUN rm /etc/nginx/conf.d/default.conf

COPY docker/nginx.frontend.conf /etc/nginx/conf.d/app.conf
COPY --from=builder /app/dist /usr/share/nginx/html

# nginx master runs as root (required to bind port 80) but workers run as nginx
# Switch to a non-privileged port to run entirely rootless if needed
EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
