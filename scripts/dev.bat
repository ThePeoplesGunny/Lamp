@echo off
REM Start both backend and frontend dev servers

echo Starting Lamp dev servers...
echo   Backend:  http://localhost:8000
echo   Frontend: http://localhost:5173
echo   API Docs: http://localhost:8000/docs
echo.

start "Lamp Backend" cmd /c "cd /d %~dp0..\backend && python -m uvicorn lamp.main:app --reload --port 8000"
start "Lamp Frontend" cmd /c "cd /d %~dp0..\frontend && npm run dev"
