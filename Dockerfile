# Build Stage: React Frontend
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Runtime Stage: Python Backend
FROM python:3.11-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir fastapi uvicorn python-multipart

# Copy built frontend assets
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Copy backend and automation scripts
COPY backend/ ./backend/
COPY Jack_Discord.py Jack_Google.py Jack_Insta.py ./
COPY .env ./

# Create uploads directory
RUN mkdir -p uploads

# Expose the API port
EXPOSE 8000

# Start the application
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
