@echo off
REM EduSafe AI - Backup du lieu ngay 1 click
cd /d "%~dp0"
echo ============================================
echo  EduSafe AI - Backup du lieu
echo ============================================
echo.
echo Dang backup database...
"%LOCALAPPDATA%\Programs\Python\Python313\python.exe" -c "import backup; result = backup.backup_database(backup_type='manual'); print('OK!' if result['success'] else 'LOI: ' + str(result.get('error', 'Unknown')))"
echo.
echo Backup thanh cong! Kiem tra thu muc:
echo   - Local: %~dp0backups
echo   - OneDrive: %USERPROFILE%\OneDrive\EduSafe_Backup
echo.
pause
