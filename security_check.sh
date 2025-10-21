#!/bin/bash
# security_check.sh - Script de verificación de seguridad automática
# Cumple con normativas de desarrollo para identificación rápida de problemas
# Sistema de monitoreo por colores con trazabilidad completa

# Configuración de colores ANSI para monitoreo visual
RED='\033[0;31m'      # Crítico
ORANGE='\033[0;33m'   # Alto
YELLOW='\033[1;33m'   # Medio
GREEN='\033[0;32m'    # Bajo
BLUE='\033[0;34m'     # Info
PURPLE='\033[0;35m'   # Debug
CYAN='\033[0;36m'     # Success
WHITE='\033[1;37m'    # Header
NC='\033[0m'          # No Color

# Configuración de trazabilidad
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
LOG_FILE="security_audit_$(date '+%Y%m%d_%H%M%S').log"
SESSION_ID=$(uuidgen | cut -d'-' -f1)

echo -e "${WHITE}🔍 VERIFICACIÓN DE SEGURIDAD BACKEND - $TIMESTAMP${NC}"
echo -e "${WHITE}==================================================${NC}"
echo -e "${BLUE}📋 Session ID: $SESSION_ID${NC}"
echo -e "${BLUE}📁 Log File: $LOG_FILE${NC}"
echo ""

# Función de logging con trazabilidad
log_with_trace() {
    local level=$1
    local message=$2
    local code=$3
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S.%3N')
    
    # Log a archivo con formato estructurado
    echo "[$timestamp] [$SESSION_ID] [$level] [$code] $message" >> "$LOG_FILE"
    
    # Log a consola con colores
    case $level in
        "CRITICAL")
            echo -e "${RED}❌ CRÍTICO: $message [$code]${NC}"
            ;;
        "HIGH")
            echo -e "${ORANGE}🔴 ALTO: $message [$code]${NC}"
            ;;
        "MEDIUM")
            echo -e "${YELLOW}🟡 MEDIO: $message [$code]${NC}"
            ;;
        "LOW")
            echo -e "${GREEN}🟢 BAJO: $message [$code]${NC}"
            ;;
        "SUCCESS")
            echo -e "${CYAN}✅ $message${NC}"
            ;;
        "INFO")
            echo -e "${BLUE}ℹ️ $message${NC}"
            ;;
        "DEBUG")
            echo -e "${PURPLE}🔍 DEBUG: $message${NC}"
            ;;
    esac
}

# Configuración
BACKEND_DIR="backend/app"
ENDPOINTS_DIR="$BACKEND_DIR/api/v1/endpoints"
CONFIG_FILE="$BACKEND_DIR/core/config.py"
MAIN_FILE="$BACKEND_DIR/main.py"
MODELS_DIR="$BACKEND_DIR/models"

# Contadores de problemas con trazabilidad
CRITICAL_ISSUES=0
HIGH_ISSUES=0
MEDIUM_ISSUES=0
LOW_ISSUES=0

# Función para reportar problemas con trazabilidad
report_issue() {
    local severity=$1
    local message=$2
    local code=$3
    
    case $severity in
        "CRITICAL")
            log_with_trace "CRITICAL" "$message" "$code"
            ((CRITICAL_ISSUES++))
            ;;
        "HIGH")
            log_with_trace "HIGH" "$message" "$code"
            ((HIGH_ISSUES++))
            ;;
        "MEDIUM")
            log_with_trace "MEDIUM" "$message" "$code"
            ((MEDIUM_ISSUES++))
            ;;
        "LOW")
            log_with_trace "LOW" "$message" "$code"
            ((LOW_ISSUES++))
            ;;
    esac
}

# Función para reportar éxito con trazabilidad
report_success() {
    local message=$1
    log_with_trace "SUCCESS" "$message" "OK"
}

echo ""
echo "1. VERIFICANDO ARCHIVOS DE DIAGNÓSTICO EN PRODUCCIÓN..."
echo "------------------------------------------------------"

# Verificar archivos de diagnóstico
DIAGNOSTIC_PATTERNS=(
    "*diagnostico*"
    "*analysis*"
    "*monitor*"
    "*forensic*"
    "*predictive*"
    "*temporal*"
    "*schema*"
    "*token_verification*"
)

