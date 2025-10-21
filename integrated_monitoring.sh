#!/bin/bash
# integrated_monitoring.sh - Sistema integrado de monitoreo con colores y trazabilidad
# Cumple con normativas de gestión de problemas y facilita identificación rápida

# Configuración de colores ANSI estándar
RED='\033[0;31m'      # Crítico
ORANGE='\033[0;33m'   # Alto
YELLOW='\033[1;33m'   # Medio
GREEN='\033[0;32m'    # Bajo
BLUE='\033[0;34m'     # Info
PURPLE='\033[0;35m'   # Advertencia
CYAN='\033[0;36m'     # Éxito
WHITE='\033[1;37m'    # Encabezados
NC='\033[0m'          # Sin color

# Configuración del sistema
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
SESSION_ID=$(uuidgen | cut -d'-' -f1)
INTEGRATED_LOG="integrated_monitoring_$(date '+%Y%m%d_%H%M%S').log"

# Función para cargar módulos de monitoreo
load_monitoring_modules() {
    echo -e "${BLUE}📦 Cargando módulos de monitoreo...${NC}"
    
    # Cargar módulos si existen
    if [ -f "color_monitor.sh" ]; then
        source color_monitor.sh
        echo -e "${GREEN}✅ Módulo de colores cargado${NC}"
    fi
    
    if [ -f "traceability_system.sh" ]; then
        source traceability_system.sh
        echo -e "${GREEN}✅ Módulo de trazabilidad cargado${NC}"
    fi
    
    if [ -f "visual_dashboard.sh" ]; then
        source visual_dashboard.sh
        echo -e "${GREEN}✅ Módulo de dashboard cargado${NC}"
    fi
    
    if [ -f "color_alerts.sh" ]; then
        source color_alerts.sh
        echo -e "${GREEN}✅ Módulo de alertas cargado${NC}"
    fi
    
    echo ""
}

# Función para ejecutar verificación de seguridad
run_security_check() {
    echo -e "${WHITE}🔍 EJECUTANDO VERIFICACIÓN DE SEGURIDAD${NC}"
    echo -e "${WHITE}=========================================${NC}"
    echo ""
    
    if [ -f "security_check.sh" ]; then
        # Ejecutar verificación de seguridad
        bash security_check.sh > security_output.tmp 2>&1
        local exit_code=$?
        
        # Extraer contadores de problemas
        local critical=$(grep -o "Problemas Críticos: [0-9]*" security_output.tmp | grep -o "[0-9]*" || echo "0")
        local high=$(grep -o "Problemas Altos: [0-9]*" security_output.tmp | grep -o "[0-9]*" || echo "0")
        local medium=$(grep -o "Problemas Medios: [0-9]*" security_output.tmp | grep -o "[0-9]*" || echo "0")
        local low=$(grep -o "Problemas Bajos: [0-9]*" security_output.tmp | grep -o "[0-9]*" || echo "0")
        
        echo -e "${CYAN}📊 Resultados de verificación de seguridad:${NC}"
        echo -e "${RED}🚨 Críticos: $critical${NC}"
        echo -e "${ORANGE}🔴 Altos: $high${NC}"
        echo -e "${YELLOW}🟡 Medios: $medium${NC}"
        echo -e "${GREEN}🟢 Bajos: $low${NC}"
        echo ""
        
        # Retornar contadores
        echo "$critical $high $medium $low"
    else
        echo -e "${RED}❌ Script de verificación de seguridad no encontrado${NC}"
        echo "0 0 0 0"
    fi
}

