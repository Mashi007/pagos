#!/usr/bin/env bash
# Start Command canonico del backend en Render.
# NO usar --max-requests: el reciclado mataba hilos BG de notificaciones.
# --graceful-timeout 900: en deploy/SIGTERM el shutdown espera el lote activo.
set -euo pipefail
exec gunicorn app.main:app \
  --bind "0.0.0.0:${PORT:-10000}" \
  --workers 1 \
  --timeout 920 \
  --graceful-timeout 900 \
  --worker-class uvicorn.workers.UvicornWorker
