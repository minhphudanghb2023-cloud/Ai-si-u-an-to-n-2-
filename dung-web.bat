@echo off
REM EduSafe AI - Tat web dang chay an
echo Dang tat web EduSafe AI...
taskkill /F /IM pythonw.exe >nul 2>nul
taskkill /F /FI "WINDOWTITLE eq EduSafe AI - Web" >nul 2>nul
echo Xong. Web da tat (neu dang chay).
pause
