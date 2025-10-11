#!/bin/bash

# SyferStack V2 Backup & Disaster Recovery System
# Automated database backups, configuration versioning, and recovery procedures

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_ROOT/backups"
LOG_DIR="$PROJECT_ROOT/logs"
BACKUP_LOG="$LOG_DIR/backup.log"

# Cloud configuration (set these in environment or .env file)
GCS_BUCKET="${GCS_BACKUP_BUCKET:-syferstack-v2-backups}"
AWS_S3_BUCKET="${AWS_BACKUP_BUCKET:-syferstack-v2-backups}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

# Database configuration
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-syferstack}"
DB_USER="${DB_USER:-syferstack}"

# Create necessary directories
mkdir -p "$BACKUP_DIR" "$LOG_DIR"

# Logging function
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$BACKUP_LOG"
}

# Function to create database backup
backup_database() {
    local backup_name="db_backup_$(date '+%Y%m%d_%H%M%S').sql"
    local backup_path="$BACKUP_DIR/$backup_name"
    
    log_message "Starting database backup..."
    
    # Set password from environment
    export PGPASSWORD="$DB_PASSWORD"
    
    # Create database dump
    if pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        --verbose --clean --if-exists --create \
        --format=custom --compress=9 \
        --file="$backup_path.dump" 2>> "$BACKUP_LOG"; then
        
        # Also create SQL version for easier inspection
        pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
            --verbose --clean --if-exists --create \
            > "$backup_path" 2>> "$BACKUP_LOG"
        
        # Compress SQL backup
        gzip "$backup_path"
        
        log_message "Database backup completed: ${backup_name}.dump and ${backup_name}.gz"
        
        # Verify backup integrity
        if verify_backup "$backup_path.dump"; then
            log_message "Backup verification passed"
            echo "$backup_path.dump"
        else
            log_message "Backup verification failed"
            return 1
        fi
    else
        log_message "Database backup failed"
        return 1
    fi
    
    unset PGPASSWORD
}

# Function to verify backup integrity
verify_backup() {
    local backup_file="$1"
    
    log_message "Verifying backup integrity: $(basename "$backup_file")"
    
    # Check if backup file exists and is not empty
    if [ ! -f "$backup_file" ] || [ ! -s "$backup_file" ]; then
        log_message "Backup file is missing or empty"
        return 1
    fi
    
    # Test restore to temporary database (if test DB is configured)
    if [ -n "${TEST_DB_NAME:-}" ]; then
        log_message "Testing backup restore to temporary database"
        
        # Drop and recreate test database
        export PGPASSWORD="$DB_PASSWORD"
        dropdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$TEST_DB_NAME" --if-exists 2>/dev/null || true
        createdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$TEST_DB_NAME" 2>/dev/null || return 1
        
        # Restore backup to test database
        if pg_restore -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$TEST_DB_NAME" \
            --verbose --clean --if-exists "$backup_file" 2>> "$BACKUP_LOG"; then
            
            # Verify some basic data integrity
            local table_count=$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$TEST_DB_NAME" \
                -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';" 2>/dev/null | xargs)
            
            if [ "${table_count:-0}" -gt 0 ]; then
                log_message "Backup verification successful: $table_count tables restored"
                dropdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$TEST_DB_NAME" 2>/dev/null || true
                unset PGPASSWORD
                return 0
            else
                log_message "Backup verification failed: No tables found"
                dropdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$TEST_DB_NAME" 2>/dev/null || true
                unset PGPASSWORD
                return 1
            fi
        else
            log_message "Backup verification failed: Could not restore to test database"
            unset PGPASSWORD
            return 1
        fi
    else
        log_message "Skipping restore test (TEST_DB_NAME not configured)"
        return 0
    fi
}

