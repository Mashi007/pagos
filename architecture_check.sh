#!/bin/bash
# architecture_check.sh - Script de verificación de arquitectura
# Cumple con normativas de desarrollo para identificación rápida de problemas

echo "🏗️ VERIFICACIÓN DE ARQUITECTURA BACKEND - $(date)"
echo "=================================================="

# Configuración
BACKEND_DIR="backend/app"
MODELS_DIR="$BACKEND_DIR/models"
SCHEMAS_DIR="$BACKEND_DIR/schemas"
SERVICES_DIR="$BACKEND_DIR/services"
UTILS_DIR="$BACKEND_DIR/utils"

# Contadores de problemas
ARCHITECTURE_ISSUES=0
DESIGN_ISSUES=0
MAINTAINABILITY_ISSUES=0
PERFORMANCE_ISSUES=0

# Función para reportar problemas
report_issue() {
    local category=$1
    local message=$2
    local code=$3
    
    case $category in
        "ARCHITECTURE")
            echo "🏗️ ARQUITECTURA: $message [$code]"
            ((ARCHITECTURE_ISSUES++))
            ;;
        "DESIGN")
            echo "🎨 DISEÑO: $message [$code]"
            ((DESIGN_ISSUES++))
            ;;
        "MAINTAINABILITY")
            echo "🔧 MANTENIBILIDAD: $message [$code]"
            ((MAINTAINABILITY_ISSUES++))
            ;;
        "PERFORMANCE")
            echo "⚡ PERFORMANCE: $message [$code]"
            ((PERFORMANCE_ISSUES++))
            ;;
    esac
}

# Función para reportar éxito
report_success() {
    local message=$1
    echo "✅ $message"
}

echo ""
echo "1. VERIFICANDO ESTRUCTURA DE MODELOS..."
echo "--------------------------------------"

