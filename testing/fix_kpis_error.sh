#!/bin/bash

# Script de verificación y corrección del error ModuleNotFoundError
# Para el proyecto backend con FastAPI

echo "======================================"
echo "Script de Corrección - Error KPIs"
echo "======================================"
echo ""

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Variables
BACKEND_PATH="backend/app/schemas"
KPIS_FILE="$BACKEND_PATH/kpis.py"
INIT_FILE="$BACKEND_PATH/__init__.py"

echo "🔍 Paso 1: Verificando estructura del proyecto..."
if [ -d "$BACKEND_PATH" ]; then
    echo -e "${GREEN}✓ Directorio schemas encontrado${NC}"
else
    echo -e "${RED}✗ Error: No se encuentra el directorio $BACKEND_PATH${NC}"
    exit 1
fi

echo ""
echo "🔍 Paso 2: Verificando archivo kpis.py..."
if [ -f "$KPIS_FILE" ]; then
    echo -e "${YELLOW}⚠ El archivo kpis.py ya existe${NC}"
    echo "¿Desea respaldarlo? (s/n)"
    read -r response
    if [[ "$response" =~ ^([sS])$ ]]; then
        cp "$KPIS_FILE" "${KPIS_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
        echo -e "${GREEN}✓ Backup creado${NC}"
    fi
else
    echo -e "${YELLOW}⚠ El archivo kpis.py no existe, será creado${NC}"
fi

echo ""
echo "🔧 Paso 3: Copiando archivo kpis.py..."
if [ -f "kpis.py" ]; then
    cp kpis.py "$KPIS_FILE"
    echo -e "${GREEN}✓ Archivo kpis.py copiado exitosamente${NC}"
else
    echo -e "${RED}✗ Error: No se encuentra el archivo kpis.py de origen${NC}"
    exit 1
fi

echo ""
echo "🔍 Paso 4: Verificando permisos..."
chmod 644 "$KPIS_FILE"
echo -e "${GREEN}✓ Permisos configurados correctamente${NC}"

echo ""
echo "🔍 Paso 5: Verificando sintaxis de Python..."
if python3 -m py_compile "$KPIS_FILE"; then
    echo -e "${GREEN}✓ Sintaxis de kpis.py es válida${NC}"
else
    echo -e "${RED}✗ Error en la sintaxis de kpis.py${NC}"
    exit 1
fi

echo ""
echo "🔧 Paso 6: Verificando importaciones en __init__.py..."
if grep -q "from app.schemas.kpis import" "$INIT_FILE"; then
    echo -e "${GREEN}✓ Las importaciones de KPIs están presentes en __init__.py${NC}"
else
    echo -e "${YELLOW}⚠ Las importaciones de KPIs no están en __init__.py${NC}"
    echo "Se recomienda agregar las importaciones manualmente"
fi

echo ""
echo "🧪 Paso 7: Probando importación..."
cd "$(dirname "$BACKEND_PATH")/../.." || exit 1
if python3 -c "from app.schemas.kpis import KPIBase; print('✓ Importación exitosa')" 2>/dev/null; then
    echo -e "${GREEN}✓ El módulo kpis se importa correctamente${NC}"
else
    echo -e "${RED}✗ Error al importar el módulo kpis${NC}"
    echo "Verifica el PYTHONPATH y la estructura del proyecto"
fi

echo ""
echo "======================================"
echo "Resumen de la corrección:"
echo "======================================"
echo "✓ Archivo kpis.py creado/actualizado"
echo "✓ Permisos configurados"
echo "✓ Sintaxis verificada"
echo ""
echo "📋 Próximos pasos:"
echo "1. Reinicia el servidor de desarrollo:"
echo "   cd backend && uvicorn app.main:app --reload"
echo ""
echo "2. Verifica los logs para confirmar que no hay errores"
echo ""
echo "3. Prueba los endpoints de KPIs si existen"
echo ""
echo -e "${GREEN}✓ Proceso completado${NC}"
