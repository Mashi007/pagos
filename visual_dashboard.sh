#!/bin/bash
# visual_dashboard.sh - Dashboard de monitoreo visual con colores
# Sistema de monitoreo en tiempo real con normativas de gestión de problemas

# Configuración de colores ANSI para dashboard
RED='\033[0;31m'      # Crítico
ORANGE='\033[0;33m'   # Alto
YELLOW='\033[1;33m'   # Medio
GREEN='\033[0;32m'    # Bajo
BLUE='\033[0;34m'     # Info
PURPLE='\033[0;35m'   # Advertencia
CYAN='\033[0;36m'     # Éxito
WHITE='\033[1;37m'    # Encabezados
NC='\033[0m'          # Sin color

# Configuración de dashboard
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
DASHBOARD_FILE="visual_dashboard_$(date '+%Y%m%d_%H%M%S').html"
CSS_FILE="dashboard_styles.css"
JS_FILE="dashboard_scripts.js"

# Función para generar CSS del dashboard
generate_dashboard_css() {
    cat > "$CSS_FILE" << 'EOF'
/* Dashboard de Monitoreo Visual - Estilos */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
    color: #333;
}

.dashboard-container {
    max-width: 1400px;
    margin: 0 auto;
    padding: 20px;
}

.header {
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(10px);
    border-radius: 15px;
    padding: 30px;
    margin-bottom: 30px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
    text-align: center;
}

.header h1 {
    font-size: 2.5em;
    color: #2c3e50;
    margin-bottom: 10px;
}

.header .subtitle {
    color: #7f8c8d;
    font-size: 1.2em;
}

.metrics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 25px;
    margin-bottom: 30px;
}

.metric-card {
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(10px);
    border-radius: 15px;
    padding: 25px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
    transition: transform 0.3s ease, box-shadow 0.3s ease;
    position: relative;
    overflow: hidden;
}

.metric-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
}

.metric-card.critical {
    border-left: 5px solid #e74c3c;
}

.metric-card.high {
    border-left: 5px solid #f39c12;
}

.metric-card.medium {
    border-left: 5px solid #f1c40f;
}

.metric-card.low {
    border-left: 5px solid #27ae60;
}

.metric-card.success {
    border-left: 5px solid #2ecc71;
}

.metric-title {
    font-size: 1.1em;
    font-weight: 600;
    margin-bottom: 15px;
    display: flex;
    align-items: center;
    gap: 10px;
}

.metric-value {
    font-size: 3em;
    font-weight: bold;
    margin-bottom: 15px;
}

.metric-card.critical .metric-value {
    color: #e74c3c;
}

.metric-card.high .metric-value {
    color: #f39c12;
}

.metric-card.medium .metric-value {
    color: #f1c40f;
}

.metric-card.low .metric-value {
    color: #27ae60;
}

.metric-card.success .metric-value {
    color: #2ecc71;
}

.progress-container {
    margin-top: 15px;
}

.progress-bar {
    width: 100%;
    height: 8px;
    background-color: #ecf0f1;
    border-radius: 4px;
    overflow: hidden;
    position: relative;
}

.progress-fill {
    height: 100%;
    border-radius: 4px;
    transition: width 0.8s ease;
    position: relative;
}