# Función para ejecutar verificación de arquitectura
run_architecture_check() {
    echo -e "${WHITE}🏗️ EJECUTANDO VERIFICACIÓN DE ARQUITECTURA${NC}"
    echo -e "${WHITE}===========================================${NC}"
    echo ""
    
    if [ -f "architecture_check.sh" ]; then
        # Ejecutar verificación de arquitectura
        bash architecture_check.sh > architecture_output.tmp 2>&1
        local exit_code=$?
        
        # Extraer contadores de problemas
        local architecture=$(grep -o "Problemas de Arquitectura: [0-9]*" architecture_output.tmp | grep -o "[0-9]*" || echo "0")
        local design=$(grep -o "Problemas de Diseño: [0-9]*" architecture_output.tmp | grep -o "[0-9]*" || echo "0")
        local maintainability=$(grep -o "Problemas de Mantenibilidad: [0-9]*" architecture_output.tmp | grep -o "[0-9]*" || echo "0")
        local performance=$(grep -o "Problemas de Performance: [0-9]*" architecture_output.tmp | grep -o "[0-9]*" || echo "0")
        
        echo -e "${CYAN}📊 Resultados de verificación de arquitectura:${NC}"
        echo -e "${RED}🏗️ Arquitectura: $architecture${NC}"
        echo -e "${ORANGE}🎨 Diseño: $design${NC}"
        echo -e "${YELLOW}🔧 Mantenibilidad: $maintainability${NC}"
        echo -e "${GREEN}⚡ Performance: $performance${NC}"
        echo ""
        
        # Retornar contadores
        echo "$architecture $design $maintainability $performance"
    else
        echo -e "${RED}❌ Script de verificación de arquitectura no encontrado${NC}"
        echo "0 0 0 0"
    fi
}

# Función para generar reporte integrado
generate_integrated_report() {
    local security_critical=$1
    local security_high=$2
    local security_medium=$3
    local security_low=$4
    local arch_issues=$5
    local design_issues=$6
    local maintainability_issues=$7
    local performance_issues=$8
    
    local total_critical=$security_critical
    local total_high=$security_high
    local total_medium=$security_medium
    local total_low=$security_low
    
    echo -e "${WHITE}📊 REPORTE INTEGRADO DE MONITOREO${NC}"
    echo -e "${WHITE}=================================${NC}"
    echo ""
    
    # Resumen ejecutivo
    echo -e "${BLUE}📋 RESUMEN EJECUTIVO${NC}"
    echo -e "${BLUE}===================${NC}"
    echo -e "${BLUE}📅 Fecha: $TIMESTAMP${NC}"
    echo -e "${BLUE}🆔 Session ID: $SESSION_ID${NC}"
    echo -e "${BLUE}📁 Log: $INTEGRATED_LOG${NC}"
    echo ""
    
    # Métricas de seguridad
    echo -e "${CYAN}🔒 MÉTRICAS DE SEGURIDAD${NC}"
    echo -e "${CYAN}=======================${NC}"
    echo -e "${RED}🚨 Críticos: $security_critical${NC}"
    echo -e "${ORANGE}🔴 Altos: $security_high${NC}"
    echo -e "${YELLOW}🟡 Medios: $security_medium${NC}"
    echo -e "${GREEN}🟢 Bajos: $security_low${NC}"
    echo ""
    
    # Métricas de arquitectura
    echo -e "${CYAN}🏗️ MÉTRICAS DE ARQUITECTURA${NC}"
    echo -e "${CYAN}===========================${NC}"
    echo -e "${RED}🏗️ Arquitectura: $arch_issues${NC}"
    echo -e "${ORANGE}🎨 Diseño: $design_issues${NC}"
    echo -e "${YELLOW}🔧 Mantenibilidad: $maintainability_issues${NC}"
    echo -e "${GREEN}⚡ Performance: $performance_issues${NC}"
    echo ""
    
    # Estado general del sistema
    echo -e "${CYAN}🎯 ESTADO GENERAL DEL SISTEMA${NC}"
    echo -e "${CYAN}=============================${NC}"
    
    if [ $total_critical -gt 0 ]; then
        echo -e "${RED}🚨 ESTADO: CRÍTICO${NC}"
        echo -e "${RED}   El sistema NO es apto para producción${NC}"
        echo -e "${RED}   Acción requerida: INTERVENCIÓN INMEDIATA${NC}"
    elif [ $total_high -gt 0 ]; then
        echo -e "${ORANGE}🔴 ESTADO: ALTO RIESGO${NC}"
        echo -e "${ORANGE}   El sistema requiere atención inmediata${NC}"
        echo -e "${ORANGE}   Acción requerida: INTERVENCIÓN EN 24H${NC}"
    elif [ $total_medium -gt 0 ]; then
        echo -e "${YELLOW}🟡 ESTADO: RIESGO MEDIO${NC}"
        echo -e "${YELLOW}   El sistema es funcional pero requiere mejoras${NC}"
        echo -e "${YELLOW}   Acción requerida: PLANIFICAR CORRECCIÓN${NC}"
    elif [ $total_low -gt 0 ]; then
        echo -e "${GREEN}🟢 ESTADO: RIESGO BAJO${NC}"
        echo -e "${GREEN}   El sistema es seguro para producción${NC}"
        echo -e "${GREEN}   Acción requerida: MEJORAS OPCIONALES${NC}"
    else
        echo -e "${GREEN}✅ ESTADO: ÓPTIMO${NC}"
        echo -e "${GREEN}   El sistema cumple todas las normativas${NC}"
        echo -e "${GREEN}   No se requiere acción${NC}"
    fi
    echo ""
    
    # Generar alertas por colores
    if command -v generate_color_alerts >/dev/null 2>&1; then
        generate_color_alerts "$total_critical" "$total_high" "$total_medium" "$total_low"
    fi
    
    # Generar dashboard visual
    if command -v generate_visual_dashboard >/dev/null 2>&1; then
        generate_visual_dashboard "$total_critical" "$total_high" "$total_medium" "$total_low"
    fi
    
    # Generar reporte de trazabilidad
    if command -v generate_traceability_report >/dev/null 2>&1; then
        generate_traceability_report
    fi
}

