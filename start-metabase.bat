@echo off
REM ShaddAI - lanzador de Metabase (dashboards BI).
REM Incluye el fix del socket AF_UNIX (-Djdk.net.unixdomain.tmpdir) que en este
REM Windows es obligatorio para que Java 17/21 arranque el servidor.

if not exist "C:\Temp" mkdir "C:\Temp"

echo ============================================
echo   Iniciando Metabase (dashboards)...
echo   Abrira en: http://localhost:3000
echo   La primera vez tarda 1-2 minutos.
echo ============================================

cd /d %~dp0metabase
java -Djdk.net.unixdomain.tmpdir=C:\Temp -jar metabase.jar
