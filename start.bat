@echo off
REM ShaddAI - levanta backend + frontend en una sola corrida.
REM Uso: doble clic en este archivo, o ejecutar "start.bat" en la terminal.

echo ============================================
echo   Iniciando ShaddAI...
echo ============================================

REM Backend (FastAPI) en una ventana nueva
start "ShaddAI Backend" cmd /k "cd /d %~dp0services\core && venv\Scripts\python.exe -m uvicorn main:app --port 8001"

REM Frontend (React/Vite) en otra ventana nueva
start "ShaddAI Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo Backend:  http://localhost:8001
echo Frontend: http://localhost:5173
echo.
echo (Ollama arranca solo con Windows)
echo Cierra las dos ventanas que se abrieron para detener ShaddAI.
