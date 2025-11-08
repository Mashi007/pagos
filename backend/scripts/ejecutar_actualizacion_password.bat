@echo off
REM Script para actualizar contraseña de usuario en la base de datos (Windows)
REM Uso: ejecutar_actualizacion_password.bat <email> <password>

if "%1"=="" (
    echo Uso: %0 ^<email^> ^<password^>
    echo.
    echo Ejemplo:
    echo   %0 itmaster@rapicreditca.com Casa1803+
    exit /b 1
)

if "%2"=="" (
    echo Error: Falta la contraseña
    echo Uso: %0 ^<email^> ^<password^>
    exit /b 1
)

set EMAIL=%1
set PASSWORD=%2

echo Actualizando contraseña para: %EMAIL%
echo.

REM Ejecutar script Python que actualiza directamente en BD
python scripts\cambiar_password_usuario.py %EMAIL% %PASSWORD%

if %ERRORLEVEL% EQU 0 (
    echo.
    echo Contraseña actualizada exitosamente
    echo.
    echo Ahora puedes iniciar sesion con:
    echo   Email: %EMAIL%
    echo   Contraseña: %PASSWORD%
) else (
    echo.
    echo Error al actualizar contraseña
    exit /b 1
)

