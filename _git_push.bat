@echo off
cd /d C:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos
set GIT_INDEX_FILE=.git\index.cursor
copy /Y .git\index .git\index.cursor >nul
git add backend/app/services/notificaciones_envio_pipeline.py backend/app/services/notificaciones_prueba_paquete.py frontend/src/components/notificaciones/ConfiguracionNotificaciones.tsx frontend/src/pages/Notificaciones.tsx
if errorlevel 1 exit /b 1
git commit --trailer "Co-authored-by: Cursor <cursoragent@cursor.com>" -m "fix: replace itmaster test dest with notificaciones for CCO flow"
if errorlevel 1 exit /b 1
set GIT_INDEX_FILE=
copy /Y .git\index.cursor .git\index >nul
git push origin HEAD
git status -sb
