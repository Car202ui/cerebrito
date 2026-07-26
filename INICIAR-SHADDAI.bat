@echo off
REM ============================================================
REM   INICIAR SHADDAI - prende TODO de una vez.
REM   Doble clic en este archivo y listo.
REM ============================================================
title Iniciando ShaddAI

if not exist "C:\Temp" mkdir "C:\Temp"

echo ============================================================
echo   Prendiendo ShaddAI... (se abren 3 ventanas, NO las cierres)
echo ============================================================
echo.

REM 1) Backend (el cerebro que procesa los archivos)
start "ShaddAI - Backend"  cmd /k "cd /d %~dp0services\core && venv\Scripts\python.exe -m uvicorn main:app --port 8001"

REM 2) Frontend (la pagina web que usas)
start "ShaddAI - Web"      cmd /k "cd /d %~dp0frontend && npm run dev"

REM 3) Metabase (los dashboards)
start "ShaddAI - Metabase" cmd /k "cd /d %~dp0metabase && java -Djdk.net.unixdomain.tmpdir=C:\Temp -jar metabase.jar"

echo Esperando a que todo prenda (unos 90 segundos la primera vez)...
timeout /t 8 >nul

REM Abrir la web de ShaddAI en el navegador
start "" http://localhost:5173

echo.
echo ============================================================
echo   LISTO. ShaddAI esta prendiendo.
echo.
echo   - La web se abrio sola en: http://localhost:5173
echo   - Los dashboards (Metabase):  http://localhost:3000
echo     (Metabase tarda 1-2 min en estar listo la primera vez)
echo.
echo   Para APAGAR todo: cerra las 3 ventanas negras que se abrieron.
echo ============================================================
echo.
pause
