#!/bin/bash

# Backup Script for Golden-AI Pro
# ================================

BACKUP_DIR="/backup/golden-ai"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

mkdir -p $BACKUP_DIR

echo "Creating backup: $DATE..."

# Backup database
echo "Backing up database..."
docker exec golden-ai-db pg_dump -U postgres golden_ai | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Backup models
echo "Backing up models..."
tar -czf $BACKUP_DIR/models_$DATE.tar.gz models/

# Backup configuration
echo "Backing up configuration..."
tar -czf $BACKUP_DIR/config_$DATE.tar.gz .env config/

# Backup logs (optional)
# tar -czf $BACKUP_DIR/logs_$DATE.tar.gz logs/

# Cleanup old backups
echo "Cleaning up old backups..."
find $BACKUP_DIR -name "*.gz" -mtime +$RETENTION_DAYS -delete

echo "✅ Backup complete: $BACKUP_DIR"
ls -lh $BACKUP_DIR/*_$DATE*
