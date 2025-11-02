#!/bin/bash
# ============================================
# ACTUALIZAR COLUMNA: cedula_cliente → cedula
# ============================================
# Script Bash para Linux/Mac que actualiza todas las referencias
# de cedula_cliente a cedula en los archivos del proyecto
# ============================================

echo "============================================"
echo "ACTUALIZAR COLUMNA: cedula_cliente → cedula"
echo "============================================"
echo ""

# Directorio base del proyecto
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Archivos a actualizar (solo archivos Python y TypeScript)
FILES=(
    "$PROJECT_ROOT/backend/app/models/pago.py"
    "$PROJECT_ROOT/backend/app/schemas/pago.py"
    "$PROJECT_ROOT/backend/app/api/v1/endpoints/pagos.py"
    "$PROJECT_ROOT/backend/app/api/v1/endpoints/pagos_upload.py"
    "$PROJECT_ROOT/frontend/src/services/pagoService.ts"
)

# Contador de cambios
TOTAL_CHANGES=0

echo "Archivos a procesar:"
for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ⚠️ $file (NO ENCONTRADO)"
    fi
done
echo ""

# Preguntar confirmación
read -p "¿Continuar con la actualización? (S/N): " confirm
if [ "$confirm" != "S" ] && [ "$confirm" != "s" ]; then
    echo "Operación cancelada."
    exit 0
fi

echo ""
echo "Procesando archivos..."
echo ""

# Procesar cada archivo
for file_path in "${FILES[@]}"; do
    if [ ! -f "$file_path" ]; then
        echo "⚠️ Archivo no encontrado: $file_path"
        continue
    fi

    echo "Procesando: $file_path"
    
    # Crear backup
    cp "$file_path" "$file_path.backup"
    echo "  💾 Backup creado: $file_path.backup"
    
    # Contar cambios antes
    CHANGES_BEFORE=$(grep -o "cedula_cliente" "$file_path" | wc -l)
    
    # Reemplazos específicos para cada tipo de archivo
    if [[ "$file_path" == *.py ]]; then
        # Python: Reemplazar referencias de la columna
        sed -i.tmp \
            -e 's/Pago\.cedula_cliente/Pago.cedula/g' \
            -e 's/pago\.cedula_cliente/pago.cedula/g' \
            -e 's/pago_data\.cedula_cliente/pago_data.cedula/g' \
            -e 's/self\.cedula_cliente/self.cedula/g' \
            -e 's/cedula_cliente = Column(/cedula = Column(/g' \
            -e 's/cedula_cliente: str =/cedula: str =/g' \
            -e 's/cedula_cliente=/cedula=/g' \
            "$file_path"
        rm -f "$file_path.tmp"
    fi
    
    if [[ "$file_path" == *.ts ]] || [[ "$file_path" == *.tsx ]]; then
        # TypeScript: Reemplazar en interfaces y tipos
        sed -i.tmp 's/cedula_cliente: string/cedula: string/g' "$file_path"
        rm -f "$file_path.tmp"
    fi
    
    # Contar cambios después
    CHANGES_AFTER=$(grep -o "cedula_cliente" "$file_path" | wc -l)
    CHANGES=$((CHANGES_BEFORE - CHANGES_AFTER))
    TOTAL_CHANGES=$((TOTAL_CHANGES + CHANGES))
    
    if [ $CHANGES -gt 0 ]; then
        echo "  ✅ Actualizado ($CHANGES cambios)"
    else
        echo "  ⏭️ Sin cambios necesarios"
    fi
done

echo ""
echo "============================================"
echo "RESUMEN"
echo "============================================"
echo "Total de cambios realizados: $TOTAL_CHANGES"
echo ""
echo "⚠️ IMPORTANTE:"
echo "1. Los archivos SQL NO se actualizaron automáticamente"
echo "2. Revisa manualmente los archivos modificados"
echo "3. Prueba la aplicación antes de hacer commit"
echo ""
echo "✅ Archivos de backup creados con extensión .backup"
echo ""

