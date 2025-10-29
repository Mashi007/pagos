@echo off
REM Script para ejecutar flake8 en el proyecto

echo ============================================
echo Ejecutando Flake8 - Analisis de Codigo Python
echo ============================================
echo.

cd /d "%~dp0\.."

REM Verificar si flake8 está instalado
python -m flake8 --version >nul 2>&1
if errorlevel 1 (
    echo Flake8 no está instalado. Instalando...
    python -m pip install flake8 flake8-docstrings flake8-bugbear flake8-import-order mccabe
    if errorlevel 1 (
        echo Error al instalar flake8
        pause
        exit /b 1
    )
)

echo.
echo Analizando codigo Python...
echo.

REM Ejecutar flake8 en el directorio app
python -m flake8 app --config=.flake8 --statistics --count

echo.
echo ============================================
echo Analisis completado
echo ============================================
pause
