@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\activate.bat" (
  echo Khong tim thay .venv. Hay tao moi truong theo README.md.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
start "" http://127.0.0.1:8000
python -m uvicorn src.web_app:app --host 127.0.0.1 --port 8000
pause