TOTAL_DIAGNOSTIC_FILES=0
for pattern in "${DIAGNOSTIC_PATTERNS[@]}"; do
    FILES_FOUND=$(find "$ENDPOINTS_DIR" -name "$pattern" 2>/dev/null | wc -l)
    if [ $FILES_FOUND -gt 0 ]; then
        report_issue "CRITICAL" "Se encontraron $FILES_FOUND archivos con patrón '$pattern'" "SEC-001"
        find "$ENDPOINTS_DIR" -name "$pattern" 2>/dev/null | while read file; do
            echo "   📁 $file"
        done
        TOTAL_DIAGNOSTIC_FILES=$((TOTAL_DIAGNOSTIC_FILES + FILES_FOUND))
    fi
done

if [ $TOTAL_DIAGNOSTIC_FILES -eq 0 ]; then
    report_success "No se encontraron archivos de diagnóstico en producción"
fi

echo ""
echo "2. VERIFICANDO CONFIGURACIÓN CORS..."
echo "-----------------------------------"

# Verificar CORS
if [ -f "$CONFIG_FILE" ]; then
    if grep -q '"*"' "$CONFIG_FILE"; then
        report_issue "CRITICAL" "CORS con wildcard (*) detectado en configuración" "CONFIG-001-A"
        echo "   📍 Línea problemática:"
        grep -n '"*"' "$CONFIG_FILE" | head -3
    else
        report_success "CORS configurado correctamente (sin wildcard)"
    fi
    
    if grep -q '"null"' "$CONFIG_FILE"; then
        report_issue "HIGH" "CORS permite origin 'null' - revisar necesidad" "CONFIG-001-B"
    fi
else
    report_issue "CRITICAL" "Archivo de configuración no encontrado: $CONFIG_FILE" "CONFIG-001-C"
fi

echo ""
echo "3. VERIFICANDO CONTRASEÑA POR DEFECTO..."
echo "---------------------------------------"

# Verificar contraseña por defecto
if [ -f "$CONFIG_FILE" ]; then
    if grep -q 'R@pi_2025\*\*' "$CONFIG_FILE"; then
        report_issue "CRITICAL" "Contraseña por defecto detectada en configuración" "CONFIG-001-D"
        echo "   📍 Línea problemática:"
        grep -n 'R@pi_2025' "$CONFIG_FILE"
    else
        report_success "Contraseña personalizada configurada"
    fi
fi

echo ""
echo "4. VERIFICANDO INTEGRACIÓN DE MONITOREO..."
echo "----------------------------------------"

# Verificar monitoreo
if [ -f "$MAIN_FILE" ]; then
    if grep -q "setup_monitoring" "$MAIN_FILE"; then
        report_success "Monitoreo integrado en main.py"
    else
        report_issue "HIGH" "Monitoreo no integrado en main.py" "CONFIG-001-E"
    fi
    
    if grep -q "from app.core.monitoring" "$MAIN_FILE"; then
        report_success "Import de monitoreo presente"
    else
        report_issue "MEDIUM" "Import de monitoreo faltante" "CONFIG-001-F"
    fi
else
    report_issue "CRITICAL" "Archivo main.py no encontrado: $MAIN_FILE" "CONFIG-001-G"
fi

echo ""
echo "5. VERIFICANDO ARQUITECTURA DE MODELOS..."
echo "----------------------------------------"

# Verificar relaciones comentadas
if [ -d "$MODELS_DIR" ]; then
    COMMENTED_RELATIONS=$(grep -r "relationship.*COMENTADO" "$MODELS_DIR" 2>/dev/null | wc -l)
    if [ $COMMENTED_RELATIONS -gt 0 ]; then
        report_issue "MEDIUM" "Se encontraron $COMMENTED_RELATIONS relaciones comentadas" "ARCH-001"
        echo "   📍 Archivos con relaciones comentadas:"
        grep -r "relationship.*COMENTADO" "$MODELS_DIR" 2>/dev/null | cut -d: -f1 | sort -u
    else
        report_success "No hay relaciones comentadas en modelos"
    fi
else
    report_issue "HIGH" "Directorio de modelos no encontrado: $MODELS_DIR" "ARCH-002"
fi

echo ""
echo "6. VERIFICANDO CONFIGURACIÓN DUPLICADA..."
echo "----------------------------------------"

