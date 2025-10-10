#!/bin/bash
# Script de corrección para errores de Pydantic v2
# Fecha: 2025-10-10

echo "=================================="
echo "🔧 CORRECCIÓN DE ERRORES PYDANTIC V2"
echo "=================================="
echo ""

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Paso 1: Detener el servidor
echo -e "${YELLOW}📌 Paso 1: Deteniendo servidor...${NC}"
docker-compose down 2>/dev/null || echo "No hay contenedores corriendo"
echo ""

# Paso 2: Limpiar caché de Python
echo -e "${YELLOW}📌 Paso 2: Limpiando caché de Python...${NC}"
find backend -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find backend -type f -name "*.pyc" -delete 2>/dev/null
find backend -type f -name "*.pyo" -delete 2>/dev/null
find backend -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null
echo -e "${GREEN}✓ Caché eliminada${NC}"
echo ""

# Paso 3: Crear respaldos
echo -e "${YELLOW}📌 Paso 3: Creando respaldos...${NC}"
BACKUP_DIR="backend/backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp backend/app/schemas/prestamo.py "$BACKUP_DIR/prestamo.py.backup" 2>/dev/null && echo -e "${GREEN}✓ Respaldo de prestamo.py creado${NC}"
cp backend/app/schemas/pago.py "$BACKUP_DIR/pago.py.backup" 2>/dev/null && echo -e "${GREEN}✓ Respaldo de pago.py creado${NC}"
echo ""

# Paso 4: Aplicar correcciones
echo -e "${YELLOW}📌 Paso 4: Aplicando correcciones...${NC}"

# Nota: Los archivos corregidos deben estar en el mismo directorio que este script
if [ -f "prestamo.py" ] && [ -f "pago.py" ]; then
    cp prestamo.py backend/app/schemas/prestamo.py
    echo -e "${GREEN}✓ prestamo.py actualizado${NC}"
    
    cp pago.py backend/app/schemas/pago.py
    echo -e "${GREEN}✓ pago.py actualizado${NC}"
else
    echo -e "${RED}✗ Archivos corregidos no encontrados${NC}"
    echo "  Asegúrate de que prestamo.py y pago.py estén en el mismo directorio"
    exit 1
fi
echo ""

# Paso 5: Verificar sintaxis Python
echo -e "${YELLOW}📌 Paso 5: Verificando sintaxis...${NC}"
python3 -m py_compile backend/app/schemas/prestamo.py 2>/dev/null && echo -e "${GREEN}✓ prestamo.py: sintaxis correcta${NC}" || echo -e "${RED}✗ prestamo.py: error de sintaxis${NC}"
python3 -m py_compile backend/app/schemas/pago.py 2>/dev/null && echo -e "${GREEN}✓ pago.py: sintaxis correcta${NC}" || echo -e "${RED}✗ pago.py: error de sintaxis${NC}"
echo ""

# Paso 6: Reconstruir contenedor (si se usa Docker)
echo -e "${YELLOW}📌 Paso 6: Reconstruyendo contenedor...${NC}"
if [ -f "docker-compose.yml" ]; then
    docker-compose build backend --no-cache
    echo -e "${GREEN}✓ Contenedor reconstruido${NC}"
else
    echo -e "${YELLOW}⚠ docker-compose.yml no encontrado, saltando...${NC}"
fi
echo ""

# Paso 7: Iniciar servidor
echo -e "${YELLOW}📌 Paso 7: Iniciando servidor...${NC}"
if [ -f "docker-compose.yml" ]; then
    docker-compose up -d
    echo ""
    echo -e "${GREEN}✓ Servidor iniciado${NC}"
    echo ""
    echo -e "${YELLOW}📋 Verificando logs...${NC}"
    echo "Esperando 5 segundos para que el servidor inicie..."
    sleep 5
    docker-compose logs --tail=50 backend
else
    echo -e "${YELLOW}⚠ Inicia manualmente con: uvicorn app.main:app --reload${NC}"
fi
echo ""

echo "=================================="
echo -e "${GREEN}✅ CORRECCIÓN COMPLETADA${NC}"
echo "=================================="
echo ""
echo "📝 Próximos pasos:"
echo "   1. Revisa los logs arriba para confirmar que no hay errores"
echo "   2. Si ves errores, ejecuta: docker-compose logs -f backend"
echo "   3. Prueba los endpoints en: http://localhost:8000/docs"
echo ""
echo "📁 Respaldos guardados en: $BACKUP_DIR"
echo ""
