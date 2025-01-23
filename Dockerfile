FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 22
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Install Poetry
RUN pip install poetry
RUN poetry config virtualenvs.create false

# Copy dependency files first
COPY backend/pyproject.toml backend/poetry.lock ./
COPY backend/python-ffmpeg-video-streaming/ ./python-ffmpeg-video-streaming
RUN poetry install --no-root

# Install frontend dependencies
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV NVIDIA_VISIBLE_DEVICES=GPU-25f5d0be-15d5-fcff-be10-c1afca13d69a
ENV NVIDIA_DRIVER_CAPABILITIES=all
ENV DATA_DIRECTORY=/app/data

# Create data directory and set permissions
RUN mkdir -p $DATA_DIRECTORY && \
    chown -R nobody:users $DATA_DIRECTORY && \
    chmod 777 $DATA_DIRECTORY

# Copy application code last
COPY backend /app/backend
COPY frontend /app/frontend
COPY data/init_db.py /app/data/
COPY start.sh /app/

# Make start.sh executable
RUN chmod +x /app/start.sh

# Expose ports
EXPOSE 3000 8000

# Set user
USER nobody:users

# Start services
CMD ["/app/start.sh"]