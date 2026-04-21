@echo off
echo Running AI Audit Harness...
echo ================================
wsl bash -c "cd /home/otis/SyferStackV2 && chmod +x ai_audit.sh && ./ai_audit.sh"
echo.
echo ================================
echo Audit complete. Check .ai_patches/ directory for generated fixes.
pause