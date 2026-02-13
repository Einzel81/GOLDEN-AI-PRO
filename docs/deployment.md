# Deployment Guide

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 4GB+ RAM available
- 20GB+ disk space

## Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/golden-ai-pro.git
cd golden-ai-pro

### 2. Environment Setup
cp .env.example .env
# Edit .env with your settings
nano .env

###3. Start Services
docker-compose up -d

4. Verify Deployment
# Check health
curl http://localhost:8000/health

# View logs
docker-compose logs -f api

Production Deployment
Server Requirements
CPU: 4+ cores
RAM: 8GB+ (16GB recommended)
Disk: SSD with 50GB+ free
Network: Stable internet connection
Security Checklist
Change default passwords
bash
Copy

# In .env file
POSTGRES_PASSWORD=strong_random_password
REDIS_PASSWORD=strong_random_password
Enable SSL/TLS
bash
Copy

# Using Let's Encrypt
certbot --nginx -d yourdomain.com
Firewall Configuration
bash
Copy
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 8000/tcp  # API (restrict to internal)
ufw enable
API Authentication
Set strong API keys in .env
Enable rate limiting
Use HTTPS only

Docker Compose Production
# docker-compose.prod.yml
version: '3.8'

services:
  api:
    build: .
    restart: always
    environment:
      - ENVIRONMENT=production
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '2'
          memory: 4G

  timescaledb:
    image: timescale/timescaledb:latest-pg15
    volumes:
      - timescale_data:/var/lib/postgresql/data
    deploy:
      resources:
        limits:
          memory: 2G

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    restart: always

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - api