.progress-fill.critical {
    background: linear-gradient(90deg, #e74c3c, #c0392b);
}

.progress-fill.high {
    background: linear-gradient(90deg, #f39c12, #e67e22);
}

.progress-fill.medium {
    background: linear-gradient(90deg, #f1c40f, #f39c12);
}

.progress-fill.low {
    background: linear-gradient(90deg, #27ae60, #2ecc71);
}

.progress-fill.success {
    background: linear-gradient(90deg, #2ecc71, #27ae60);
}

.progress-text {
    font-size: 0.9em;
    color: #7f8c8d;
    margin-top: 5px;
}

.alerts-section {
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(10px);
    border-radius: 15px;
    padding: 25px;
    margin-bottom: 30px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
}

.alerts-title {
    font-size: 1.5em;
    font-weight: 600;
    margin-bottom: 20px;
    color: #2c3e50;
}

.alert-item {
    padding: 15px;
    border-radius: 10px;
    margin-bottom: 15px;
    display: flex;
    align-items: center;
    gap: 15px;
    transition: transform 0.2s ease;
}

.alert-item:hover {
    transform: translateX(5px);
}

.alert-item.critical {
    background: linear-gradient(135deg, #e74c3c, #c0392b);
    color: white;
}

.alert-item.high {
    background: linear-gradient(135deg, #f39c12, #e67e22);
    color: white;
}

.alert-item.medium {
    background: linear-gradient(135deg, #f1c40f, #f39c12);
    color: #333;
}

.alert-item.low {
    background: linear-gradient(135deg, #27ae60, #2ecc71);
    color: white;
}

.alert-item.success {
    background: linear-gradient(135deg, #2ecc71, #27ae60);
    color: white;
}

.alert-icon {
    font-size: 1.5em;
}

.alert-content {
    flex: 1;
}

.alert-title {
    font-weight: 600;
    margin-bottom: 5px;
}

.alert-description {
    font-size: 0.9em;
    opacity: 0.9;
}

.status-indicator {
    position: absolute;
    top: 20px;
    right: 20px;
    width: 12px;
    height: 12px;
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

.status-indicator.success {
    background-color: #2ecc71;
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

.footer {
    text-align: center;
    color: rgba(255, 255, 255, 0.8);
    margin-top: 30px;
}

.auto-refresh {
    position: fixed;
    top: 20px;
    right: 20px;
    background: rgba(52, 152, 219, 0.9);
    color: white;
    padding: 10px 15px;
    border-radius: 25px;
    font-size: 0.9em;
    backdrop-filter: blur(10px);
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
}

@media (max-width: 768px) {
    .dashboard-container {
        padding: 10px;
    }
    
    .header h1 {
        font-size: 2em;
    }
    
    .metrics-grid {
        grid-template-columns: 1fr;
    }
    
    .metric-value {
        font-size: 2.5em;
    }
}
EOF
}

# Función para generar JavaScript del dashboard
generate_dashboard_js() {
    cat > "$JS_FILE" << 'EOF'
// Dashboard de Monitoreo Visual - Scripts
document.addEventListener('DOMContentLoaded', function() {
    // Auto-refresh cada 30 segundos
    let refreshInterval = 30000;
    let timeLeft = refreshInterval / 1000;
    
    function updateRefreshTimer() {
        const timerElement = document.querySelector('.auto-refresh');
        if (timerElement) {
            timerElement.textContent = `🔄 Auto-refresh en ${timeLeft}s`;
        }
        timeLeft--;
        
        if (timeLeft <= 0) {
            location.reload();
        }
    }
    
    setInterval(updateRefreshTimer, 1000);
    
    // Animaciones de entrada
    const cards = document.querySelectorAll('.metric-card');
    cards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            card.style.transition = 'opacity 0.6s ease, transform 0.6s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
        }, index * 100);
    });
    
    // Efectos de hover mejorados
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-8px) scale(1.02)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0) scale(1)';
        });
    });
    
    // Actualización de barras de progreso
    function animateProgressBars() {
        const progressBars = document.querySelectorAll('.progress-fill');
        progressBars.forEach(bar => {
            const width = bar.style.width;
            bar.style.width = '0%';
            setTimeout(() => {
                bar.style.width = width;
            }, 100);
        });
    }
    
    // Ejecutar animaciones después de un breve delay
    setTimeout(animateProgressBars, 500);
    
    // Notificaciones de estado
    function showStatusNotification() {
        const criticalCount = document.querySelector('.metric-card.critical .metric-value')?.textContent || '0';
        const highCount = document.querySelector('.metric-card.high .metric-value')?.textContent || '0';
        
        if (parseInt(criticalCount) > 0) {
            showNotification('🚨 ALERTA CRÍTICA', 'Se detectaron problemas críticos que requieren atención inmediata', 'critical');
        } else if (parseInt(highCount) > 0) {
            showNotification('🔴 ALERTA ALTA', 'Se detectaron problemas altos que requieren atención', 'high');
        } else {
            showNotification('✅ SISTEMA ESTABLE', 'No se detectaron problemas críticos', 'success');
        }
    }
    
    function showNotification(title, message, type) {
        // Crear elemento de notificación
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <h3>${title}</h3>
                <p>${message}</p>
            </div>
        `;
        
        // Estilos de notificación
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: ${type === 'critical' ? '#e74c3c' : type === 'high' ? '#f39c12' : '#2ecc71'};
            color: white;
            padding: 15px 25px;
            border-radius: 10px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
            z-index: 1000;
            animation: slideDown 0.5s ease;
        `;
        
        document.body.appendChild(notification);
        
        // Remover después de 5 segundos
        setTimeout(() => {
            notification.style.animation = 'slideUp 0.5s ease';
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 500);
        }, 5000);
    }
    
    // Mostrar notificación inicial
    setTimeout(showStatusNotification, 1000);
    
    // Agregar estilos de animación
    const style = document.createElement('style');
    style.textContent = `
        @keyframes slideDown {
            from {
                transform: translateX(-50%) translateY(-100%);
                opacity: 0;
            }
            to {
                transform: translateX(-50%) translateY(0);
                opacity: 1;
            }
        }
        
        @keyframes slideUp {
            from {
                transform: translateX(-50%) translateY(0);
                opacity: 1;
            }
            to {
                transform: translateX(-50%) translateY(-100%);
                opacity: 0;
            }
        }
    `;
    document.head.appendChild(style);
});
EOF
}

