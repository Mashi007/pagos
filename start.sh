#!/bin/bash

echo "🚀 Iniciando aplicación..."

# Navegar al directorio backend
cd backend

# Ejecutar migraciones de Alembic
echo "📊 Ejecutando migraciones de base de datos..."
alembic upgrade head

# Inicializar datos si es necesario
echo "🔧 Inicializando configuración..."
python -c "
from app.db.session import SessionLocal
from app.db.init_db import init_db

db = SessionLocal()
try:
    init_db(db)
    print('✅ Base de datos inicializada')
except Exception as e:
    print(f'⚠️ Error inicializando BD: {e}')
finally:
    db.close()
"

# Iniciar servidor
echo "🎯 Iniciando servidor FastAPI..."
uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2
