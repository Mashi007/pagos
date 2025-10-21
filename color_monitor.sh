#!/bin/bash
# color_monitor.sh - Sistema de monitoreo por colores con trazabilidad
# Normativas de gestión de problemas con códigos de color estándar

# Configuración de colores ANSI estándar para gestión de problemas
# Basado en normativas ITIL y ISO 20000

# Colores principales para niveles de severidad
CRITICAL_COLOR='\033[0;31m'    # Rojo - Crítico (ITIL Priority 1)
HIGH_COLOR='\033[0;33m'        # Naranja - Alto (ITIL Priority 2)
MEDIUM_COLOR='\033[1;33m'      # Amarillo - Medio (ITIL Priority 3)
LOW_COLOR='\033[0;32m'         # Verde - Bajo (ITIL Priority 4)
INFO_COLOR='\033[0;34m'        # Azul - Informativo
SUCCESS_COLOR='\033[0;36m'     # Cian - Éxito
WARNING_COLOR='\033[0;35m'     # Magenta - Advertencia
DEBUG_COLOR='\033[0;37m'       # Blanco - Debug
HEADER_COLOR='\033[1;37m'      # Blanco brillante - Encabezados
NC='\033[0m'                   # Sin color

# Configuración de trazabilidad
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
SESSION_ID=$(uuidgen | cut -d'-' -f1)
LOG_FILE="monitoring_$(date '+%Y%m%d_%H%M%S').log"
TRACE_FILE="traceability_$(date '+%Y%m%d_%H%M%S').json"

# Función para generar código de color basado en severidad
get_color_code() {
    local severity=$1
    case $severity in
        "CRITICAL"|"P1")
            echo "$CRITICAL_COLOR"
            ;;
        "HIGH"|"P2")
            echo "$HIGH_COLOR"
            ;;
        "MEDIUM"|"P3")
            echo "$MEDIUM_COLOR"
            ;;
        "LOW"|"P4")
            echo "$LOW_COLOR"
            ;;
        "INFO")
            echo "$INFO_COLOR"
            ;;
        "SUCCESS")
            echo "$SUCCESS_COLOR"
            ;;
        "WARNING")
            echo "$WARNING_COLOR"
            ;;
        "DEBUG")
            echo "$DEBUG_COLOR"
            ;;
        *)
            echo "$NC"
            ;;
    esac
}

# Función para generar emoji basado en severidad
get_severity_emoji() {
    local severity=$1
    case $severity in
        "CRITICAL"|"P1")
            echo "🚨"
            ;;
        "HIGH"|"P2")
            echo "🔴"
            ;;
        "MEDIUM"|"P3")
            echo "🟡"
            ;;
        "LOW"|"P4")
            echo "🟢"
            ;;
        "INFO")
            echo "ℹ️"
            ;;
        "SUCCESS")
            echo "✅"
            ;;
        "WARNING")
            echo "⚠️"
            ;;
        "DEBUG")
            echo "🔍"
            ;;
        *)
            echo "📋"
            ;;
    esac
}

# Función de logging con trazabilidad completa
log_with_full_trace() {
    local level=$1
    local message=$2
    local code=$3
    local component=$4
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S.%3N')
    local color=$(get_color_code "$level")
    local emoji=$(get_severity_emoji "$level")
    
    # Log estructurado a archivo
    echo "[$timestamp] [$SESSION_ID] [$level] [$code] [$component] $message" >> "$LOG_FILE"
    
    # Log JSON para trazabilidad
    cat >> "$TRACE_FILE" << EOF
{
    "timestamp": "$timestamp",
    "session_id": "$SESSION_ID",
    "level": "$level",
    "code": "$code",
    "component": "$component",
    "message": "$message",
    "emoji": "$emoji",
    "color": "$color"
},
EOF
    
    # Log a consola con colores
    echo -e "${color}${emoji} $level: $message [$code]${NC}"
}

# Función para generar dashboard visual
generate_visual_dashboard() {
    local critical=$1
    local high=$2
    local medium=$3
    local low=$4
    
    echo -e "${HEADER_COLOR}📊 DASHBOARD DE MONITOREO VISUAL${NC}"
    echo -e "${HEADER_COLOR}================================${NC}"
    echo ""
    
    # Barra de progreso visual para problemas críticos
    echo -e "${CRITICAL_COLOR}🚨 PROBLEMAS CRÍTICOS: $critical${NC}"
    if [ $critical -gt 0 ]; then
        echo -e "${CRITICAL_COLOR}████████████████████████████████████████ 100%${NC}"
    else
        echo -e "${SUCCESS_COLOR}████████████████████████████████████████ 0%${NC}"
    fi
    echo ""
    
    # Barra de progreso visual para problemas altos
    echo -e "${HIGH_COLOR}🔴 PROBLEMAS ALTOS: $high${NC}"
    if [ $high -gt 0 ]; then
        echo -e "${HIGH_COLOR}████████████████████████████████████████ 100%${NC}"
    else
        echo -e "${SUCCESS_COLOR}████████████████████████████████████████ 0%${NC}"
    fi
    echo ""
    
    # Barra de progreso visual para problemas medios
    echo -e "${MEDIUM_COLOR}🟡 PROBLEMAS MEDIOS: $medium${NC}"
    if [ $medium -gt 0 ]; then
        echo -e "${MEDIUM_COLOR}████████████████████████████████████████ 100%${NC}"
    else
        echo -e "${SUCCESS_COLOR}████████████████████████████████████████ 0%${NC}"
    fi
    echo ""
    
    # Barra de progreso visual para problemas bajos
    echo -e "${LOW_COLOR}🟢 PROBLEMAS BAJOS: $low${NC}"
    if [ $low -gt 0 ]; then
        echo -e "${LOW_COLOR}████████████████████████████████████████ 100%${NC}"
    else
        echo -e "${SUCCESS_COLOR}████████████████████████████████████████ 0%${NC}"
    fi
    echo ""
}

