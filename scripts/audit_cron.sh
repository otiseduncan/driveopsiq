#!/bin/bash

# SyferStack V2 Audit Scheduler Cron Setup
# Sets up automated nightly security audits with proper logging and error handling

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$PROJECT_ROOT/logs"
AUDIT_LOG="$LOG_DIR/audit_cron.log"
PYTHON_ENV="$PROJECT_ROOT/venv/bin/python"
AUDIT_SCRIPT="$SCRIPT_DIR/audit_automation.py"

# Create logs directory if it doesn't exist
mkdir -p "$LOG_DIR"

# Function to log messages with timestamp
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" >> "$AUDIT_LOG"
}

# Function to run audit with proper error handling
run_audit() {
    log_message "Starting scheduled security audit"
    
    # Change to project directory
    cd "$PROJECT_ROOT"
    
    # Activate virtual environment and run audit
    if [ -f "$PYTHON_ENV" ]; then
        "$PYTHON_ENV" "$AUDIT_SCRIPT" --run-once >> "$AUDIT_LOG" 2>&1
        AUDIT_STATUS=$?
    else
        # Fallback to system python
        python3 "$AUDIT_SCRIPT" --run-once >> "$AUDIT_LOG" 2>&1
        AUDIT_STATUS=$?
    fi
    
    if [ $AUDIT_STATUS -eq 0 ]; then
        log_message "Security audit completed successfully"
    else
        log_message "Security audit completed with findings (exit code: $AUDIT_STATUS)"
        
        # Send alert for critical findings (exit code 1)
        if [ $AUDIT_STATUS -eq 1 ]; then
            send_critical_alert
        fi
    fi
    
    # Rotate logs if they get too large (>10MB)
    if [ -f "$AUDIT_LOG" ] && [ $(stat -f%z "$AUDIT_LOG" 2>/dev/null || stat -c%s "$AUDIT_LOG") -gt 10485760 ]; then
        mv "$AUDIT_LOG" "${AUDIT_LOG}.old"
        log_message "Log file rotated"
    fi
}

# Function to send critical alert (if webhook is configured)
send_critical_alert() {
    if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
        curl -X POST -H 'Content-type: application/json' \
            --data '{"text":"🚨 Critical security findings detected in SyferStack V2 nightly audit. Check reports/latest.json for details."}' \
            "$SLACK_WEBHOOK_URL" >> "$AUDIT_LOG" 2>&1 || true
    fi
}

# Function to install crontab entry
install_cron() {
    local cron_schedule="${1:-0 2 * * *}"  # Default: 2 AM daily
    local cron_entry="$cron_schedule cd $PROJECT_ROOT && $SCRIPT_DIR/audit_cron.sh run >/dev/null 2>&1"
    
    # Check if cron entry already exists
    if crontab -l 2>/dev/null | grep -q "audit_cron.sh"; then
        echo "Cron job already exists. Use 'remove' to uninstall first."
        exit 1
    fi
    
    # Add new cron entry
    (crontab -l 2>/dev/null; echo "$cron_entry") | crontab -
    echo "Audit cron job installed: $cron_schedule"
    log_message "Audit cron job installed with schedule: $cron_schedule"
}

# Function to remove crontab entry
remove_cron() {
    crontab -l 2>/dev/null | grep -v "audit_cron.sh" | crontab -
    echo "Audit cron job removed"
    log_message "Audit cron job removed"
}

# Function to show cron status
show_status() {
    echo "=== SyferStack V2 Audit Scheduler Status ==="
    echo
    
    # Check if cron job exists
    if crontab -l 2>/dev/null | grep -q "audit_cron.sh"; then
        echo "✅ Cron job is installed:"
        crontab -l 2>/dev/null | grep "audit_cron.sh"
    else
        echo "❌ Cron job is not installed"
    fi
    
    echo
    
    # Check recent audit runs
    if [ -f "$AUDIT_LOG" ]; then
        echo "📋 Recent audit activity:"
        tail -n 10 "$AUDIT_LOG"
    else
        echo "📋 No audit logs found"
    fi
    
    echo
    
    # Check latest report
    if [ -f "$PROJECT_ROOT/reports/latest.json" ]; then
        echo "📊 Latest audit report:"
        python3 -c "
import json
with open('$PROJECT_ROOT/reports/latest.json') as f:
    report = json.load(f)
print(f\"Timestamp: {report['timestamp']}\")
print(f\"Total Findings: {report['total_findings']}\")
print(f\"Critical: {report['critical_findings']}\")
print(f\"High: {report['high_findings']}\")
print(f\"Medium: {report['medium_findings']}\")
print(f\"Low: {report['low_findings']}\")
" 2>/dev/null || echo "Failed to read latest report"
    else
        echo "📊 No audit reports found"
    fi
}

# Main script logic
case "${1:-help}" in
    "run")
        run_audit
        ;;
    "install")
        install_cron "${2:-0 2 * * *}"
        ;;
    "remove")
        remove_cron
        ;;
    "status")
        show_status
        ;;
    "test")
        echo "Running test audit..."
        cd "$PROJECT_ROOT"
        if [ -f "$PYTHON_ENV" ]; then
            "$PYTHON_ENV" "$AUDIT_SCRIPT" --run-once --dry-run
        else
            python3 "$AUDIT_SCRIPT" --run-once --dry-run
        fi
        ;;
    "help"|*)
        echo "SyferStack V2 Audit Scheduler"
        echo ""
        echo "Usage: $0 {install|remove|status|run|test|help}"
        echo ""
        echo "Commands:"
        echo "  install [schedule] - Install cron job (default: '0 2 * * *' = 2 AM daily)"
        echo "  remove            - Remove cron job"
        echo "  status            - Show scheduler status and recent activity"
        echo "  run              - Run audit now (used by cron)"
        echo "  test             - Run test audit without notifications"
        echo "  help             - Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0 install '0 2 * * *'    # Install daily 2 AM audit"
        echo "  $0 install '0 */6 * * *'  # Install every 6 hours"
        echo "  $0 test                   # Test audit configuration"
        ;;
esac