# Función para generar dashboard HTML
generate_dashboard_html() {
    local critical=$1
    local high=$2
    local medium=$3
    local low=$4
    local total=$((critical + high + medium + low))
    
    cat > "$DASHBOARD_FILE" << EOF
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard de Monitoreo Visual - Backend</title>
    <link rel="stylesheet" href="$CSS_FILE">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
</head>
<body>
    <div class="auto-refresh">🔄 Auto-refresh en 30s</div>
    
    <div class="dashboard-container">
        <div class="header">
            <h1>📊 Dashboard de Monitoreo Visual</h1>
            <p class="subtitle">Sistema de Gestión de Problemas Backend</p>
            <p>Última actualización: $TIMESTAMP</p>
        </div>
        
        <div class="metrics-grid">
            <div class="metric-card critical">
                <div class="status-indicator critical"></div>
                <div class="metric-title">
                    <i class="fas fa-exclamation-triangle"></i>
                    Problemas Críticos
                </div>
                <div class="metric-value">$critical</div>
                <div class="progress-container">
                    <div class="progress-bar">
                        <div class="progress-fill critical" style="width: $(echo "scale=1; $critical * 100 / $(($total + 1))" | bc)%"></div>
                    </div>
                    <div class="progress-text">$(echo "scale=1; $critical * 100 / $(($total + 1))" | bc)% del total</div>
                </div>
            </div>
            
            <div class="metric-card high">
                <div class="status-indicator high"></div>
                <div class="metric-title">
                    <i class="fas fa-exclamation-circle"></i>
                    Problemas Altos
                </div>
                <div class="metric-value">$high</div>
                <div class="progress-container">
                    <div class="progress-bar">
                        <div class="progress-fill high" style="width: $(echo "scale=1; $high * 100 / $(($total + 1))" | bc)%"></div>
                    </div>
                    <div class="progress-text">$(echo "scale=1; $high * 100 / $(($total + 1))" | bc)% del total</div>
                </div>
            </div>
            
            <div class="metric-card medium">
                <div class="status-indicator medium"></div>
                <div class="metric-title">
                    <i class="fas fa-exclamation"></i>
                    Problemas Medios
                </div>
                <div class="metric-value">$medium</div>
                <div class="progress-container">
                    <div class="progress-bar">
                        <div class="progress-fill medium" style="width: $(echo "scale=1; $medium * 100 / $(($total + 1))" | bc)%"></div>
                    </div>
                    <div class="progress-text">$(echo "scale=1; $medium * 100 / $(($total + 1))" | bc)% del total</div>
                </div>
            </div>
            
            <div class="metric-card low">
                <div class="status-indicator low"></div>
                <div class="metric-title">
                    <i class="fas fa-info-circle"></i>
                    Problemas Bajos
                </div>
                <div class="metric-value">$low</div>
                <div class="progress-container">
                    <div class="progress-bar">
                        <div class="progress-fill low" style="width: $(echo "scale=1; $low * 100 / $(($total + 1))" | bc)%"></div>
                    </div>
                    <div class="progress-text">$(echo "scale=1; $low * 100 / $(($total + 1))" | bc)% del total</div>
                </div>
            </div>
            
            <div class="metric-card success">
                <div class="status-indicator success"></div>
                <div class="metric-title">
                    <i class="fas fa-check-circle"></i>
                    Estado General
                </div>
                <div class="metric-value">$(if [ $critical -eq 0 ] && [ $high -eq 0 ]; then echo "✅"; else echo "⚠️"; fi)</div>
                <div class="progress-container">
                    <div class="progress-bar">
                        <div class="progress-fill success" style="width: $(echo "scale=1; ($total - $critical - $high) * 100 / $(($total + 1))" | bc)%"></div>
                    </div>
                    <div class="progress-text">$(echo "scale=1; ($total - $critical - $high) * 100 / $(($total + 1))" | bc)% estable</div>
                </div>
            </div>
        </div>
        
        <div class="alerts-section">
            <h2 class="alerts-title">🚨 Sistema de Alertas por Colores</h2>
            
            $(if [ $critical -gt 0 ]; then
                echo '<div class="alert-item critical">
                    <div class="alert-icon">🚨</div>
                    <div class="alert-content">
                        <div class="alert-title">ALERTA CRÍTICA</div>
                        <div class="alert-description">'$critical' problemas críticos detectados - Intervención inmediata requerida</div>
                    </div>
                </div>'
            fi)
            
            $(if [ $high -gt 0 ]; then
                echo '<div class="alert-item high">
                    <div class="alert-icon">🔴</div>
                    <div class="alert-content">
                        <div class="alert-title">ALERTA ALTA</div>
                        <div class="alert-description">'$high' problemas altos detectados - Intervención en 24h requerida</div>
                    </div>
                </div>'
            fi)
            
            $(if [ $medium -gt 0 ]; then
                echo '<div class="alert-item medium">
                    <div class="alert-icon">🟡</div>
                    <div class="alert-content">
                        <div class="alert-title">ALERTA MEDIA</div>
                        <div class="alert-description">'$medium' problemas medios detectados - Planificar corrección</div>
                    </div>
                </div>'
            fi)
            
            $(if [ $low -gt 0 ]; then
                echo '<div class="alert-item low">
                    <div class="alert-icon">🟢</div>
                    <div class="alert-content">
                        <div class="alert-title">ALERTA BAJA</div>
                        <div class="alert-description">'$low' problemas bajos detectados - Mejoras opcionales</div>
                    </div>
                </div>'
            fi)
            
            $(if [ $critical -eq 0 ] && [ $high -eq 0 ] && [ $medium -eq 0 ] && [ $low -eq 0 ]; then
                echo '<div class="alert-item success">
                    <div class="alert-icon">✅</div>
                    <div class="alert-content">
                        <div class="alert-title">SISTEMA ÓPTIMO</div>
                        <div class="alert-description">No se detectaron problemas - Sistema cumple normativas</div>
                    </div>
                </div>'
            fi)
        </div>
        
        <div class="footer">
            <p>🎯 Sistema de Monitoreo por Colores - Cumple con normativas ITIL e ISO 20000</p>
            <p>📊 Generado automáticamente el $TIMESTAMP</p>
        </div>
    </div>
    
    <script src="$JS_FILE"></script>
</body>
</html>
EOF
}

