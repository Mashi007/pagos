#!/bin/bash
# Script para corregir importaciones de app.config a app.core.config

echo "🔧 Corrigiendo importaciones de config en todo el proyecto..."
echo ""

# Buscar y mostrar archivos afectados
echo "📋 Archivos que necesitan corrección:"
find backend/app -type f -name "*.py" -exec grep -l "from app\.config import" {} \;
echo ""

# Confirmar antes de proceder
read -p "¿Deseas corregir estos archivos? (s/n): " confirm

if [ "$confirm" != "s" ] && [ "$confirm" != "S" ]; then
    echo "❌ Operación cancelada"
    exit 0
fi

# Realizar la corrección
echo ""
echo "🔄 Aplicando correcciones..."

find backend/app -type f -name "*.py" -exec sed -i 's/from app\.config import/from app.core.config import/g' {} \;

echo "✅ Correcciones aplicadas"
echo ""

# Verificar que no queden importaciones incorrectas
echo "🔍 Verificando correcciones..."
remaining=$(find backend/app -type f -name "*.py" -exec grep -l "from app\.config import" {} \; | wc -l)

if [ "$remaining" -eq 0 ]; then
    echo "✅ Todas las importaciones fueron corregidas exitosamente"
else
    echo "⚠️  Aún quedan $remaining archivo(s) con importaciones incorrectas:"
    find backend/app -type f -name "*.py" -exec grep -l "from app\.config import" {} \;
fi

echo ""
echo "🎯 Resumen de cambios realizados:"
echo "   - Cambiado: from app.config import → from app.core.config import"
echo ""
echo "📝 Próximos pasos:"
echo "   1. Revisar los cambios con: git diff"
echo "   2. Hacer commit de los cambios"
echo "   3. Reiniciar el servidor"
