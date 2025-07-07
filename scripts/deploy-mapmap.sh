#!/bin/bash
set -e

echo "🚀 Deploying MapMap Tile Proxy..."

# Navigate to project directory
cd /home/mapmap/mapmap

# Update repository
echo "📥 Updating repository..."
git pull origin main

# Build and start services
echo "🐳 Building and starting Docker services..."
docker-compose -f docker-compose.production.yml build --no-cache
docker-compose -f docker-compose.production.yml up -d

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 30

# Health check
echo "🔍 Checking service health..."
if curl -f http://localhost:8000/health; then
    echo "✅ MapMap is running successfully!"
    echo "🌐 Service available at: https://$(hostname -f)"
else
    echo "❌ Health check failed!"
    docker-compose -f docker-compose.production.yml logs
    exit 1
fi