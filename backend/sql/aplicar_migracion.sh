#!/bin/bash
# ============================================================================
# Script para aplicar migración de índices a BD de producción
# Uso: bash aplicar_migracion.sh
# ============================================================================

set -e

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}═══════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}MIGRACIÓN: Crear índices para optimizar APIs públicas${NC}"
echo -e "${YELLOW}Fecha: 2026-03-30${NC}"
echo -e "${YELLOW}═══════════════════════════════════════════════════════════${NC}"
echo ""

# Verificar que DATABASE_URL está configurada
if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}ERROR: DATABASE_URL no está configurada${NC}"
    echo "Configura: export DATABASE_URL='postgresql://user:pass@host/db'"
    exit 1
fi

echo -e "${GREEN}✓ DATABASE_URL detectada${NC}"
echo ""

# Conectar y ejecutar migración
echo -e "${YELLOW}Ejecutando migración de índices...${NC}"
echo ""

psql "$DATABASE_URL" << 'EOF'

-- 1. Índice: Búsqueda rápida de clientes por cédula
CREATE INDEX IF NOT EXISTS idx_cliente_cedula ON clientes (cedula)
WHERE cedula IS NOT NULL;
SELECT 'idx_cliente_cedula creado' as status;

-- 2. Índice: Códigos de estado de cuenta activos
CREATE INDEX IF NOT EXISTS idx_estado_cuenta_codigo_cedula_activo 
ON estado_cuenta_codigos (cedula_normalizada, usado, expira_en)
WHERE usado = FALSE;
SELECT 'idx_estado_cuenta_codigo_cedula_activo creado' as status;

-- 3. Índice: Préstamos por cliente y estado APROBADO
CREATE INDEX IF NOT EXISTS idx_prestamo_cliente_estado 
ON prestamos (cliente_id, estado)
WHERE estado = 'APROBADO';
SELECT 'idx_prestamo_cliente_estado creado' as status;

-- 4. Índice: Pagos reportados por cédula y estado
CREATE INDEX IF NOT EXISTS idx_pago_reportado_cedula_estado 
ON pagos_reportados (tipo_cedula, numero_cedula, estado);
SELECT 'idx_pago_reportado_cedula_estado creado' as status;

-- 5. Índice: Cuotas por préstamo
CREATE INDEX IF NOT EXISTS idx_cuota_prestamo 
ON cuotas (prestamo_id, numero_cuota)
WHERE estado != 'CANCELADA';
SELECT 'idx_cuota_prestamo creado' as status;

-- Verificación final
SELECT 
    COUNT(*) as total_indices_creados,
    NOW() as timestamp
FROM pg_indexes
WHERE indexname IN (
    'idx_cliente_cedula',
    'idx_estado_cuenta_codigo_cedula_activo',
    'idx_prestamo_cliente_estado',
    'idx_pago_reportado_cedula_estado',
    'idx_cuota_prestamo'
);

EOF

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✓ MIGRACIÓN COMPLETADA EXITOSAMENTE${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${GREEN}Índices creados:${NC}"
    echo "  1. idx_cliente_cedula (clientes)"
    echo "  2. idx_estado_cuenta_codigo_cedula_activo (estado_cuenta_codigos)"
    echo "  3. idx_prestamo_cliente_estado (prestamos)"
    echo "  4. idx_pago_reportado_cedula_estado (pagos_reportados)"
    echo "  5. idx_cuota_prestamo (cuotas)"
    echo ""
    echo -e "${YELLOW}Próximos pasos:${NC}"
    echo "  1. Ejecutar VACUUM ANALYZE en BD:"
    echo "     psql \$DATABASE_URL -c 'VACUUM ANALYZE;'"
    echo ""
    echo "  2. Verificar performance con EXPLAIN:"
    echo "     psql \$DATABASE_URL < sql/033_MIGRACION_INDICES_PUBLICOS_2026_03_30.sql"
    echo ""
    echo "  3. Monitorear en próximas 24h:"
    echo "     - Latencia en /validar-cedula"
    echo "     - Latencia en /recibo-cuota"
    echo "     - Latencia en pagos-reportados/listado-y-kpis"
    echo ""
else
    echo -e "${RED}ERROR: Falló la migración${NC}"
    exit 1
fi
