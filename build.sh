#!/usr/bin/env bash
# exit on error
set -o errexit

# Navegar al directorio backend si existe
if [ -d "backend" ]; then
    cd backend
fi

# Instalar dependencias
pip install --upgrade pip
pip install -r requirements.txt

# Ejecutar migraciones
# alembic upgrade head