# Función para generar alertas por colores
generate_color_alerts() {
    local critical=$1
    local high=$2
    local medium=$3
    local low=$4
    
    echo -e "${HEADER_COLOR}🚨 SISTEMA DE ALERTAS POR COLORES${NC}"
    echo -e "${HEADER_COLOR}==================================${NC}"
    echo ""
    
    if [ $critical -gt 0 ]; then
        echo -e "${CRITICAL_COLOR}🚨 ALERTA CRÍTICA: $critical problemas críticos detectados${NC}"
        echo -e "${CRITICAL_COLOR}   Acción requerida: INTERVENCIÓN INMEDIATA${NC}"
        echo -e "${CRITICAL_COLOR}   Tiempo de respuesta: < 1 hora${NC}"
        echo -e "${CRITICAL_COLOR}   Escalación: Nivel 1 (DevOps Lead)${NC}"
        echo ""
    fi
    
    if [ $high -gt 0 ]; then
        echo -e "${HIGH_COLOR}🔴 ALERTA ALTA: $high problemas altos detectados${NC}"
        echo -e "${HIGH_COLOR}   Acción requerida: INTERVENCIÓN EN 24H${NC}"
        echo -e "${HIGH_COLOR}   Tiempo de respuesta: < 4 horas${NC}"
        echo -e "${HIGH_COLOR}   Escalación: Nivel 2 (Backend Lead)${NC}"
        echo ""
    fi
    
    if [ $medium -gt 0 ]; then
        echo -e "${MEDIUM_COLOR}🟡 ALERTA MEDIA: $medium problemas medios detectados${NC}"
        echo -e "${MEDIUM_COLOR}   Acción requerida: PLANIFICAR CORRECCIÓN${NC}"
        echo -e "${MEDIUM_COLOR}   Tiempo de respuesta: < 1 semana${NC}"
        echo -e "${MEDIUM_COLOR}   Escalación: Nivel 3 (Desarrollador Senior)${NC}"
        echo ""
    fi
    
    if [ $low -gt 0 ]; then
        echo -e "${LOW_COLOR}🟢 ALERTA BAJA: $low problemas bajos detectados${NC}"
        echo -e "${LOW_COLOR}   Acción requerida: MEJORAS OPCIONALES${NC}"
        echo -e "${LOW_COLOR}   Tiempo de respuesta: < 1 mes${NC}"
        echo -e "${LOW_COLOR}   Escalación: Nivel 4 (Desarrollador)${NC}"
        echo ""
    fi
    
    if [ $critical -eq 0 ] && [ $high -eq 0 ] && [ $medium -eq 0 ] && [ $low -eq 0 ]; then
        echo -e "${SUCCESS_COLOR}✅ SISTEMA EN ESTADO ÓPTIMO${NC}"
        echo -e "${SUCCESS_COLOR}   No se detectaron problemas${NC}"
        echo -e "${SUCCESS_COLOR}   Estado: CUMPLE NORMATIVAS${NC}"
        echo ""
    fi
}

# Función para generar reporte de trazabilidad
generate_traceability_report() {
    echo -e "${HEADER_COLOR}🔍 REPORTE DE TRAZABILIDAD${NC}"
    echo -e "${HEADER_COLOR}==========================${NC}"
    echo ""
    echo -e "${INFO_COLOR}📋 Session ID: $SESSION_ID${NC}"
    echo -e "${INFO_COLOR}📁 Log File: $LOG_FILE${NC}"
    echo -e "${INFO_COLOR}📊 Trace File: $TRACE_FILE${NC}"
    echo -e "${INFO_COLOR}⏰ Timestamp: $TIMESTAMP${NC}"
    echo ""
    
    # Mostrar estadísticas de trazabilidad
    if [ -f "$LOG_FILE" ]; then
        TOTAL_ENTRIES=$(wc -l < "$LOG_FILE")
        echo -e "${INFO_COLOR}📈 Total de entradas de log: $TOTAL_ENTRIES${NC}"
        
        CRITICAL_COUNT=$(grep -c "CRITICAL" "$LOG_FILE")
        HIGH_COUNT=$(grep -c "HIGH" "$LOG_FILE")
        MEDIUM_COUNT=$(grep -c "MEDIUM" "$LOG_FILE")
        LOW_COUNT=$(grep -c "LOW" "$LOG_FILE")
        
        echo -e "${CRITICAL_COLOR}🚨 Entradas críticas: $CRITICAL_COUNT${NC}"
        echo -e "${HIGH_COLOR}🔴 Entradas altas: $HIGH_COUNT${NC}"
        echo -e "${MEDIUM_COLOR}🟡 Entradas medias: $MEDIUM_COUNT${NC}"
        echo -e "${LOW_COLOR}🟢 Entradas bajas: $LOW_COUNT${NC}"
        echo ""
    fi
}

