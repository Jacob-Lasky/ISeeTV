# Multi-stage build for ISeeTV frontend and backend

# Stage 1: Build the Vue.js frontend
FROM node:22-slim AS frontend-builder

RUN corepack enable && corepack prepare pnpm@10.13.1 --activate

WORKDIR /app/frontend

# Copy frontend files
COPY frontend/package*.json ./
RUN pnpm install

# Copy the rest of the frontend code
COPY frontend/ ./

# build the frontend
RUN pnpm run build

# Stage 2: Set up the Python backend
FROM python:3.11-slim-bookworm AS backend-builder

# Install uv (pinned version for reproducible builds)
COPY --from=ghcr.io/astral-sh/uv:0.7.20 /uv /bin/

# Set working directory
WORKDIR /app

# Copy Python project files
COPY backend/pyproject.toml backend/uv.lock ./

# Install dependencies without the project itself
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project --no-editable

# Copy backend source code
COPY backend/ ./

# Install the project in non-editable mode
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable

# Stage 3: Final image
FROM python:3.11-slim-bookworm
WORKDIR /app

# Install runtime deps (nginx, curl, tini for proper PID 1)
RUN apt-get update && apt-get install -y nginx curl ca-certificates \
  && rm -rf /var/lib/apt/lists/* \
  && mkdir -p /app/data/meili_data

# --- Meilisearch install ---
ARG MEILI_VERSION=v1.7.0
RUN curl -L "https://github.com/meilisearch/meilisearch/releases/download/${MEILI_VERSION}/meilisearch-linux-amd64" \
  -o /usr/local/bin/meilisearch && \
  chmod +x /usr/local/bin/meilisearch

# Copy virtual environment and frontend artifacts
COPY --from=backend-builder /app/.venv /app/.venv
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Nginx config
RUN rm -f /etc/nginx/sites-enabled/default
RUN printf '%s\n' \
  'server {' \
  '    listen 80;' \
  '    server_name _;' \
  '    location / {' \
  '        alias /app/frontend/dist/;' \
  '        index index.html;' \
  '        try_files $uri $uri/ /index.html;' \
  '    }' \
  '    location /api/ {' \
  '        proxy_pass http://127.0.0.1:1314;' \
  '        proxy_set_header Host $host;' \
  '        proxy_set_header X-Real-IP $remote_addr;' \
  '    }' \
  '}' > /etc/nginx/sites-available/default && \
  ln -s /etc/nginx/sites-available/default /etc/nginx/sites-enabled/

# Start script (runs Meili + API + Nginx)
RUN printf '%s\n' \
'#!/usr/bin/env bash' \
'set -euo pipefail' \
'trap "echo Shutting down...; kill 0" SIGTERM SIGINT' \
'' \
': "${MEILI_MASTER_KEY:=meili_prod_master_key}"' \
': "${MEILI_HTTP_ADDR:=127.0.0.1:7700}"' \
': "${MEILI_ENV:=production}"' \
': "${MEILI_NO_ANALYTICS:=true}"' \
'' \
'echo "Starting Meilisearch..."' \
'meilisearch \\' \
'  --master-key "$MEILI_MASTER_KEY" \\' \
'  --db-path "/app/data/meili_data" \\' \
'  --http-addr "$MEILI_HTTP_ADDR" \\' \
'  $( [ "$MEILI_NO_ANALYTICS" = "true" ] && echo "--no-analytics" ) \\' \
'  & MEILI_PID=$!' \
'' \
'echo "Starting API (Uvicorn)..."' \
'/app/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 1314 & API_PID=$!' \
'' \
'echo "Starting Nginx..."' \
'nginx -g "daemon off;" & NGINX_PID=$!' \
'' \
'wait -n $MEILI_PID $API_PID $NGINX_PID' \
'EXIT_CODE=$?' \
'kill 0 || true' \
'exit "$EXIT_CODE"' \
> /app/start.sh && chmod +x /app/start.sh

EXPOSE 80
CMD ["/app/start.sh"]
