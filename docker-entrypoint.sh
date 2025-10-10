#!/bin/bash
set -e

echo "🔍 Verificando conexión a base de datos..."

# Función para verificar DATABASE_URL
check_database_url() {
    if [ -z "$DATABASE_URL" ]; then
        echo "❌ ERROR: DATABASE_URL no está configurada"
        echo "Variables de entorno disponibles:"
        env | grep -i "database\|postgres\|db" || echo "No se encontraron variables relacionadas"
        exit 1
    fi
    echo "✅ DATABASE_URL configurada"
}

# Función para esperar a que la base de datos esté lista
wait_for_db() {
    echo "⏳ Esperando a que PostgreSQL esté disponible..."
    
    max_attempts=30
    attempt=0
    
    while [ $attempt -lt $max_attempts ]; do
        if python -c "
import psycopg2
import os
import sys
from urllib.parse import urlparse

url = os.environ.get('DATABASE_URL', '')
if url.startswith('postgres://'):
    url = url.replace('postgres://', 'postgresql://', 1)

parsed = urlparse(url)
try:
    conn = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port,
        user=parsed.username,
        password=parsed.password,
        database=parsed.path[1:],
        connect_timeout=5
    )
    conn.close()
    sys.exit(0)
except Exception as e:
    print(f'Intento {$attempt + 1}: {e}')
    sys.exit(1)
" 2>/dev/null; then
            echo "✅ PostgreSQL está disponible"
            return 0
        fi
        
        attempt=$((attempt + 1))
        echo "Reintentando en 2 segundos... ($attempt/$max_attempts)"
        sleep 2
    done
    
    echo "❌ No se pudo conectar a PostgreSQL después de $max_attempts intentos"
    return 1
}

# Verificar DATABASE_URL
check_database_url

# Esperar a que la base de datos esté lista
wait_for_db

# Ejecutar migraciones
echo "🔄 Ejecutando migraciones de base de datos..."
if alembic upgrade head; then
    echo "✅ Migraciones completadas exitosamente"
else
    echo "❌ Error en migraciones"
    exit 1
fi

# Iniciar aplicación
echo "🚀 Iniciando aplicación en puerto ${PORT:-8080}..."
exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
