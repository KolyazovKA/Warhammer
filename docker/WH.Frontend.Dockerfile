FROM node:20-alpine AS builder

WORKDIR /app

COPY src/frontend/frontend-proto/package*.json ./

RUN npm ci --legacy-peer-deps

COPY src/frontend/frontend-proto/ .

# CMD ["sh"]
RUN npm run build

FROM nginx:alpine

COPY --from=builder /app/dist /usr/share/nginx/html
COPY src/frontend/frontend-proto/nginx.conf /etc/nginx/nginx.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
