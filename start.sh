#!/bin/bash
set -e

echo "🚀 Iniciando aplicación..."

# Navegar al directorio backend
cd backend

# Esperar a que PostgreSQL esté disponible
echo "⏳ Esperando PostgreSQL..."
max_attempts=30
attempt=0

until pg_isready -h $(echo $DATABASE_URL | sed -E 's|.*@([^:/]+).*|\1|') 2>/dev/null || [ $attempt -eq $max_attempts ]; do
  attempt=$((attempt + 1))
  echo "Intento $attempt/$max_attempts..."
  sleep 2
done

if [ $attempt -eq $max_attempts ]; then
  echo "⚠️ No se pudo conectar a PostgreSQL, continuando de todas formas..."
fi

# Ejecutar migraciones
echo "📊 Ejecutando migraciones..."
alembic upgrade head || echo "⚠️ Migraciones fallaron, continuando..."

# Inicializar datos
echo "🔧 Inicializando configuración..."
python -c "
try:
    from app.db.session import SessionLocal
    from app.db.init_db import init_db
    db = SessionLocal()
    init_db(db)
    db.close()
    print('✅ Base de datos inicializada')
except Exception as e:
    print(f'⚠️ Error inicializando BD: {e}')
" || echo "⚠️ Inicialización fallida, continuando..."

# Iniciar servidor
echo "🎯 Iniciando servidor FastAPI en puerto ${PORT:-8000}..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --log-level info
