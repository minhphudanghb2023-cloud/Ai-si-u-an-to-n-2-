@echo off
REM EduSafe AI - Chay web an (khong can giu cua so)
cd /d "%~dp0"
echo ============================================
echo  EduSafe AI - Che do chay an
echo ============================================
powershell -NoProfile -Command "$t=New-Object Net.Sockets.TcpClient; try { $t.Connect('127.0.0.1',3000); exit 0 } catch { exit 1 }" >nul 2>nul
if %errorlevel%==0 (
  echo  Web DANG CHAY roi: http://127.0.0.1:3000/login
  pause
  exit /b 0
)
echo  Dang khoi dong web...
set PYW313=%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe
if exist "%PYW313%" (
  start "" "%PYW313%" app.py
) else (
  start "" pythonw.exe app.py
)

timeout /t 7 /nobreak >nul
powershell -NoProfile -Command "$t=New-Object Net.Sockets.TcpClient; try { $t.Connect('127.0.0.1',3000); exit 0 } catch { exit 1 }" >nul 2>nul
if %errorlevel%==0 (
  echo  XONG! Mo trinh duyet: http://127.0.0.1:3000/login
  echo  Cua so nay co the TAT DI, web van chay.
  echo  Muon tat web: chay file dung-web.bat
) else (
  echo  LOI: Web khong khoi dong duoc. Hay chay run.bat de xem loi chi tiet.
)
pause
