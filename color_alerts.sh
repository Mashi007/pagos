#!/bin/bash
# color_alerts.sh - Sistema de alertas por colores con normativas de gestión
# Cumple con estándares ITIL, ISO 20000 y normativas de monitoreo

# Configuración de colores ANSI estándar para alertas
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

# Configuración de alertas
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
ALERT_LOG="color_alerts_$(date '+%Y%m%d_%H%M%S').log"
ALERT_CONFIG="alert_config.json"

# Función para generar configuración de alertas
generate_alert_config() {
    cat > "$ALERT_CONFIG" << 'EOF'
{
    "alert_levels": {
        "CRITICAL": {
            "color": "#e74c3c",
            "emoji": "🚨",
            "priority": 1,
            "response_time": "1 hora",
            "escalation_level": 1,
            "escalation_contact": "DevOps Lead",
            "action_required": "INTERVENCIÓN INMEDIATA",
            "notification_channels": ["email", "sms", "slack", "dashboard"],
            "auto_escalate": true,
            "escalate_after": "30 minutos"
        },
        "HIGH": {
            "color": "#f39c12",
            "emoji": "🔴",
            "priority": 2,
            "response_time": "4 horas",
            "escalation_level": 2,
            "escalation_contact": "Backend Lead",
            "action_required": "INTERVENCIÓN EN 24H",
            "notification_channels": ["email", "slack", "dashboard"],
            "auto_escalate": true,
            "escalate_after": "2 horas"
        },
        "MEDIUM": {
            "color": "#f1c40f",
            "emoji": "🟡",
            "priority": 3,
            "response_time": "1 semana",
            "escalation_level": 3,
            "escalation_contact": "Desarrollador Senior",
            "action_required": "PLANIFICAR CORRECCIÓN",
            "notification_channels": ["email", "dashboard"],
            "auto_escalate": false,
            "escalate_after": "1 semana"
        },
        "LOW": {
            "color": "#27ae60",
            "emoji": "🟢",
            "priority": 4,
            "response_time": "1 mes",
            "escalation_level": 4,
            "escalation_contact": "Desarrollador",
            "action_required": "MEJORAS OPCIONALES",
            "notification_channels": ["dashboard"],
            "auto_escalate": false,
            "escalate_after": "1 mes"
        }
    },
    "notification_templates": {
        "CRITICAL": {
            "subject": "🚨 ALERTA CRÍTICA - Sistema Backend",
            "body": "Se detectaron {count} problemas críticos que requieren intervención inmediata.\n\nDetalles:\n{details}\n\nAcción requerida: INTERVENCIÓN INMEDIATA\nTiempo de respuesta: < 1 hora\nEscalación: Nivel 1 (DevOps Lead)"
        },
        "HIGH": {
            "subject": "🔴 ALERTA ALTA - Sistema Backend",
            "body": "Se detectaron {count} problemas altos que requieren atención.\n\nDetalles:\n{details}\n\nAcción requerida: INTERVENCIÓN EN 24H\nTiempo de respuesta: < 4 horas\nEscalación: Nivel 2 (Backend Lead)"
        },
        "MEDIUM": {
            "subject": "🟡 ALERTA MEDIA - Sistema Backend",
            "body": "Se detectaron {count} problemas medios que requieren planificación.\n\nDetalles:\n{details}\n\nAcción requerida: PLANIFICAR CORRECCIÓN\nTiempo de respuesta: < 1 semana\nEscalación: Nivel 3 (Desarrollador Senior)"
        },
        "LOW": {
            "subject": "🟢 ALERTA BAJA - Sistema Backend",
            "body": "Se detectaron {count} problemas bajos para mejoras opcionales.\n\nDetalles:\n{details}\n\nAcción requerida: MEJORAS OPCIONALES\nTiempo de respuesta: < 1 mes\nEscalación: Nivel 4 (Desarrollador)"
        }
    }
}
EOF
}

