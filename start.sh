#! /bin/bash

# Initialize database
python /app/data/init_db.py

# Start backend in background
cd /app/backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload --reload-exclude="_dev.py" &

# Start frontend
cd /app/frontend
exec npm start