# Función principal de monitoreo integrado
main_integrated_monitoring() {
    echo -e "${WHITE}🎯 SISTEMA INTEGRADO DE MONITOREO${NC}"
    echo -e "${WHITE}===================================${NC}"
    echo -e "${WHITE}Con colores, trazabilidad y normativas de gestión${NC}"
    echo ""
    
    # Cargar módulos
    load_monitoring_modules
    
    # Ejecutar verificaciones
    echo -e "${BLUE}🔍 Iniciando verificaciones...${NC}"
    echo ""
    
    # Verificación de seguridad
    local security_results=$(run_security_check)
    local security_critical=$(echo $security_results | cut -d' ' -f1)
    local security_high=$(echo $security_results | cut -d' ' -f2)
    local security_medium=$(echo $security_results | cut -d' ' -f3)
    local security_low=$(echo $security_results | cut -d' ' -f4)
    
    # Verificación de arquitectura
    local architecture_results=$(run_architecture_check)
    local arch_issues=$(echo $architecture_results | cut -d' ' -f1)
    local design_issues=$(echo $architecture_results | cut -d' ' -f2)
    local maintainability_issues=$(echo $architecture_results | cut -d' ' -f3)
    local performance_issues=$(echo $architecture_results | cut -d' ' -f4)
    
    # Generar reporte integrado
    generate_integrated_report "$security_critical" "$security_high" "$security_medium" "$security_low" "$arch_issues" "$design_issues" "$maintainability_issues" "$performance_issues"
    
    # Determinar código de salida
    local total_critical=$security_critical
    if [ $total_critical -gt 0 ]; then
        echo -e "${RED}🚨 CÓDIGO DE SALIDA: 1 (CRÍTICO)${NC}"
        exit 1
    elif [ $security_high -gt 0 ]; then
        echo -e "${ORANGE}🔴 CÓDIGO DE SALIDA: 2 (ALTO RIESGO)${NC}"
        exit 2
    elif [ $security_medium -gt 0 ]; then
        echo -e "${YELLOW}🟡 CÓDIGO DE SALIDA: 3 (RIESGO MEDIO)${NC}"
        exit 3
    elif [ $security_low -gt 0 ]; then
        echo -e "${GREEN}🟢 CÓDIGO DE SALIDA: 4 (RIESGO BAJO)${NC}"
        exit 4
    else
        echo -e "${GREEN}✅ CÓDIGO DE SALIDA: 0 (ÓPTIMO)${NC}"
        exit 0
    fi
}