# Verificar relaciones comentadas
if [ -d "$MODELS_DIR" ]; then
    COMMENTED_RELATIONS=$(grep -r "relationship.*COMENTADO" "$MODELS_DIR" 2>/dev/null | wc -l)
    if [ $COMMENTED_RELATIONS -gt 0 ]; then
        report_issue "ARCHITECTURE" "Se encontraron $COMMENTED_RELATIONS relaciones comentadas" "ARCH-001"
        echo "   📍 Archivos con relaciones comentadas:"
        grep -r "relationship.*COMENTADO" "$MODELS_DIR" 2>/dev/null | cut -d: -f1 | sort -u | while read file; do
            echo "   📁 $file"
        done
    else
        report_success "No hay relaciones comentadas en modelos"
    fi
    
    # Verificar modelos sin relaciones
    MODELS_WITHOUT_RELATIONS=0
    for model_file in "$MODELS_DIR"/*.py; do
        if [ -f "$model_file" ] && [ "$(basename "$model_file")" != "__init__.py" ]; then
            RELATION_COUNT=$(grep -c "relationship" "$model_file" 2>/dev/null)
            if [ $RELATION_COUNT -eq 0 ]; then
                echo "   ⚠️ Modelo sin relaciones: $(basename "$model_file")"
                ((MODELS_WITHOUT_RELATIONS++))
            fi
        fi
    done
    
    if [ $MODELS_WITHOUT_RELATIONS -gt 0 ]; then
        report_issue "DESIGN" "Se encontraron $MODELS_WITHOUT_RELATIONS modelos sin relaciones" "ARCH-002"
    fi
else
    report_issue "ARCHITECTURE" "Directorio de modelos no encontrado: $MODELS_DIR" "ARCH-003"
fi

echo ""
echo "2. VERIFICANDO ESQUEMAS PYDANTIC..."
echo "---------------------------------"

# Verificar complejidad de esquemas
if [ -d "$SCHEMAS_DIR" ]; then
    INIT_FILE="$SCHEMAS_DIR/__init__.py"
    if [ -f "$INIT_FILE" ]; then
        INIT_LINES=$(wc -l < "$INIT_FILE")
        if [ $INIT_LINES -gt 100 ]; then
            report_issue "MAINTAINABILITY" "Archivo __init__.py muy complejo ($INIT_LINES líneas)" "ARCH-004"
            echo "   📍 Recomendación: Dividir en módulos más pequeños"
        else
            report_success "Archivo __init__.py de tamaño adecuado ($INIT_LINES líneas)"
        fi
        
        # Verificar imports excesivos
        IMPORT_COUNT=$(grep -c "^from\|^import" "$INIT_FILE" 2>/dev/null)
        if [ $IMPORT_COUNT -gt 20 ]; then
            report_issue "MAINTAINABILITY" "Demasiados imports en __init__.py ($IMPORT_COUNT)" "ARCH-005"
        else
            report_success "Número de imports adecuado ($IMPORT_COUNT)"
        fi
    fi
    
    # Verificar archivos de esquemas individuales
    SCHEMA_FILES=$(find "$SCHEMAS_DIR" -name "*.py" -not -name "__init__.py" | wc -l)
    if [ $SCHEMA_FILES -gt 0 ]; then
        report_success "Se encontraron $SCHEMA_FILES archivos de esquemas individuales"
        
        # Verificar esquemas muy grandes
        for schema_file in "$SCHEMAS_DIR"/*.py; do
            if [ -f "$schema_file" ] && [ "$(basename "$schema_file")" != "__init__.py" ]; then
                SCHEMA_LINES=$(wc -l < "$schema_file")
                if [ $SCHEMA_LINES -gt 200 ]; then
                    report_issue "MAINTAINABILITY" "Esquema muy grande: $(basename "$schema_file") ($SCHEMA_LINES líneas)" "ARCH-006"
                fi
            fi
        done
    fi
else
    report_issue "ARCHITECTURE" "Directorio de esquemas no encontrado: $SCHEMAS_DIR" "ARCH-007"
fi

echo ""
echo "3. VERIFICANDO SERVICIOS Y UTILIDADES..."
echo "---------------------------------------"

# Verificar servicios
if [ -d "$SERVICES_DIR" ]; then
    SERVICE_FILES=$(find "$SERVICES_DIR" -name "*.py" -not -name "__init__.py" | wc -l)
    if [ $SERVICE_FILES -gt 0 ]; then
        report_success "Se encontraron $SERVICE_FILES archivos de servicios"
        
        # Verificar servicios muy grandes
        for service_file in "$SERVICES_DIR"/*.py; do
            if [ -f "$service_file" ] && [ "$(basename "$service_file")" != "__init__.py" ]; then
                SERVICE_LINES=$(wc -l < "$service_file")
                if [ $SERVICE_LINES -gt 300 ]; then
                    report_issue "MAINTAINABILITY" "Servicio muy grande: $(basename "$service_file") ($SERVICE_LINES líneas)" "ARCH-008"
                fi
            fi
        done
    else
        report_issue "DESIGN" "No se encontraron archivos de servicios" "ARCH-009"
    fi
else
    report_issue "ARCHITECTURE" "Directorio de servicios no encontrado: $SERVICES_DIR" "ARCH-010"
fi

# Verificar utilidades
if [ -d "$UTILS_DIR" ]; then
    UTIL_FILES=$(find "$UTILS_DIR" -name "*.py" -not -name "__init__.py" | wc -l)
    if [ $UTIL_FILES -gt 0 ]; then
        report_success "Se encontraron $UTIL_FILES archivos de utilidades"
    else
        report_issue "DESIGN" "No se encontraron archivos de utilidades" "ARCH-011"
    fi
else
    report_issue "ARCHITECTURE" "Directorio de utilidades no encontrado: $UTILS_DIR" "ARCH-012"
fi

echo ""
echo "4. VERIFICANDO PATRONES DE DISEÑO..."
echo "----------------------------------"

# Verificar uso de patrones comunes
PATTERNS_FOUND=0

# Verificar Factory Pattern
if grep -r "class.*Factory" "$BACKEND_DIR" 2>/dev/null | grep -q "Factory"; then
    echo "   ✅ Factory Pattern detectado"
    ((PATTERNS_FOUND++))
fi

# Verificar Repository Pattern
if grep -r "class.*Repository" "$BACKEND_DIR" 2>/dev/null | grep -q "Repository"; then
    echo "   ✅ Repository Pattern detectado"
    ((PATTERNS_FOUND++))
fi

# Verificar Service Pattern
if grep -r "class.*Service" "$BACKEND_DIR" 2>/dev/null | grep -q "Service"; then
    echo "   ✅ Service Pattern detectado"
    ((PATTERNS_FOUND++))
fi

# Verificar Dependency Injection
if grep -r "Depends(" "$BACKEND_DIR" 2>/dev/null | grep -q "Depends"; then
    echo "   ✅ Dependency Injection detectado"
    ((PATTERNS_FOUND++))
fi

if [ $PATTERNS_FOUND -eq 0 ]; then
    report_issue "DESIGN" "No se detectaron patrones de diseño comunes" "ARCH-013"
else
    report_success "Se detectaron $PATTERNS_FOUND patrones de diseño"
fi

echo ""
echo "5. VERIFICANDO SEPARACIÓN DE RESPONSABILIDADES..."
echo "-----------------------------------------------"

# Verificar que los endpoints no contengan lógica de negocio
ENDPOINTS_DIR="$BACKEND_DIR/api/v1/endpoints"
if [ -d "$ENDPOINTS_DIR" ]; then
    ENDPOINT_FILES=$(find "$ENDPOINTS_DIR" -name "*.py" -not -name "__init__.py" | wc -l)
    BUSINESS_LOGIC_IN_ENDPOINTS=0
    
    for endpoint_file in "$ENDPOINTS_DIR"/*.py; do
        if [ -f "$endpoint_file" ] && [ "$(basename "$endpoint_file")" != "__init__.py" ]; then
            # Verificar si hay lógica de negocio compleja en endpoints
            COMPLEX_LOGIC=$(grep -c -E "(if.*len|for.*in|while|try.*except)" "$endpoint_file" 2>/dev/null)
            if [ $COMPLEX_LOGIC -gt 5 ]; then
                echo "   ⚠️ Endpoint con lógica compleja: $(basename "$endpoint_file")"
                ((BUSINESS_LOGIC_IN_ENDPOINTS++))
            fi
        fi
    done
    
    if [ $BUSINESS_LOGIC_IN_ENDPOINTS -gt 0 ]; then
        report_issue "DESIGN" "Se encontraron $BUSINESS_LOGIC_IN_ENDPOINTS endpoints con lógica de negocio compleja" "ARCH-014"
        echo "   📍 Recomendación: Mover lógica a servicios"
    else
        report_success "Endpoints mantienen separación de responsabilidades"
    fi
fi

echo ""
echo "6. VERIFICANDO CONFIGURACIÓN DE BASE DE DATOS..."
echo "----------------------------------------------"

# Verificar configuración de pool de conexiones
CONFIG_FILE="$BACKEND_DIR/core/config.py"
if [ -f "$CONFIG_FILE" ]; then
    if grep -q "DB_POOL_SIZE" "$CONFIG_FILE"; then
        report_success "Pool de conexiones configurado"
    else
        report_issue "PERFORMANCE" "Pool de conexiones no configurado" "ARCH-015"
    fi
    
    if grep -q "DB_MAX_OVERFLOW" "$CONFIG_FILE"; then
        report_success "Overflow de conexiones configurado"
    else
        report_issue "PERFORMANCE" "Overflow de conexiones no configurado" "ARCH-016"
    fi
    
    if grep -q "DB_POOL_TIMEOUT" "$CONFIG_FILE"; then
        report_success "Timeout de pool configurado"
    else
        report_issue "PERFORMANCE" "Timeout de pool no configurado" "ARCH-017"
    fi
fi

echo ""
echo "7. VERIFICANDO MANEJO DE ERRORES..."
echo "----------------------------------"

# Verificar consistencia en manejo de errores
ERROR_HANDLING_CONSISTENCY=0
if [ -d "$ENDPOINTS_DIR" ]; then
    for endpoint_file in "$ENDPOINTS_DIR"/*.py; do
        if [ -f "$endpoint_file" ] && [ "$(basename "$endpoint_file")" != "__init__.py" ]; then
            HTTP_EXCEPTIONS=$(grep -c "HTTPException" "$endpoint_file" 2>/dev/null)
            RESPONSE_USAGE=$(grep -c "Response(" "$endpoint_file" 2>/dev/null)
            
            if [ $HTTP_EXCEPTIONS -gt 0 ] && [ $RESPONSE_USAGE -gt 0 ]; then
                echo "   ⚠️ Manejo inconsistente en: $(basename "$endpoint_file")"
                ((ERROR_HANDLING_CONSISTENCY++))
            fi
        fi
    done
    
    if [ $ERROR_HANDLING_CONSISTENCY -gt 0 ]; then
        report_issue "DESIGN" "Se encontraron $ERROR_HANDLING_CONSISTENCY archivos con manejo inconsistente de errores" "ARCH-018"
        echo "   📍 Recomendación: Estandarizar manejo de errores"
    else
        report_success "Manejo de errores consistente"
    fi
fi

echo ""
echo "8. VERIFICANDO DOCUMENTACIÓN..."
echo "-----------------------------"

# Verificar documentación en archivos críticos
DOCUMENTATION_SCORE=0
CRITICAL_FILES=(
    "$BACKEND_DIR/main.py"
    "$BACKEND_DIR/core/config.py"
    "$BACKEND_DIR/core/security.py"
)

for file in "${CRITICAL_FILES[@]}"; do
    if [ -f "$file" ]; then
        DOC_LINES=$(grep -c '"""\|"""' "$file" 2>/dev/null)
        TOTAL_LINES=$(wc -l < "$file")
        DOC_PERCENTAGE=$((DOC_LINES * 100 / TOTAL_LINES))
        
        if [ $DOC_PERCENTAGE -gt 10 ]; then
            echo "   ✅ Documentación adecuada en $(basename "$file") ($DOC_PERCENTAGE%)"
            ((DOCUMENTATION_SCORE++))
        else
            echo "   ⚠️ Documentación insuficiente en $(basename "$file") ($DOC_PERCENTAGE%)"
        fi
    fi
done

if [ $DOCUMENTATION_SCORE -eq ${#CRITICAL_FILES[@]} ]; then
    report_success "Documentación adecuada en archivos críticos"
else
    report_issue "MAINTAINABILITY" "Documentación insuficiente en archivos críticos" "ARCH-019"
fi

echo ""
echo "=================================================="
echo "📊 RESUMEN DE VERIFICACIÓN DE ARQUITECTURA"
echo "=================================================="
echo "🏗️ Problemas de Arquitectura: $ARCHITECTURE_ISSUES"
echo "🎨 Problemas de Diseño: $DESIGN_ISSUES"
echo "🔧 Problemas de Mantenibilidad: $MAINTAINABILITY_ISSUES"
echo "⚡ Problemas de Performance: $PERFORMANCE_ISSUES"
echo ""

TOTAL_ARCHITECTURE_ISSUES=$((ARCHITECTURE_ISSUES + DESIGN_ISSUES + MAINTAINABILITY_ISSUES + PERFORMANCE_ISSUES))

if [ $ARCHITECTURE_ISSUES -gt 2 ]; then
    echo "🚨 ESTADO: ARQUITECTURA CRÍTICA - REFACTORING REQUERIDO"
    echo "   El sistema requiere reestructuración significativa"
    exit 1
elif [ $DESIGN_ISSUES -gt 3 ]; then
    echo "⚠️ ESTADO: DISEÑO DEFICIENTE - MEJORAS REQUERIDAS"
    echo "   El sistema requiere mejoras en patrones de diseño"
    exit 2
elif [ $MAINTAINABILITY_ISSUES -gt 3 ]; then
    echo "🟡 ESTADO: MANTENIBILIDAD BAJA - OPTIMIZACIÓN RECOMENDADA"
    echo "   El sistema es funcional pero difícil de mantener"
    exit 3
elif [ $PERFORMANCE_ISSUES -gt 2 ]; then
    echo "🟡 ESTADO: PERFORMANCE SUBÓPTIMA - OPTIMIZACIÓN RECOMENDADA"
    echo "   El sistema funciona pero puede mejorar en performance"
    exit 4
else
    echo "✅ ESTADO: ARQUITECTURA SÓLIDA - CUMPLE ESTÁNDARES"
    echo "   El sistema tiene una arquitectura bien diseñada"
    exit 0
fi