# Función principal para generar dashboard visual
generate_visual_dashboard() {
    local critical=$1
    local high=$2
    local medium=$3
    local low=$4
    
    echo -e "${WHITE}🎨 GENERANDO DASHBOARD DE MONITOREO VISUAL${NC}"
    echo -e "${WHITE}===========================================${NC}"
    echo ""
    
    # Generar archivos CSS y JS
    generate_dashboard_css
    generate_dashboard_js
    
    # Generar dashboard HTML
    generate_dashboard_html "$critical" "$high" "$medium" "$low"
    
    echo -e "${CYAN}✅ Dashboard visual generado exitosamente${NC}"
    echo -e "${BLUE}📁 Archivos generados:${NC}"
    echo -e "${BLUE}   - $DASHBOARD_FILE${NC}"
    echo -e "${BLUE}   - $CSS_FILE${NC}"
    echo -e "${BLUE}   - $JS_FILE${NC}"
    echo ""
    echo -e "${GREEN}🌐 Abrir dashboard: file://$(pwd)/$DASHBOARD_FILE${NC}"
    echo ""
    
    # Mostrar resumen de colores
    echo -e "${WHITE}🎨 CÓDIGOS DE COLOR IMPLEMENTADOS:${NC}"
    echo -e "${RED}🚨 CRÍTICO: #e74c3c (Rojo)${NC}"
    echo -e "${ORANGE}🔴 ALTO: #f39c12 (Naranja)${NC}"
    echo -e "${YELLOW}🟡 MEDIO: #f1c40f (Amarillo)${NC}"
    echo -e "${GREEN}🟢 BAJO: #27ae60 (Verde)${NC}"
    echo -e "${CYAN}✅ ÉXITO: #2ecc71 (Verde claro)${NC}"
    echo ""
}

# Exportar funciones para uso en otros scripts
export -f generate_dashboard_css
export -f generate_dashboard_js
export -f generate_dashboard_html
export -f generate_visual_dashboard

# Si se ejecuta directamente, mostrar ayuda
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    echo -e "${WHITE}🎨 DASHBOARD DE MONITOREO VISUAL${NC}"
    echo -e "${WHITE}=================================${NC}"
    echo ""
    echo -e "${BLUE}Uso: source visual_dashboard.sh${NC}"
    echo -e "${BLUE}Luego: generate_visual_dashboard <critical> <high> <medium> <low>${NC}"
    echo ""
    echo -e "${GREEN}Ejemplo:${NC}"
    echo -e "${GREEN}  generate_visual_dashboard 2 1 3 0${NC}"
    echo ""
    echo -e "${YELLOW}Características:${NC}"
    echo -e "${YELLOW}  ✅ Monitoreo por colores${NC}"
    echo -e "${YELLOW}  ✅ Auto-refresh cada 30s${NC}"
    echo -e "${YELLOW}  ✅ Animaciones suaves${NC}"
    echo -e "${YELLOW}  ✅ Responsive design${NC}"
    echo -e "${YELLOW}  ✅ Notificaciones de estado${NC}"
    echo ""
fi