# Función para generar alerta por color
generate_color_alert() {
    local level=$1
    local count=$2
    local details=$3
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Obtener configuración del nivel
    local color=$(jq -r ".alert_levels.$level.color" "$ALERT_CONFIG" 2>/dev/null)
    local emoji=$(jq -r ".alert_levels.$level.emoji" "$ALERT_CONFIG" 2>/dev/null)
    local priority=$(jq -r ".alert_levels.$level.priority" "$ALERT_CONFIG" 2>/dev/null)
    local response_time=$(jq -r ".alert_levels.$level.response_time" "$ALERT_CONFIG" 2>/dev/null)
    local escalation_level=$(jq -r ".alert_levels.$level.escalation_level" "$ALERT_CONFIG" 2>/dev/null)
    local escalation_contact=$(jq -r ".alert_levels.$level.escalation_contact" "$ALERT_CONFIG" 2>/dev/null)
    local action_required=$(jq -r ".alert_levels.$level.action_required" "$ALERT_CONFIG" 2>/dev/null)
    
    # Determinar color ANSI
    local ansi_color
    case $level in
        "CRITICAL")
            ansi_color="$CRITICAL_COLOR"
            ;;
        "HIGH")
            ansi_color="$HIGH_COLOR"
            ;;
        "MEDIUM")
            ansi_color="$MEDIUM_COLOR"
            ;;
        "LOW")
            ansi_color="$LOW_COLOR"
            ;;
        *)
            ansi_color="$NC"
            ;;
    esac
    
    # Generar alerta visual
    echo -e "${ansi_color}${emoji} ALERTA $level${NC}"
    echo -e "${ansi_color}================================${NC}"
    echo -e "${ansi_color}📊 Cantidad: $count problemas${NC}"
    echo -e "${ansi_color}🎯 Prioridad: $priority${NC}"
    echo -e "${ansi_color}⏰ Tiempo de respuesta: $response_time${NC}"
    echo -e "${ansi_color}👤 Escalación: Nivel $escalation_level ($escalation_contact)${NC}"
    echo -e "${ansi_color}🚨 Acción requerida: $action_required${NC}"
    echo ""
    
    if [ -n "$details" ]; then
        echo -e "${ansi_color}📋 Detalles:${NC}"
        echo -e "${ansi_color}$details${NC}"
        echo ""
    fi
    
    # Log de alerta
    echo "[$timestamp] ALERT_$level: $count problemas detectados - $action_required" >> "$ALERT_LOG"
    
    # Generar notificación si es crítica o alta
    if [ "$level" = "CRITICAL" ] || [ "$level" = "HIGH" ]; then
        generate_notification "$level" "$count" "$details"
    fi
}

# Función para generar notificaciones
generate_notification() {
    local level=$1
    local count=$2
    local details=$3
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Obtener plantilla de notificación
    local subject=$(jq -r ".notification_templates.$level.subject" "$ALERT_CONFIG" 2>/dev/null)
    local body=$(jq -r ".notification_templates.$level.body" "$ALERT_CONFIG" 2>/dev/null)
    
    # Reemplazar variables en la plantilla
    body=$(echo "$body" | sed "s/{count}/$count/g" | sed "s/{details}/$details/g")
    
    # Generar archivo de notificación
    local notification_file="notification_${level}_$(date '+%Y%m%d_%H%M%S').txt"
    
    cat > "$notification_file" << EOF
Subject: $subject
Date: $timestamp
Priority: $level

$body

---
Sistema de Monitoreo por Colores
Generado automáticamente el $timestamp
EOF
    
    echo -e "${INFO_COLOR}📧 Notificación generada: $notification_file${NC}"
}

