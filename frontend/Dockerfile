# syntax=docker/dockerfile:1.7

# ---- Build stage (pnpm + Vite) ----
FROM node:20-alpine AS build

# pnpm via corepack
RUN corepack enable && corepack prepare pnpm@9 --activate

WORKDIR /app

COPY package.json pnpm-lock.yaml* ./
RUN pnpm install --frozen-lockfile || pnpm install

ARG VITE_WS_URL=ws://localhost:8000
ARG VITE_API_URL=http://localhost:8000
ENV VITE_WS_URL=$VITE_WS_URL
ENV VITE_API_URL=$VITE_API_URL

COPY . .
RUN pnpm build

# ---- Serve stage (nginx) ----
FROM nginx:alpine AS serve

COPY --from=build /app/dist /usr/share/nginx/html

# SPA fallback: enruta rutas desconocidas a index.html
RUN printf 'server {\n\
    listen 80;\n\
    server_name _;\n\
    root /usr/share/nginx/html;\n\
    index index.html;\n\
    location / { try_files $uri $uri/ /index.html; }\n\
}\n' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]