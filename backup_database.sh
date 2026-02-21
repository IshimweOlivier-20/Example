#!/bin/bash
# Automated PostgreSQL backup script for IshemaLink
# Compliance: Data sovereignty - backups stored in Rwanda data centers
# Schedule: Run via cron every 6 hours

set -e

# Configuration
BACKUP_DIR="/backups"
DB_NAME="${DB_NAME:-ishemalink_db}"
DB_USER="${DB_USER:-ishemalink}"
DB_HOST="${DB_HOST:-localhost}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/ishemalink_${TIMESTAMP}.sql.gz"
RETENTION_DAYS=30

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}=========================================="
echo "IshemaLink Database Backup"
echo "==========================================${NC}"
echo "Timestamp: $(date)"
echo "Database: ${DB_NAME}"
echo ""

# Create backup directory if it doesn't exist
mkdir -p ${BACKUP_DIR}

# Perform backup
echo -e "${YELLOW}[1/4] Creating database dump...${NC}"
pg_dump -h ${DB_HOST} -U ${DB_USER} -d ${DB_NAME} \
    --format=plain \
    --no-owner \
    --no-acl \
    --verbose \
    | gzip > ${BACKUP_FILE}

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Backup created successfully${NC}"
    BACKUP_SIZE=$(du -h ${BACKUP_FILE} | cut -f1)
    echo "  File: ${BACKUP_FILE}"
    echo "  Size: ${BACKUP_SIZE}"
else
    echo -e "${RED}✗ Backup failed${NC}"
    exit 1
fi
echo ""

# Verify backup integrity
echo -e "${YELLOW}[2/4] Verifying backup integrity...${NC}"
gunzip -t ${BACKUP_FILE}
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Backup file is valid${NC}"
else
    echo -e "${RED}✗ Backup file is corrupted${NC}"
    exit 1
fi
echo ""

# Upload to S3-compatible storage (MinIO/AWS)
echo -e "${YELLOW}[3/4] Uploading to remote storage...${NC}"
if command -v aws &> /dev/null; then
    # Upload to S3 (or MinIO with S3 compatibility)
    aws s3 cp ${BACKUP_FILE} s3://ishemalink-backups/database/ \
        --endpoint-url ${S3_ENDPOINT:-https://s3.rwanda.cloud} \
        --region rw-kigali-1
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Uploaded to remote storage${NC}"
    else
        echo -e "${YELLOW}⚠ Remote upload failed (local backup retained)${NC}"
    fi
else
    echo -e "${YELLOW}⚠ AWS CLI not found, skipping remote upload${NC}"
fi
echo ""

# Clean up old backups
echo -e "${YELLOW}[4/4] Cleaning up old backups (>${RETENTION_DAYS} days)...${NC}"
find ${BACKUP_DIR} -name "ishemalink_*.sql.gz" -type f -mtime +${RETENTION_DAYS} -delete
DELETED_COUNT=$(find ${BACKUP_DIR} -name "ishemalink_*.sql.gz" -type f -mtime +${RETENTION_DAYS} | wc -l)
echo -e "${GREEN}✓ Removed ${DELETED_COUNT} old backup(s)${NC}"
echo ""

# Summary
echo -e "${GREEN}=========================================="
echo "Backup Complete"
echo "==========================================${NC}"
echo "Latest backup: ${BACKUP_FILE}"
echo "Retention: ${RETENTION_DAYS} days"
echo ""

# Log to syslog
logger -t ishemalink-backup "Database backup completed: ${BACKUP_FILE}"

exit 0
