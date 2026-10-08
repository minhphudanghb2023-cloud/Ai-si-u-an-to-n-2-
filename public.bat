@echo off
REM EduSafe AI - Chay web + mo tunnel cong khai (1 click)
cd /d "%~dp0"
echo ============================================
echo  EduSafe AI - Mo web cong khai
echo ============================================
echo [1/2] Khoi dong web (port 3000)...
start "EduSafe AI - Web" "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" app.py
timeout /t 7 /nobreak >nul
echo [2/2] Mo tunnel cong khai...
echo  URL se hien thi dong "your url is: ..."
"C:\Program Files\nodejs\npx.cmd" -y localtunnel --port 3000 --subdomain edusafeai-vmb
pause
