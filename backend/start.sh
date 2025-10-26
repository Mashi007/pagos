#!/bin/bash
set -e

echo "Ejecutando migraciones de Alembic..."
alembic upgrade head

echo "Iniciando aplicación con Gunicorn..."
exec gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT

