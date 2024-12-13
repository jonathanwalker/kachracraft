# Build frontend
FROM node:18 as frontend-builder
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

# Setup backend
FROM python:3.9-slim
RUN apt-get update && \
    apt-get install -y openscad && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app/backend
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy files and setup directories
COPY backend/ ./
RUN mkdir -p static /root/.aws
COPY --from=frontend-builder /app/frontend/dist/ ./static/

EXPOSE 5000
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
