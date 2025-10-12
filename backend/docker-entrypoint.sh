#!/bin/bash
set -e

echo "=========================================="
echo "🚀 Iniciando Sistema de Pagos"
echo "=========================================="

# Función para esperar DATABASE_URL
wait_for_database_url() {
    echo "⏳ Esperando DATABASE_URL..."
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if [ ! -z "$DATABASE_URL" ]; then
            echo "✅ DATABASE_URL encontrada en intento $attempt"
            # Mostrar info de conexión (sin credenciales)
            local host=$(echo $DATABASE_URL | grep -oP '(?<=@)[^:/]+' || echo 'unknown')
            local port=$(echo $DATABASE_URL | grep -oP '(?<=:)\d+(?=/)' || echo '5432')
            echo "🔗 Conectando a: $host:$port"
            return 0
        fi
        
        echo "Intento $attempt/$max_attempts - DATABASE_URL no disponible aún..."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    echo "❌ ERROR: DATABASE_URL no disponible después de $max_attempts intentos"
    echo "📋 Variables de entorno disponibles relacionadas con DB:"
    env | grep -iE "postgres|database|railway" || echo "  Ninguna variable de DB encontrada"
    return 1
}

# Esperar a que DATABASE_URL esté disponible
if ! wait_for_database_url; then
    echo ""
    echo "❌ FALLO CRÍTICO: No se puede continuar sin DATABASE_URL"
    echo ""
    echo "Verifica en Railway:"
    echo "  1. Settings > Variables > DATABASE_URL debe existir"
    echo "  2. O conecta el servicio PostgreSQL"
    exit 1
fi

# Normalizar URL (postgres:// -> postgresql://)
if echo "$DATABASE_URL" | grep -q "^postgres://"; then
    export DATABASE_URL=$(echo "$DATABASE_URL" | sed 's/^postgres:\/\//postgresql:\/\//')
    echo "✅ URL normalizada a postgresql://"
fi

# Ejecutar migraciones con reintentos
echo ""
echo "🔄 Ejecutando migraciones de Alembic..."
max_migration_attempts=3
migration_attempt=1

while [ $migration_attempt -le $max_migration_attempts ]; do
    echo "📝 Intento de migración $migration_attempt de $max_migration_attempts..."
    
    if alembic upgrade head 2>&1; then
        echo "✅ Migraciones completadas exitosamente"
        break
    else
        if [ $migration_attempt -eq $max_migration_attempts ]; then
            echo ""
            echo "❌ ERROR: Migraciones fallaron después de $max_migration_attempts intentos"
            echo "Posibles causas:"
            echo "  - Base de datos no accesible"
            echo "  - Credenciales incorrectas"
            echo "  - Error en archivos de migración"
            echo ""
            exit 1
        fi
        echo "⚠️  Intento fallido, reintentando en 5 segundos..."
        sleep 5
        migration_attempt=$((migration_attempt + 1))
    fi
done

# Iniciar aplicación
echo ""
echo "=========================================="
echo "🚀 Iniciando aplicación FastAPI"
echo "=========================================="
echo "📍 Host: 0.0.0.0"
echo "🔌 Puerto: ${PORT:-8080}"
echo "👷 Workers: 1"
echo "📊 Log level: info"
echo "=========================================="
echo ""

exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8080}" \
    --workers 1 \
    --log-level info

