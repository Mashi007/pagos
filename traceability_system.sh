#!/bin/bash
# traceability_system.sh - Sistema de trazabilidad de problemas
# Cumple con normativas ISO 20000 e ITIL para gestión de problemas

# Configuración de trazabilidad
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
SESSION_ID=$(uuidgen | cut -d'-' -f1)
TRACE_DB="traceability_$(date '+%Y%m%d').json"
PROBLEM_REGISTRY="problem_registry_$(date '+%Y%m%d').csv"

# Función para generar ID único de problema
generate_problem_id() {
    local component=$1
    local severity=$2
    local timestamp=$(date '+%Y%m%d%H%M%S')
    local random=$(openssl rand -hex 2)
    echo "${component}_${severity}_${timestamp}_${random}"
}

# Función para registrar problema con trazabilidad completa
register_problem() {
    local problem_id=$1
    local severity=$2
    local component=$3
    local description=$4
    local code=$5
    local file_path=$6
    local line_number=$7
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S.%3N')
    
    # Registrar en base de datos JSON
    cat >> "$TRACE_DB" << EOF
{
    "problem_id": "$problem_id",
    "timestamp": "$timestamp",
    "session_id": "$SESSION_ID",
    "severity": "$severity",
    "component": "$component",
    "description": "$description",
    "code": "$code",
    "file_path": "$file_path",
    "line_number": "$line_number",
    "status": "OPEN",
    "assigned_to": "",
    "resolution": "",
    "resolution_date": "",
    "verification": "",
    "closure_date": ""
},
EOF
    
    # Registrar en registro CSV para análisis
    echo "$problem_id,$timestamp,$SESSION_ID,$severity,$component,$description,$code,$file_path,$line_number,OPEN" >> "$PROBLEM_REGISTRY"
    
    # Log de trazabilidad
    echo "[$timestamp] [$SESSION_ID] PROBLEM_REGISTERED [$problem_id] [$severity] [$component] $description"
}

# Función para actualizar estado de problema
update_problem_status() {
    local problem_id=$1
    local new_status=$2
    local assigned_to=$3
    local resolution=$4
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S.%3N')
    
    # Actualizar en base de datos JSON
    local temp_file=$(mktemp)
    jq --arg id "$problem_id" --arg status "$new_status" --arg assigned "$assigned_to" --arg resolution "$resolution" --arg timestamp "$timestamp" '
        map(if .problem_id == $id then 
            .status = $status | 
            .assigned_to = $assigned | 
            .resolution = $resolution | 
            .resolution_date = $timestamp 
        else . end)
    ' "$TRACE_DB" > "$temp_file" && mv "$temp_file" "$TRACE_DB"
    
    # Actualizar en registro CSV
    sed -i "s/$problem_id,.*,OPEN/$problem_id,$timestamp,$SESSION_ID,$new_status,$assigned_to,$resolution/" "$PROBLEM_REGISTRY"
    
    echo "[$timestamp] [$SESSION_ID] PROBLEM_UPDATED [$problem_id] [$new_status] [$assigned_to]"
}

# Función para cerrar problema
close_problem() {
    local problem_id=$1
    local verification=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S.%3N')
    
    # Actualizar estado a cerrado
    local temp_file=$(mktemp)
    jq --arg id "$problem_id" --arg verification "$verification" --arg timestamp "$timestamp" '
        map(if .problem_id == $id then 
            .status = "CLOSED" | 
            .verification = $verification | 
            .closure_date = $timestamp 
        else . end)
    ' "$TRACE_DB" > "$temp_file" && mv "$temp_file" "$TRACE_DB"
    
    # Actualizar en registro CSV
    sed -i "s/$problem_id,.*,OPEN/$problem_id,$timestamp,$SESSION_ID,CLOSED,$verification/" "$PROBLEM_REGISTRY"
    
    echo "[$timestamp] [$SESSION_ID] PROBLEM_CLOSED [$problem_id] [$verification]"
}