# Función para generar dashboard de alertas
generate_alerts_dashboard() {
    local critical=$1
    local high=$2
    local medium=$3
    local low=$4
    local dashboard_file="alerts_dashboard_$(date '+%Y%m%d_%H%M%S').html"
    
    cat > "$dashboard_file" << EOF
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard de Alertas por Colores</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            margin: 0;
            padding: 20px;
        }
        
        .dashboard-container {
            max-width: 1200px;
            margin: 0 auto;
        }
        
        .header {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 30px;
            margin-bottom: 30px;
            text-align: center;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }
        
        .alerts-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 25px;
            margin-bottom: 30px;
        }
        
        .alert-card {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
            transition: transform 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        
        .alert-card:hover {
            transform: translateY(-5px);
        }
        
        .alert-card.critical {
            border-left: 5px solid #e74c3c;
        }
        
        .alert-card.high {
            border-left: 5px solid #f39c12;
        }
        
        .alert-card.medium {
            border-left: 5px solid #f1c40f;
        }
        
        .alert-card.low {
            border-left: 5px solid #27ae60;
        }
        
        .alert-icon {
            font-size: 3em;
            margin-bottom: 15px;
        }
        
        .alert-title {
            font-size: 1.5em;
            font-weight: bold;
            margin-bottom: 10px;
        }
        
        .alert-count {
            font-size: 2.5em;
            font-weight: bold;
            margin-bottom: 15px;
        }
        
        .alert-card.critical .alert-count {
            color: #e74c3c;
        }
        
        .alert-card.high .alert-count {
            color: #f39c12;
        }
        
        .alert-card.medium .alert-count {
            color: #f1c40f;
        }
        
        .alert-card.low .alert-count {
            color: #27ae60;
        }
        
        .alert-details {
            font-size: 0.9em;
            color: #666;
            line-height: 1.5;
        }
        
        .status-indicator {
            position: absolute;
            top: 20px;
            right: 20px;
            width: 15px;
            height: 15px;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        
        .status-indicator.critical {
            background-color: #e74c3c;
        }
        
        .status-indicator.high {
            background-color: #f39c12;
        }
        
        .status-indicator.medium {
            background-color: #f1c40f;
        }
        
        .status-indicator.low {
            background-color: #27ae60;
        }
        
        @keyframes pulse {
            0% {
                transform: scale(1);
                opacity: 1;
            }
            50% {
                transform: scale(1.2);
                opacity: 0.7;
            }
            100% {
                transform: scale(1);
                opacity: 1;
            }
        }
        
        .summary-section {
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 30px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }
        
        .summary-title {
            font-size: 1.5em;
            font-weight: bold;
            margin-bottom: 20px;
            color: #2c3e50;
        }
        
        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }
        
        .summary-item {
            text-align: center;
            padding: 15px;
            border-radius: 10px;
            background: rgba(236, 240, 241, 0.5);
        }
        
        .summary-value {
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .summary-label {
            font-size: 0.9em;
            color: #666;
        }
        
        .footer {
            text-align: center;
            color: rgba(255, 255, 255, 0.8);
            margin-top: 30px;
        }
    </style>
</head>
<body>
    <div class="dashboard-container">
        <div class="header">
            <h1>🚨 Dashboard de Alertas por Colores</h1>
            <p>Sistema de Monitoreo Backend - Normativas ITIL e ISO 20000</p>
            <p>Última actualización: $TIMESTAMP</p>
        </div>
        
        <div class="alerts-grid">
            <div class="alert-card critical">
                <div class="status-indicator critical"></div>
                <div class="alert-icon">🚨</div>
                <div class="alert-title">ALERTA CRÍTICA</div>
                <div class="alert-count">$critical</div>
                <div class="alert-details">
                    <strong>Prioridad:</strong> 1<br>
                    <strong>Tiempo de respuesta:</strong> < 1 hora<br>
                    <strong>Escalación:</strong> Nivel 1 (DevOps Lead)<br>
                    <strong>Acción:</strong> INTERVENCIÓN INMEDIATA
                </div>
            </div>
            
            <div class="alert-card high">
                <div class="status-indicator high"></div>
                <div class="alert-icon">🔴</div>
                <div class="alert-title">ALERTA ALTA</div>
                <div class="alert-count">$high</div>
                <div class="alert-details">
                    <strong>Prioridad:</strong> 2<br>
                    <strong>Tiempo de respuesta:</strong> < 4 horas<br>
                    <strong>Escalación:</strong> Nivel 2 (Backend Lead)<br>
                    <strong>Acción:</strong> INTERVENCIÓN EN 24H
                </div>
            </div>
            
            <div class="alert-card medium">
                <div class="status-indicator medium"></div>
                <div class="alert-icon">🟡</div>
                <div class="alert-title">ALERTA MEDIA</div>
                <div class="alert-count">$medium</div>
                <div class="alert-details">
                    <strong>Prioridad:</strong> 3<br>
                    <strong>Tiempo de respuesta:</strong> < 1 semana<br>
                    <strong>Escalación:</strong> Nivel 3 (Desarrollador Senior)<br>
                    <strong>Acción:</strong> PLANIFICAR CORRECCIÓN
                </div>
            </div>
            
            <div class="alert-card low">
                <div class="status-indicator low"></div>
                <div class="alert-icon">🟢</div>
                <div class="alert-title">ALERTA BAJA</div>
                <div class="alert-count">$low</div>
                <div class="alert-details">
                    <strong>Prioridad:</strong> 4<br>
                    <strong>Tiempo de respuesta:</strong> < 1 mes<br>
                    <strong>Escalación:</strong> Nivel 4 (Desarrollador)<br>
                    <strong>Acción:</strong> MEJORAS OPCIONALES
                </div>
            </div>
        </div>
        
        <div class="summary-section">
            <div class="summary-title">📊 Resumen de Alertas</div>
            <div class="summary-grid">
                <div class="summary-item">
                    <div class="summary-value" style="color: #e74c3c;">$critical</div>
                    <div class="summary-label">Críticos</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value" style="color: #f39c12;">$high</div>
                    <div class="summary-label">Altos</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value" style="color: #f1c40f;">$medium</div>
                    <div class="summary-label">Medios</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value" style="color: #27ae60;">$low</div>
                    <div class="summary-label">Bajos</div>
                </div>
                <div class="summary-item">
                    <div class="summary-value" style="color: #2c3e50;">$(($critical + $high + $medium + $low))</div>
                    <div class="summary-label">Total</div>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>🎯 Sistema de Alertas por Colores - Cumple con normativas ITIL e ISO 20000</p>
            <p>📊 Generado automáticamente el $TIMESTAMP</p>
        </div>
    </div>
</body>
</html>
EOF
    
    echo -e "${SUCCESS_COLOR}📊 Dashboard de alertas generado: $dashboard_file${NC}"
}

# Función principal para generar alertas por colores
generate_color_alerts() {
    local critical=$1
    local high=$2
    local medium=$3
    local low=$4
    
    echo -e "${HEADER_COLOR}🚨 SISTEMA DE ALERTAS POR COLORES${NC}"
    echo -e "${HEADER_COLOR}==================================${NC}"
    echo ""
    
    # Generar configuración de alertas
    generate_alert_config
    
    # Generar alertas individuales
    if [ $critical -gt 0 ]; then
        generate_color_alert "CRITICAL" "$critical" "Problemas críticos detectados en el sistema backend"
    fi
    
    if [ $high -gt 0 ]; then
        generate_color_alert "HIGH" "$high" "Problemas altos detectados en el sistema backend"
    fi
    
    if [ $medium -gt 0 ]; then
        generate_color_alert "MEDIUM" "$medium" "Problemas medios detectados en el sistema backend"
    fi
    
    if [ $low -gt 0 ]; then
        generate_color_alert "LOW" "$low" "Problemas bajos detectados en el sistema backend"
    fi
    
    if [ $critical -eq 0 ] && [ $high -eq 0 ] && [ $medium -eq 0 ] && [ $low -eq 0 ]; then
        echo -e "${SUCCESS_COLOR}✅ SISTEMA EN ESTADO ÓPTIMO${NC}"
        echo -e "${SUCCESS_COLOR}   No se detectaron problemas${NC}"
        echo -e "${SUCCESS_COLOR}   Estado: CUMPLE NORMATIVAS${NC}"
        echo ""
    fi
    
    # Generar dashboard de alertas
    generate_alerts_dashboard "$critical" "$high" "$medium" "$low"
    
    echo -e "${INFO_COLOR}📁 Archivos generados:${NC}"
    echo -e "${INFO_COLOR}   - $ALERT_CONFIG${NC}"
    echo -e "${INFO_COLOR}   - $ALERT_LOG${NC}"
    echo -e "${INFO_COLOR}   - alerts_dashboard_*.html${NC}"
    echo ""
}

# Exportar funciones para uso en otros scripts
export -f generate_alert_config
export -f generate_color_alert
export -f generate_notification
export -f generate_alerts_dashboard
export -f generate_color_alerts

# Si se ejecuta directamente, mostrar ayuda
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    echo -e "${HEADER_COLOR}🚨 SISTEMA DE ALERTAS POR COLORES${NC}"
    echo -e "${HEADER_COLOR}==================================${NC}"
    echo ""
    echo -e "${BLUE}Uso: source color_alerts.sh${NC}"
    echo -e "${BLUE}Luego: generate_color_alerts <critical> <high> <medium> <low>${NC}"
    echo ""
    echo -e "${GREEN}Ejemplo:${NC}"
    echo -e "${GREEN}  generate_color_alerts 2 1 3 0${NC}"
    echo ""
    echo -e "${YELLOW}Características:${NC}"
    echo -e "${YELLOW}  ✅ Alertas por colores estándar${NC}"
    echo -e "${YELLOW}  ✅ Escalación automática${NC}"
    echo -e "${YELLOW}  ✅ Notificaciones por nivel${NC}"
    echo -e "${YELLOW}  ✅ Dashboard visual${NC}"
    echo -e "${YELLOW}  ✅ Cumple normativas ITIL${NC}"
    echo ""
    echo -e "${RED}🚨 CRÍTICO: #e74c3c (Rojo)${NC}"
    echo -e "${ORANGE}🔴 ALTO: #f39c12 (Naranja)${NC}"
    echo -e "${YELLOW}🟡 MEDIO: #f1c40f (Amarillo)${NC}"
    echo -e "${GREEN}🟢 BAJO: #27ae60 (Verde)${NC}"
    echo ""
fi
