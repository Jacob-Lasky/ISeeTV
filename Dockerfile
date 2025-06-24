# Multi-stage build for ISeeTV frontend and backend

# Stage 1: Build the Vue.js frontend
FROM node:22-alpine AS frontend-builder
WORKDIR /app/frontend

# Copy frontend files
COPY frontend/package*.json ./
RUN npm install

# Copy the rest of the frontend code
COPY frontend/ ./

# Build the frontend
RUN npm run build

# Stage 2: Set up the Python backend
FROM python:3.11-slim AS backend-builder
WORKDIR /app/backend

# Install Poetry
RUN pip install poetry==2.1.1

# Copy backend files
COPY backend/pyproject.toml backend/poetry.lock* ./

# Configure Poetry to not create a virtual environment
RUN poetry config virtualenvs.create false

# Install dependencies
RUN poetry install --no-root --no-interaction

# Stage 3: Final image
FROM python:3.11-slim
WORKDIR /app

# Install Nginx for serving the frontend
RUN apt-get update && apt-get install -y nginx && rm -rf /var/lib/apt/lists/*

# Copy backend from backend-builder
COPY --from=backend-builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=backend-builder /usr/local/bin /usr/local/bin
COPY backend/ /app/backend/

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
  '# Start the backend API server' \
  'cd /app/backend && python -m uvicorn main:app --host 0.0.0.0 --port 1314 --reload --reload-dir /app/backend &' \
  '' \
  '# Start Nginx' \
  'nginx -g "daemon off;"' \
  > /app/start.sh

RUN chmod +x /app/start.sh

# Expose port 80 for the web server
EXPOSE 80

# Start both services
CMD ["/app/start.sh"]
