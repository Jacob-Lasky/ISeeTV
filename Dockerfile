# Multi-stage build for ISeeTV frontend and backend

# Stage 1: Build the Vue.js frontend
FROM node:22-slim AS frontend-builder
WORKDIR /app/frontend

# Copy frontend files
COPY frontend/package*.json ./
RUN npm install

# Copy the rest of the frontend code
COPY frontend/ ./

# build the frontend
RUN npm run build

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

# Install Nginx for serving the frontend
RUN apt-get update && apt-get install -y nginx && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from backend-builder (no source code needed)
COPY --from=backend-builder /app/.venv /app/.venv

# Copy frontend build from frontend-builder
COPY --from=frontend-builder /app/frontend/dist /app/frontend/dist

# Configure Nginx to serve the frontend and proxy API requests to the backend
RUN rm -f /etc/nginx/sites-enabled/default

# Create Nginx configuration file
RUN printf '%s\n' \
  'server {' \
  '    listen 80;' \
  '    server_name localhost;' \
  '' \
  '    location / {' \
  '        alias /app/frontend/dist/;' \
  '        index index.html;' \
  '        try_files $uri $uri/ /index.html;' \
  '    }' \
  '' \
  '    location /api/ {' \
  '        proxy_pass http://localhost:1314;' \
  '        proxy_set_header Host $host;' \
  '        proxy_set_header X-Real-IP $remote_addr;' \
  '    }' \
  '}' > /etc/nginx/sites-available/default

RUN ln -s /etc/nginx/sites-available/default /etc/nginx/sites-enabled/

# Create a startup script
RUN printf '%s\n' \
  '#!/bin/bash' \
  '# Start the backend API server using venv binary directly' \
  'cd /app && /app/.venv/bin/uvicorn main:app --host 0.0.0.0 --port 1314 &' \
  '' \
  '# Start Nginx' \
  'nginx -g "daemon off;"' \
  > /app/start.sh

RUN chmod +x /app/start.sh

# Expose port 80 for the web server
EXPOSE 80

# Start both services
CMD ["/app/start.sh"]
