@echo off
setlocal
set PYTHONUNBUFFERED=1
cd /d "%~dp0"
if not exist "venv\Scripts\python.exe" (
  echo ERRO: ambiente nao encontrado. Execute setup.bat primeiro.
  pause
  exit /b 1
)
"venv\Scripts\python.exe" "scripts\run_server.py" %*
if not "%ERRORLEVEL%"=="0" (
  echo.
  echo O servidor encerrou com erro.
  pause
)
exit /b %ERRORLEVEL%
