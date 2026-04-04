@echo off
echo ============================================
echo   CyberGuard AI - Starting Backend Server
echo ============================================
echo.
echo [1/2] Installing dependencies...
pip install -r requirements.txt
echo.
echo [2/2] Starting FastAPI server...
echo.
echo  Open your browser at: http://127.0.0.1:8000
echo  Press Ctrl+C to stop the server.
echo.
uvicorn main:app --reload --host 127.0.0.1 --port 8000
pause
