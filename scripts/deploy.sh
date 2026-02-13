#!/bin/bash

# Deployment Script for Golden-AI Pro
# ===================================

set -e

ENVIRONMENT=${1:-production}
VERSION=$(git describe --tags --always 2>/dev/null || echo "latest")

echo "🚀 Deploying Golden-AI Pro v$VERSION to $ENVIRONMENT..."

# Pull latest changes
if [ -d ".git" ]; then
    git pull origin main
fi

# Build and start services
if [ "$ENVIRONMENT" == "production" ]; then
    docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
else
    docker-compose up -d --build
fi

# Wait for services to be healthy
echo "⏳ Waiting for services to be healthy..."
sleep 10

# Health check
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Deployment successful!"
    echo ""
    echo "Services:"
    echo "  API: http://localhost:8000"
    echo "  Dashboard: http://localhost:3000"
    echo "  MLflow: http://localhost:5000"
    echo "  Grafana: http://localhost:3100"
else
    echo "❌ Health check failed!"
    docker-compose logs api
    exit 1
fi