# Función para generar reporte de trazabilidad
generate_traceability_report() {
    local report_file="traceability_report_$(date '+%Y%m%d_%H%M%S').html"
    
    cat > "$report_file" << EOF
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Reporte de Trazabilidad de Problemas</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background-color: #2c3e50; color: white; padding: 20px; border-radius: 5px; }
        .summary { background-color: #ecf0f1; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .critical { color: #e74c3c; font-weight: bold; }
        .high { color: #f39c12; font-weight: bold; }
        .medium { color: #f1c40f; font-weight: bold; }
        .low { color: #27ae60; font-weight: bold; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
        th { background-color: #34495e; color: white; }
        .status-open { background-color: #e74c3c; color: white; }
        .status-in-progress { background-color: #f39c12; color: white; }
        .status-resolved { background-color: #3498db; color: white; }
        .status-closed { background-color: #27ae60; color: white; }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 Reporte de Trazabilidad de Problemas</h1>
        <p>Generado el: $(date '+%Y-%m-%d %H:%M:%S')</p>
        <p>Session ID: $SESSION_ID</p>
    </div>
    
    <div class="summary">
        <h2>📊 Resumen Ejecutivo</h2>
        <p><span class="critical">🚨 Críticos:</span> $(grep -c "CRITICAL" "$PROBLEM_REGISTRY" 2>/dev/null || echo "0")</p>
        <p><span class="high">🔴 Altos:</span> $(grep -c "HIGH" "$PROBLEM_REGISTRY" 2>/dev/null || echo "0")</p>
        <p><span class="medium">🟡 Medios:</span> $(grep -c "MEDIUM" "$PROBLEM_REGISTRY" 2>/dev/null || echo "0")</p>
        <p><span class="low">🟢 Bajos:</span> $(grep -c "LOW" "$PROBLEM_REGISTRY" 2>/dev/null || echo "0")</p>
    </div>
    
    <h2>📋 Detalle de Problemas</h2>
    <table>
        <tr>
            <th>ID</th>
            <th>Timestamp</th>
            <th>Severidad</th>
            <th>Componente</th>
            <th>Descripción</th>
            <th>Código</th>
            <th>Archivo</th>
            <th>Línea</th>
            <th>Estado</th>
        </tr>
EOF
    
    # Generar filas de la tabla
    if [ -f "$PROBLEM_REGISTRY" ]; then
        while IFS=',' read -r id timestamp session severity component description code file_path line_number status; do
            case $severity in
                "CRITICAL")
                    severity_class="critical"
                    ;;
                "HIGH")
                    severity_class="high"
                    ;;
                "MEDIUM")
                    severity_class="medium"
                    ;;
                "LOW")
                    severity_class="low"
                    ;;
                *)
                    severity_class=""
                    ;;
            esac
            
            case $status in
                "OPEN")
                    status_class="status-open"
                    ;;
                "IN_PROGRESS")
                    status_class="status-in-progress"
                    ;;
                "RESOLVED")
                    status_class="status-resolved"
                    ;;
                "CLOSED")
                    status_class="status-closed"
                    ;;
                *)
                    status_class=""
                    ;;
            esac
            
            cat >> "$report_file" << EOF
        <tr>
            <td>$id</td>
            <td>$timestamp</td>
            <td class="$severity_class">$severity</td>
            <td>$component</td>
            <td>$description</td>
            <td>$code</td>
            <td>$file_path</td>
            <td>$line_number</td>
            <td class="$status_class">$status</td>
        </tr>
EOF
        done < "$PROBLEM_REGISTRY"
    fi
    
    cat >> "$report_file" << EOF
    </table>
    
    <div class="summary">
        <h2>📈 Métricas de Trazabilidad</h2>
        <p><strong>Total de problemas registrados:</strong> $(wc -l < "$PROBLEM_REGISTRY" 2>/dev/null || echo "0")</p>
        <p><strong>Problemas abiertos:</strong> $(grep -c "OPEN" "$PROBLEM_REGISTRY" 2>/dev/null || echo "0")</p>
        <p><strong>Problemas en progreso:</strong> $(grep -c "IN_PROGRESS" "$PROBLEM_REGISTRY" 2>/dev/null || echo "0")</p>
        <p><strong>Problemas resueltos:</strong> $(grep -c "RESOLVED" "$PROBLEM_REGISTRY" 2>/dev/null || echo "0")</p>
        <p><strong>Problemas cerrados:</strong> $(grep -c "CLOSED" "$PROBLEM_REGISTRY" 2>/dev/null || echo "0")</p>
    </div>
    
    <div class="summary">
        <h2>🎯 Recomendaciones</h2>
        <ul>
            <li>Priorizar problemas críticos para resolución inmediata</li>
            <li>Asignar responsables para cada problema abierto</li>
            <li>Establecer tiempos de respuesta según severidad</li>
            <li>Implementar seguimiento regular del estado</li>
            <li>Documentar lecciones aprendidas</li>
        </ul>
    </div>
