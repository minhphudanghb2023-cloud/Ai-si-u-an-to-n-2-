@echo off
REM EduSafe AI - Cai dat tu chay web moi khi mo may
cd /d "%~dp0"
set "TARGET=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\EduSafeAI.vbs"
> "%TARGET%" echo Set WshShell = CreateObject("WScript.Shell")
>>"%TARGET%" echo WshShell.CurrentDirectory = "%~dp0"
>>"%TARGET%" echo WshShell.Run """%LOCALAPPDATA%\Programs\Python\Python313\pythonw.exe"" app.py", 0, False
echo ============================================
echo  Da cai dat xong!
echo  Moi lan mo may, web EduSafe AI se tu chay an.
echo  Truy cap: http://127.0.0.1:3000/login
echo  Muon go bo: chay file go-tu-chay.bat
echo ============================================
pause