# Verificar configuración duplicada
if [ -f "$CONFIG_FILE" ]; then
    DUPLICATE_CONFIG=$(grep -E "(MONTO_MINIMO|MIN_LOAN)" "$CONFIG_FILE" 2>/dev/null | wc -l)
    if [ $DUPLICATE_CONFIG -gt 2 ]; then
        report_issue "LOW" "Configuración duplicada detectada ($DUPLICATE_CONFIG líneas)" "ARCH-003"
        echo "   📍 Configuraciones duplicadas:"
        grep -n -E "(MONTO_MINIMO|MIN_LOAN)" "$CONFIG_FILE" 2>/dev/null
    else
        report_success "Configuración única (sin duplicados críticos)"
    fi
fi

echo ""
echo "7. VERIFICANDO IMPORTS DE DIAGNÓSTICO..."
echo "--------------------------------------"

# Verificar imports en __init__.py
INIT_FILE="$ENDPOINTS_DIR/__init__.py"
if [ -f "$INIT_FILE" ]; then
    DIAGNOSTIC_IMPORTS=$(grep -E "(diagnostico|analysis|monitor|forensic|predictive|temporal|schema|token_verification)" "$INIT_FILE" 2>/dev/null | wc -l)
    if [ $DIAGNOSTIC_IMPORTS -gt 0 ]; then
        report_issue "HIGH" "Se encontraron $DIAGNOSTIC_IMPORTS imports de diagnóstico en __init__.py" "SEC-002"
        echo "   📍 Imports problemáticos:"
        grep -n -E "(diagnostico|analysis|monitor|forensic|predictive|temporal|schema|token_verification)" "$INIT_FILE" 2>/dev/null
    else
        report_success "No hay imports de diagnóstico en __init__.py"
    fi
else
    report_issue "MEDIUM" "Archivo __init__.py no encontrado: $INIT_FILE" "ARCH-004"
fi

echo ""
echo "8. VERIFICANDO PERMISOS DE ARCHIVOS..."
echo "------------------------------------"

# Verificar permisos críticos
CRITICAL_FILES=("$CONFIG_FILE" "$MAIN_FILE")
for file in "${CRITICAL_FILES[@]}"; do
    if [ -f "$file" ]; then
        PERMS=$(stat -c "%a" "$file" 2>/dev/null)
        if [ "$PERMS" = "644" ] || [ "$PERMS" = "600" ]; then
            report_success "Permisos correctos para $file ($PERMS)"
        else
            report_issue "MEDIUM" "Permisos inadecuados para $file ($PERMS) - debería ser 644 o 600" "SEC-003"
        fi
    fi
done

echo ""
echo "=================================================="
echo "📊 RESUMEN DE VERIFICACIÓN DE SEGURIDAD"
echo "=================================================="
echo "❌ Problemas Críticos: $CRITICAL_ISSUES"
echo "🔴 Problemas Altos: $HIGH_ISSUES"
echo "🟡 Problemas Medios: $MEDIUM_ISSUES"
echo "🟢 Problemas Bajos: $LOW_ISSUES"
echo ""

TOTAL_ISSUES=$((CRITICAL_ISSUES + HIGH_ISSUES + MEDIUM_ISSUES + LOW_ISSUES))

if [ $CRITICAL_ISSUES -gt 0 ]; then
    echo "🚨 ESTADO: CRÍTICO - ACCIÓN INMEDIATA REQUERIDA"
    echo "   El sistema NO es apto para producción"
    exit 1
elif [ $HIGH_ISSUES -gt 0 ]; then
    echo "⚠️ ESTADO: ALTO RIESGO - ACCIÓN REQUERIDA EN 24H"
    echo "   El sistema requiere atención inmediata"
    exit 2
elif [ $MEDIUM_ISSUES -gt 0 ]; then
    echo "🟡 ESTADO: RIESGO MEDIO - PLANIFICAR CORRECCIÓN"
    echo "   El sistema es funcional pero requiere mejoras"
    exit 3
elif [ $LOW_ISSUES -gt 0 ]; then
    echo "🟢 ESTADO: RIESGO BAJO - MEJORAS OPCIONALES"
    echo "   El sistema es seguro para producción"
    exit 4
else
    echo "✅ ESTADO: SEGURO - CUMPLE NORMATIVAS"
    echo "   El sistema es apto para producción"
    exit 0
fi
