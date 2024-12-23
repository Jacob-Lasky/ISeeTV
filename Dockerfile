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

# Copy backend files
COPY backend/pyproject.toml backend/poetry.lock ./
RUN poetry install --no-root --no-dev

# Copy frontend files
COPY frontend/package*.json ./frontend/
WORKDIR /app/frontend
RUN npm install

# Copy all application code
COPY backend /app/backend
COPY frontend /app/frontend
COPY data/init_db.py /app/data/
COPY start.sh /app/

# Make start.sh executable
RUN chmod +x /app/start.sh

# Create startup script
WORKDIR /app

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV NVIDIA_VISIBLE_DEVICES=GPU-25f5d0be-15d5-fcff-be10-c1afca13d69a
ENV NVIDIA_DRIVER_CAPABILITIES=all

# Expose ports
EXPOSE 3000 8000

# Set user
USER nobody:users

# Start services
CMD ["/app/start.sh"]