# Función para generar código de estado final
generate_final_status_code() {
    local critical=$1
    local high=$2
    local medium=$3
    local low=$4
    
    if [ $critical -gt 0 ]; then
        echo -e "${CRITICAL_COLOR}🚨 CÓDIGO DE ESTADO: CRÍTICO (Exit Code: 1)${NC}"
        echo -e "${CRITICAL_COLOR}   El sistema NO es apto para producción${NC}"
        return 1
    elif [ $high -gt 0 ]; then
        echo -e "${HIGH_COLOR}🔴 CÓDIGO DE ESTADO: ALTO RIESGO (Exit Code: 2)${NC}"
        echo -e "${HIGH_COLOR}   El sistema requiere atención inmediata${NC}"
        return 2
    elif [ $medium -gt 0 ]; then
        echo -e "${MEDIUM_COLOR}🟡 CÓDIGO DE ESTADO: RIESGO MEDIO (Exit Code: 3)${NC}"
        echo -e "${MEDIUM_COLOR}   El sistema es funcional pero requiere mejoras${NC}"
        return 3
    elif [ $low -gt 0 ]; then
        echo -e "${LOW_COLOR}🟢 CÓDIGO DE ESTADO: RIESGO BAJO (Exit Code: 4)${NC}"
        echo -e "${LOW_COLOR}   El sistema es seguro para producción${NC}"
        return 4
    else
        echo -e "${SUCCESS_COLOR}✅ CÓDIGO DE ESTADO: SEGURO (Exit Code: 0)${NC}"
        echo -e "${SUCCESS_COLOR}   El sistema cumple todas las normativas${NC}"
        return 0
    fi
}

# Función principal de monitoreo
main_monitoring() {
    local critical=$1
    local high=$2
    local medium=$3
    local low=$4
    
    echo -e "${HEADER_COLOR}🎯 SISTEMA DE MONITOREO POR COLORES${NC}"
    echo -e "${HEADER_COLOR}====================================${NC}"
    echo ""
    
    # Generar dashboard visual
    generate_visual_dashboard "$critical" "$high" "$medium" "$low"
    
    # Generar alertas por colores
    generate_color_alerts "$critical" "$high" "$medium" "$low"
    
    # Generar reporte de trazabilidad
    generate_traceability_report
    
    # Generar código de estado final
    generate_final_status_code "$critical" "$high" "$medium" "$low"
}

# Exportar funciones para uso en otros scripts
export -f get_color_code
export -f get_severity_emoji
export -f log_with_full_trace
export -f generate_visual_dashboard
export -f generate_color_alerts
export -f generate_traceability_report
export -f generate_final_status_code
export -f main_monitoring

# Si se ejecuta directamente, mostrar ayuda
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    echo -e "${HEADER_COLOR}🎨 SISTEMA DE MONITOREO POR COLORES${NC}"
    echo -e "${HEADER_COLOR}===================================${NC}"
    echo ""
    echo -e "${INFO_COLOR}Uso: source color_monitor.sh${NC}"
    echo -e "${INFO_COLOR}Luego: main_monitoring <critical> <high> <medium> <low>${NC}"
    echo ""
    echo -e "${SUCCESS_COLOR}Ejemplo:${NC}"
    echo -e "${SUCCESS_COLOR}  main_monitoring 2 1 3 0${NC}"
    echo ""
    echo -e "${WARNING_COLOR}Colores disponibles:${NC}"
    echo -e "${CRITICAL_COLOR}🚨 CRITICAL${NC}"
    echo -e "${HIGH_COLOR}🔴 HIGH${NC}"
    echo -e "${MEDIUM_COLOR}🟡 MEDIUM${NC}"
    echo -e "${LOW_COLOR}🟢 LOW${NC}"
    echo -e "${INFO_COLOR}ℹ️ INFO${NC}"
    echo -e "${SUCCESS_COLOR}✅ SUCCESS${NC}"
    echo -e "${WARNING_COLOR}⚠️ WARNING${NC}"
    echo -e "${DEBUG_COLOR}🔍 DEBUG${NC}"
fi
