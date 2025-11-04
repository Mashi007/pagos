#!/bin/bash
# Script para buscar y listar todos los usos de 'any' para corrección manual

echo "🔍 Buscando todos los usos de 'any' en frontend/src..."
echo ""

# Buscar catch (error: any)
echo "📋 BLOQUES CATCH (error: any):"
grep -rn "catch.*error: any" frontend/src --include="*.ts" --include="*.tsx" | wc -l
echo ""

# Buscar as any
echo "📋 TYPE ASSERTIONS (as any):"
grep -rn "as any" frontend/src --include="*.ts" --include="*.tsx" | wc -l
echo ""

# Buscar props: any
echo "📋 PROPS (props: any):"
grep -rn "props: any\|: any)" frontend/src --include="*.ts" --include="*.tsx" | wc -l
echo ""

# Buscar parámetros any
echo "📋 PARÁMETROS (param: any):"
grep -rn ": any[,)]" frontend/src --include="*.ts" --include="*.tsx" | wc -l
echo ""

echo "✅ Búsqueda completada"

