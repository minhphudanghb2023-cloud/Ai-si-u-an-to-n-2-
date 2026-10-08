@echo off
REM EduSafe AI - Chay web bang 1 click
cd /d "%~dp0"
echo ============================================
echo  EduSafe AI - Tro ly AI phong chong bao luc hoc duong
echo ============================================
set PY313=%LOCALAPPDATA%\Programs\Python\Python313\python.exe
if exist "%PY313%" (
  set PYTHON="%PY313%"
) else (
  set PYTHON=python
)
where python >nul 2>nul
if errorlevel 1 (
  if not exist "%PY313%" (
    echo  LOI: Khong tim thay Python. Hay cai Python va tick "Add to PATH".
    pause
    exit /b 1
  )
)
echo  Dang khoi dong web...
echo  Mo trinh duyet: http://127.0.0.1:3000/login
echo  (Giu cua so nay mo - tat di la web tat theo)
echo ============================================
echo  Cho den khi thay dong:
echo  "Running on http://127.0.0.1:3000"
echo  roi moi Refresh trinh duyet.
echo ============================================
%PYTHON% app.py
echo.
echo  Web da dung. Neu thay loi o tren, chup man hinh gui lai.
pause