# Function to backup configuration files
backup_configs() {
    local config_backup="config_backup_$(date '+%Y%m%d_%H%M%S').tar.gz"
    local backup_path="$BACKUP_DIR/$config_backup"
    
    log_message "Starting configuration backup..."
    
    # List of configuration files and directories to backup
    local config_paths=(
        "backend/app/core/config.py"
        "backend/docker-compose.yml"
        "backend/docker-compose.prod.yml"
        "backend/nginx/nginx.conf"
        "backend/monitoring/"
        "frontend/vite.config.ts"
        "frontend/package.json"
        ".github/workflows/"
        ".pre-commit-config.yaml"
        "scripts/"
    )
    
    # Create archive of configuration files
    cd "$PROJECT_ROOT"
    
    # Build tar command with existing files only
    local existing_paths=()
    for path in "${config_paths[@]}"; do
        if [ -e "$path" ]; then
            existing_paths+=("$path")
        fi
    done
    
    if [ ${#existing_paths[@]} -gt 0 ]; then
        if tar -czf "$backup_path" "${existing_paths[@]}" 2>> "$BACKUP_LOG"; then
            log_message "Configuration backup completed: $config_backup"
            echo "$backup_path"
        else
            log_message "Configuration backup failed"
            return 1
        fi
    else
        log_message "No configuration files found to backup"
        return 1
    fi
}

# Function to upload backup to Google Cloud Storage
upload_to_gcs() {
    local backup_file="$1"
    local remote_path="backups/$(date '+%Y/%m')/$(basename "$backup_file")"
    
    if command -v gsutil >/dev/null 2>&1; then
        log_message "Uploading backup to Google Cloud Storage..."
        
        if gsutil cp "$backup_file" "gs://$GCS_BUCKET/$remote_path" 2>> "$BACKUP_LOG"; then
            log_message "Upload to GCS successful: gs://$GCS_BUCKET/$remote_path"
            
            # Set lifecycle policy for automatic cleanup
            gsutil lifecycle set /dev/stdin "gs://$GCS_BUCKET" << EOF
{
  "rule": [
    {
      "action": {"type": "Delete"},
      "condition": {
        "age": $BACKUP_RETENTION_DAYS,
        "matchesPrefix": ["backups/"]
      }
    }
  ]
}
EOF
            return 0
        else
            log_message "Upload to GCS failed"
            return 1
        fi
    else
        log_message "gsutil not found, skipping GCS upload"
        return 1
    fi
}

# Function to upload backup to AWS S3
upload_to_s3() {
    local backup_file="$1"
    local remote_path="backups/$(date '+%Y/%m')/$(basename "$backup_file")"
    
    if command -v aws >/dev/null 2>&1; then
        log_message "Uploading backup to AWS S3..."
        
        if aws s3 cp "$backup_file" "s3://$AWS_S3_BUCKET/$remote_path" 2>> "$BACKUP_LOG"; then
            log_message "Upload to S3 successful: s3://$AWS_S3_BUCKET/$remote_path"
            
            # Set lifecycle policy for automatic cleanup
            aws s3api put-bucket-lifecycle-configuration \
                --bucket "$AWS_S3_BUCKET" \
                --lifecycle-configuration '{
                    "Rules": [{
                        "ID": "BackupCleanup",
                        "Status": "Enabled",
                        "Filter": {"Prefix": "backups/"},
                        "Expiration": {"Days": '$BACKUP_RETENTION_DAYS'}
                    }]
                }' 2>> "$BACKUP_LOG" || true
            
            return 0
        else
            log_message "Upload to S3 failed"
            return 1
        fi
    else
        log_message "aws CLI not found, skipping S3 upload"
        return 1
    fi
}

# Function to clean up old local backups
cleanup_old_backups() {
    log_message "Cleaning up local backups older than $BACKUP_RETENTION_DAYS days..."
    
    # Find and remove old backup files
    local deleted_count=0
    
    # Database backups
    while IFS= read -r -d '' backup_file; do
        rm "$backup_file"
        ((deleted_count++))
        log_message "Deleted old backup: $(basename "$backup_file")"
    done < <(find "$BACKUP_DIR" -name "db_backup_*.sql*" -o -name "db_backup_*.dump" -type f -mtime +"$BACKUP_RETENTION_DAYS" -print0)
    
    # Configuration backups
    while IFS= read -r -d '' backup_file; do
        rm "$backup_file"
        ((deleted_count++))
        log_message "Deleted old backup: $(basename "$backup_file")"
    done < <(find "$BACKUP_DIR" -name "config_backup_*.tar.gz" -type f -mtime +"$BACKUP_RETENTION_DAYS" -print0)
    
    log_message "Cleaned up $deleted_count old backup files"
}

# Function to restore database from backup
restore_database() {
    local backup_file="$1"
    local target_db="${2:-$DB_NAME}"
    
    log_message "Starting database restore from: $(basename "$backup_file")"
    
    # Confirm restore operation
    if [ "${FORCE_RESTORE:-}" != "true" ]; then
        echo "WARNING: This will overwrite the database '$target_db'"
        read -p "Are you sure you want to continue? (yes/no): " confirm
        if [ "$confirm" != "yes" ]; then
            log_message "Database restore cancelled by user"
            return 1
        fi
    fi
    
    export PGPASSWORD="$DB_PASSWORD"
    
    # Drop and recreate database
    log_message "Dropping and recreating database: $target_db"
    dropdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$target_db" --if-exists 2>> "$BACKUP_LOG" || true
    createdb -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" "$target_db" 2>> "$BACKUP_LOG"
    
    # Restore from backup
    if [ "${backup_file##*.}" = "dump" ]; then
        # Custom format backup
        if pg_restore -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$target_db" \
            --verbose --clean --if-exists "$backup_file" 2>> "$BACKUP_LOG"; then
            log_message "Database restore completed successfully"
        else
            log_message "Database restore failed"
            unset PGPASSWORD
            return 1
        fi
    else
        # SQL format backup
        if [ "${backup_file##*.}" = "gz" ]; then
            # Compressed SQL backup
            if gunzip -c "$backup_file" | psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$target_db" 2>> "$BACKUP_LOG"; then
                log_message "Database restore completed successfully"
            else
                log_message "Database restore failed"
                unset PGPASSWORD
                return 1
            fi
        else
            # Uncompressed SQL backup
            if psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$target_db" < "$backup_file" 2>> "$BACKUP_LOG"; then
                log_message "Database restore completed successfully"
            else
                log_message "Database restore failed"
                unset PGPASSWORD
                return 1
            fi
        fi
    fi
    
    unset PGPASSWORD
}

# Function to run full backup procedure
run_full_backup() {
    log_message "Starting full backup procedure..."
    
    local backup_success=0
    local db_backup=""
    local config_backup=""
    
    # Database backup
    if db_backup=$(backup_database); then
        log_message "Database backup successful"
        
        # Upload to cloud storage
        if [ -n "$GCS_BUCKET" ] && upload_to_gcs "$db_backup"; then
            log_message "Database backup uploaded to GCS"
        fi
        
        if [ -n "$AWS_S3_BUCKET" ] && upload_to_s3 "$db_backup"; then
            log_message "Database backup uploaded to S3"
        fi
    else
        log_message "Database backup failed"
        backup_success=1
    fi
    
    # Configuration backup
    if config_backup=$(backup_configs); then
        log_message "Configuration backup successful"
        
        # Upload to cloud storage
        if [ -n "$GCS_BUCKET" ] && upload_to_gcs "$config_backup"; then
            log_message "Configuration backup uploaded to GCS"
        fi
        
        if [ -n "$AWS_S3_BUCKET" ] && upload_to_s3 "$config_backup"; then
            log_message "Configuration backup uploaded to S3"
        fi
    else
        log_message "Configuration backup failed"
        backup_success=1
    fi
    
    # Cleanup old backups
    cleanup_old_backups
    
    log_message "Full backup procedure completed (exit code: $backup_success)"
    return $backup_success
}

# Function to list available backups
list_backups() {
    echo "=== Local Backups ==="
    echo
    
    echo "Database backups:"
    find "$BACKUP_DIR" -name "db_backup_*" -type f | sort -r | head -10 | while read -r backup; do
        local size=$(du -h "$backup" | cut -f1)
        local date=$(stat -c %y "$backup" 2>/dev/null || stat -f %Sm "$backup")
        echo "  $(basename "$backup") - $size - $date"
    done
    
    echo
    echo "Configuration backups:"
    find "$BACKUP_DIR" -name "config_backup_*" -type f | sort -r | head -10 | while read -r backup; do
        local size=$(du -h "$backup" | cut -f1)
        local date=$(stat -c %y "$backup" 2>/dev/null || stat -f %Sm "$backup")
        echo "  $(basename "$backup") - $size - $date"
    done
}

# Function to show backup status
show_status() {
    echo "=== SyferStack V2 Backup Status ==="
    echo
    
    # Check backup directory
    if [ -d "$BACKUP_DIR" ]; then
        local backup_count=$(find "$BACKUP_DIR" -type f | wc -l)
        local backup_size=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1)
        echo "📁 Backup directory: $BACKUP_DIR"
        echo "📊 Local backups: $backup_count files ($backup_size)"
    else
        echo "❌ Backup directory not found"
    fi
    
    echo
    
    # Check recent activity
    if [ -f "$BACKUP_LOG" ]; then
        echo "📋 Recent backup activity:"
        tail -n 5 "$BACKUP_LOG"
    else
        echo "📋 No backup logs found"
    fi
    
    echo
    
    # Check cloud configuration
    echo "☁️  Cloud storage configuration:"
    if [ -n "$GCS_BUCKET" ] && command -v gsutil >/dev/null 2>&1; then
        echo "  ✅ Google Cloud Storage: gs://$GCS_BUCKET"
    else
        echo "  ❌ Google Cloud Storage: Not configured"
    fi
    
    if [ -n "$AWS_S3_BUCKET" ] && command -v aws >/dev/null 2>&1; then
        echo "  ✅ AWS S3: s3://$AWS_S3_BUCKET"
    else
        echo "  ❌ AWS S3: Not configured"
    fi
}