</body>
</html>
EOF
    
    echo "📊 Reporte de trazabilidad generado: $report_file"
}

# Función para generar dashboard de monitoreo en tiempo real
generate_realtime_dashboard() {
    local dashboard_file="realtime_dashboard_$(date '+%Y%m%d_%H%M%S').html"
    
    cat > "$dashboard_file" << EOF
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard de Monitoreo en Tiempo Real</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }
        .dashboard { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 20px; }
        .card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .critical { border-left: 5px solid #e74c3c; }
        .high { border-left: 5px solid #f39c12; }
        .medium { border-left: 5px solid #f1c40f; }
        .low { border-left: 5px solid #27ae60; }
        .metric { font-size: 2em; font-weight: bold; margin: 10px 0; }
        .progress-bar { width: 100%; height: 20px; background-color: #ecf0f1; border-radius: 10px; overflow: hidden; }
        .progress-fill { height: 100%; transition: width 0.3s ease; }
        .critical-fill { background-color: #e74c3c; }
        .high-fill { background-color: #f39c12; }
        .medium-fill { background-color: #f1c40f; }
        .low-fill { background-color: #27ae60; }
        .auto-refresh { position: fixed; top: 20px; right: 20px; background: #3498db; color: white; padding: 10px; border-radius: 5px; }
    </style>
    <script>
        // Auto-refresh cada 30 segundos
        setTimeout(function() {
            location.reload();
        }, 30000);
    </script>
</head>
<body>
    <div class="auto-refresh">🔄 Auto-refresh en 30s</div>
    
    <h1>📊 Dashboard de Monitoreo en Tiempo Real</h1>
    <p>Última actualización: $(date '+%Y-%m-%d %H:%M:%S')</p>
    
    <div class="dashboard">
        <div class="card critical">
            <h2>🚨 Problemas Críticos</h2>
            <div class="metric">$(grep -c "CRITICAL" "$PROBLEM_REGISTRY" 2>/dev/null || echo "0")</div>
            <div class="progress-bar">
                <div class="progress-fill critical-fill" style="width: $(echo "scale=2; $(grep -c "CRITICAL" "$PROBLEM_REGISTRY" 2>/dev/null || echo "0") * 100 / $(wc -l < "$PROBLEM_REGISTRY" 2>/dev/null || echo "1")" | bc)%"></div>
            </div>
        </div>
        
        <div class="card high">
            <h2>🔴 Problemas Altos</h2>
            <div class="metric">$(grep -c "HIGH" "$PROBLEM_REGISTRY" 2>/dev/null || echo "0")</div>
            <div class="progress-bar">
                <div class="progress-fill high-fill" style="width: $(echo "scale=2; $(grep -c "HIGH" "$PROBLEM_REGISTRY" 2>/dev/null || echo "0") * 100 / $(wc -l < "$PROBLEM_REGISTRY" 2>/dev/null || echo "1")" | bc)%"></div>
            </div>
        </div>
        
        <div class="card medium">
            <h2>🟡 Problemas Medios</h2>
            <div class="metric">$(grep -c "MEDIUM" "$PROBLEM_REGISTRY" 2>/dev/null || echo "0")</div>
            <div class="progress-bar">
                <div class="progress-fill medium-fill" style="width: $(echo "scale=2; $(grep -c "MEDIUM" "$PROBLEM_REGISTRY" 2>/dev/null || echo "0") * 100 / $(wc -l < "$PROBLEM_REGISTRY" 2>/dev/null || echo "1")" | bc)%"></div>
            </div>
        </div>
        
        <div class="card low">
            <h2>🟢 Problemas Bajos</h2>
            <div class="metric">$(grep -c "LOW" "$PROBLEM_REGISTRY" 2>/dev/null || echo "0")</div>
            <div class="progress-bar">
                <div class="progress-fill low-fill" style="width: $(echo "scale=2; $(grep -c "LOW" "$PROBLEM_REGISTRY" 2>/dev/null || echo "0") * 100 / $(wc -l < "$PROBLEM_REGISTRY" 2>/dev/null || echo "1")" | bc)%"></div>
            </div>
        </div>
    </div>
    
    <div class="card">
        <h2>📈 Tendencias</h2>
        <p>Problemas abiertos: $(grep -c "OPEN" "$PROBLEM_REGISTRY" 2>/dev/null || echo "0")</p>
        <p>Problemas en progreso: $(grep -c "IN_PROGRESS" "$PROBLEM_REGISTRY" 2>/dev/null || echo "0")</p>
        <p>Problemas resueltos: $(grep -c "RESOLVED" "$PROBLEM_REGISTRY" 2>/dev/null || echo "0")</p>
        <p>Problemas cerrados: $(grep -c "CLOSED" "$PROBLEM_REGISTRY" 2>/dev/null || echo "0")</p>
    </div>
</body>
</html>
EOF
    
    echo "📊 Dashboard en tiempo real generado: $dashboard_file"
}

# Función para generar alertas por colores
generate_color_alerts() {
    local critical=$(grep -c "CRITICAL" "$PROBLEM_REGISTRY" 2>/dev/null || echo "0")
    local high=$(grep -c "HIGH" "$PROBLEM_REGISTRY" 2>/dev/null || echo "0")
    local medium=$(grep -c "MEDIUM" "$PROBLEM_REGISTRY" 2>/dev/null || echo "0")
    local low=$(grep -c "LOW" "$PROBLEM_REGISTRY" 2>/dev/null || echo "0")
    
    echo "🚨 SISTEMA DE ALERTAS POR COLORES"
    echo "=================================="
    echo ""
    
    if [ $critical -gt 0 ]; then
        echo "🚨 ALERTA CRÍTICA: $critical problemas críticos detectados"
        echo "   Color: ROJO (#e74c3c)"
        echo "   Acción: INTERVENCIÓN INMEDIATA"
        echo "   Tiempo: < 1 hora"
        echo ""
    fi
    
    if [ $high -gt 0 ]; then
        echo "🔴 ALERTA ALTA: $high problemas altos detectados"
        echo "   Color: NARANJA (#f39c12)"
        echo "   Acción: INTERVENCIÓN EN 24H"
        echo "   Tiempo: < 4 horas"
        echo ""
    fi
    
    if [ $medium -gt 0 ]; then
        echo "🟡 ALERTA MEDIA: $medium problemas medios detectados"
        echo "   Color: AMARILLO (#f1c40f)"
        echo "   Acción: PLANIFICAR CORRECCIÓN"
        echo "   Tiempo: < 1 semana"
        echo ""
    fi
    
    if [ $low -gt 0 ]; then
        echo "🟢 ALERTA BAJA: $low problemas bajos detectados"
        echo "   Color: VERDE (#27ae60)"
        echo "   Acción: MEJORAS OPCIONALES"
        echo "   Tiempo: < 1 mes"
        echo ""
    fi
    
    if [ $critical -eq 0 ] && [ $high -eq 0 ] && [ $medium -eq 0 ] && [ $low -eq 0 ]; then
        echo "✅ SISTEMA EN ESTADO ÓPTIMO"
        echo "   Color: VERDE (#27ae60)"
        echo "   Estado: CUMPLE NORMATIVAS"
        echo ""
    fi
}

# Exportar funciones para uso en otros scripts
export -f generate_problem_id
export -f register_problem
export -f update_problem_status
export -f close_problem
export -f generate_traceability_report
export -f generate_realtime_dashboard
export -f generate_color_alerts

# Si se ejecuta directamente, mostrar ayuda
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    echo "🔍 SISTEMA DE TRAZABILIDAD DE PROBLEMAS"
    echo "======================================"
    echo ""
    echo "Uso: source traceability_system.sh"
    echo ""
    echo "Funciones disponibles:"
    echo "  generate_problem_id <component> <severity>"
    echo "  register_problem <id> <severity> <component> <description> <code> <file> <line>"
    echo "  update_problem_status <id> <status> <assigned_to> <resolution>"
    echo "  close_problem <id> <verification>"
    echo "  generate_traceability_report"
    echo "  generate_realtime_dashboard"
    echo "  generate_color_alerts"
    echo ""
    echo "Archivos generados:"
    echo "  $TRACE_DB - Base de datos JSON"
    echo "  $PROBLEM_REGISTRY - Registro CSV"
    echo ""
fi