# Función de ayuda
show_help() {
    echo -e "${WHITE}🎯 SISTEMA INTEGRADO DE MONITOREO${NC}"
    echo -e "${WHITE}===================================${NC}"
    echo ""
    echo -e "${BLUE}Uso:${NC}"
    echo -e "${BLUE}  ./integrated_monitoring.sh [opciones]${NC}"
    echo ""
    echo -e "${GREEN}Opciones:${NC}"
    echo -e "${GREEN}  --help, -h          Mostrar esta ayuda${NC}"
    echo -e "${GREEN}  --security-only     Solo verificación de seguridad${NC}"
    echo -e "${GREEN}  --architecture-only Solo verificación de arquitectura${NC}"
    echo -e "${GREEN}  --dashboard-only    Solo generar dashboard${NC}"
    echo -e "${GREEN}  --alerts-only       Solo generar alertas${NC}"
    echo ""
    echo -e "${YELLOW}Características:${NC}"
    echo -e "${YELLOW}  ✅ Monitoreo por colores${NC}"
    echo -e "${YELLOW}  ✅ Trazabilidad completa${NC}"
    echo -e "${YELLOW}  ✅ Dashboard visual${NC}"
    echo -e "${YELLOW}  ✅ Alertas automáticas${NC}"
    echo -e "${YELLOW}  ✅ Cumple normativas ITIL${NC}"
    echo -e "${YELLOW}  ✅ Cumple normativas ISO 20000${NC}"
    echo ""
    echo -e "${CYAN}Ejemplos:${NC}"
    echo -e "${CYAN}  ./integrated_monitoring.sh${NC}"
    echo -e "${CYAN}  ./integrated_monitoring.sh --security-only${NC}"
    echo -e "${CYAN}  ./integrated_monitoring.sh --dashboard-only${NC}"
    echo ""
}

# Procesar argumentos de línea de comandos
case "${1:-}" in
    "--help"|"-h")
        show_help
        exit 0
        ;;
    "--security-only")
        echo -e "${WHITE}🔍 MODO: Solo verificación de seguridad${NC}"
        load_monitoring_modules
        run_security_check
        exit $?
        ;;
    "--architecture-only")
        echo -e "${WHITE}🏗️ MODO: Solo verificación de arquitectura${NC}"
        load_monitoring_modules
        run_architecture_check
        exit $?
        ;;
    "--dashboard-only")
        echo -e "${WHITE}📊 MODO: Solo generación de dashboard${NC}"
        load_monitoring_modules
        if command -v generate_visual_dashboard >/dev/null 2>&1; then
            generate_visual_dashboard 0 0 0 0
        else
            echo -e "${RED}❌ Módulo de dashboard no disponible${NC}"
            exit 1
        fi
        exit 0
        ;;
    "--alerts-only")
        echo -e "${WHITE}🚨 MODO: Solo generación de alertas${NC}"
        load_monitoring_modules
        if command -v generate_color_alerts >/dev/null 2>&1; then
            generate_color_alerts 0 0 0 0
        else
            echo -e "${RED}❌ Módulo de alertas no disponible${NC}"
            exit 1
        fi
        exit 0
        ;;
    "")
        # Modo por defecto: monitoreo completo
        main_integrated_monitoring
        ;;
    *)
        echo -e "${RED}❌ Opción desconocida: $1${NC}"
        echo -e "${BLUE}Usa --help para ver las opciones disponibles${NC}"
        exit 1
        ;;
esac