# Main script logic
case "${1:-help}" in
    "backup")
        run_full_backup
        ;;
    "restore")
        if [ -z "${2:-}" ]; then
            echo "Error: Backup file path required"
            echo "Usage: $0 restore <backup_file> [target_database]"
            exit 1
        fi
        restore_database "$2" "${3:-}"
        ;;
    "list")
        list_backups
        ;;
    "status")
        show_status
        ;;
    "cleanup")
        cleanup_old_backups
        ;;
    "verify")
        if [ -z "${2:-}" ]; then
            echo "Error: Backup file path required"
            echo "Usage: $0 verify <backup_file>"
            exit 1
        fi
        verify_backup "$2"
        ;;
    "help"|*)
        echo "SyferStack V2 Backup & Disaster Recovery System"
        echo ""
        echo "Usage: $0 {backup|restore|list|status|cleanup|verify|help}"
        echo ""
        echo "Commands:"
        echo "  backup                     - Run full backup (database + configs)"
        echo "  restore <file> [db_name]  - Restore database from backup file"
        echo "  list                      - List available backups"
        echo "  status                    - Show backup system status"
        echo "  cleanup                   - Remove old backups (respects retention policy)"
        echo "  verify <file>             - Verify backup integrity"
        echo "  help                      - Show this help message"
        echo ""
        echo "Environment Variables:"
        echo "  DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD - Database connection"
        echo "  GCS_BACKUP_BUCKET        - Google Cloud Storage bucket"
        echo "  AWS_BACKUP_BUCKET        - AWS S3 bucket"
        echo "  BACKUP_RETENTION_DAYS    - Backup retention period (default: 30)"
        echo "  TEST_DB_NAME             - Test database for backup verification"
        echo "  FORCE_RESTORE=true       - Skip restore confirmation prompt"
        ;;
esac