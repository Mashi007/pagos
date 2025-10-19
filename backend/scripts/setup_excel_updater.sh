#!/bin/bash
"""
Script de Configuración para Actualizador Automático de Plantilla Excel
======================================================================

Este script configura y ejecuta el actualizador automático de plantilla Excel.
Se puede ejecutar como:
- Servicio del sistema (systemd)
- Cron job
- Proceso en background
- Docker container

Uso:
    ./setup_excel_updater.sh [install|start|stop|status|uninstall]
"""

set -e

# Configuración
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PYTHON_SCRIPT="$SCRIPT_DIR/auto_update_excel_template.py"
SERVICE_NAME="excel-template-updater"
SERVICE_USER="www-data"
LOG_DIR="/var/log/excel-updater"
CACHE_DIR="/var/cache/excel-updater"

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funciones de utilidad
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Verificar dependencias
check_dependencies() {
    log_info "Verificando dependencias..."
    
    # Verificar Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 no está instalado"
        exit 1
    fi
    
    # Verificar pip
    if ! command -v pip3 &> /dev/null; then
        log_error "pip3 no está instalado"
        exit 1
    fi
    
    # Verificar que el script Python existe
    if [ ! -f "$PYTHON_SCRIPT" ]; then
        log_error "Script Python no encontrado: $PYTHON_SCRIPT"
        exit 1
    fi
    
    log_success "Dependencias verificadas"
}

# Instalar dependencias Python
install_python_deps() {
    log_info "Instalando dependencias Python..."
    
    cd "$PROJECT_DIR"
    
    # Instalar dependencias del proyecto
    pip3 install -r requirements.txt
    
    log_success "Dependencias Python instaladas"
}

# Crear directorios necesarios
create_directories() {
    log_info "Creando directorios..."
    
    sudo mkdir -p "$LOG_DIR"
    sudo mkdir -p "$CACHE_DIR"
    sudo chown "$SERVICE_USER:$SERVICE_USER" "$LOG_DIR"
    sudo chown "$SERVICE_USER:$SERVICE_USER" "$CACHE_DIR"
    
    log_success "Directorios creados"
}

# Crear archivo de servicio systemd
create_systemd_service() {
    log_info "Creando servicio systemd..."
    
    cat > "/tmp/$SERVICE_NAME.service" << EOF
[Unit]
Description=Excel Template Auto Updater
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=simple
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$PROJECT_DIR
ExecStart=/usr/bin/python3 $PYTHON_SCRIPT --watch --interval 10
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVICE_NAME

# Variables de entorno
Environment=PYTHONPATH=$PROJECT_DIR
Environment=LOG_LEVEL=INFO

# Límites de recursos
MemoryLimit=512M
CPUQuota=50%

[Install]
WantedBy=multi-user.target
EOF

    sudo mv "/tmp/$SERVICE_NAME.service" "/etc/systemd/system/"
    sudo systemctl daemon-reload
    
    log_success "Servicio systemd creado"
}

# Crear script de cron
create_cron_job() {
    log_info "Creando trabajo cron..."
    
    # Crear script wrapper
    cat > "/tmp/excel_updater_cron.sh" << EOF
#!/bin/bash
# Actualizador de plantilla Excel - Cron Job
# Ejecuta cada 15 minutos

cd "$PROJECT_DIR"
export PYTHONPATH="$PROJECT_DIR"
/usr/bin/python3 "$PYTHON_SCRIPT" --save >> "$LOG_DIR/cron.log" 2>&1
EOF

    sudo mv "/tmp/excel_updater_cron.sh" "/usr/local/bin/"
    sudo chmod +x "/usr/local/bin/excel_updater_cron.sh"
    
    # Agregar a crontab
    (crontab -l 2>/dev/null; echo "*/15 * * * * /usr/local/bin/excel_updater_cron.sh") | crontab -
    
    log_success "Trabajo cron creado (cada 15 minutos)"
}

# Instalar servicio
install_service() {
    log_info "Instalando servicio..."
    
    check_dependencies
    install_python_deps
    create_directories
    create_systemd_service
    create_cron_job
    
    log_success "Servicio instalado exitosamente"
    log_info "Comandos disponibles:"
    log_info "  start:   Iniciar servicio"
    log_info "  stop:    Detener servicio"
    log_info "  status:  Ver estado del servicio"
    log_info "  logs:    Ver logs del servicio"
}

# Iniciar servicio
start_service() {
    log_info "Iniciando servicio..."
    
    sudo systemctl enable "$SERVICE_NAME"
    sudo systemctl start "$SERVICE_NAME"
    
    sleep 2
    
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_success "Servicio iniciado correctamente"
    else
        log_error "Error iniciando servicio"
        sudo systemctl status "$SERVICE_NAME"
        exit 1
    fi
}

# Detener servicio
stop_service() {
    log_info "Deteniendo servicio..."
    
    sudo systemctl stop "$SERVICE_NAME"
    sudo systemctl disable "$SERVICE_NAME"
    
    log_success "Servicio detenido"
}

# Ver estado del servicio
show_status() {
    log_info "Estado del servicio:"
    sudo systemctl status "$SERVICE_NAME" --no-pager
    
    echo ""
    log_info "Logs recientes:"
    sudo journalctl -u "$SERVICE_NAME" --no-pager -n 20
    
    echo ""
    log_info "Archivos generados:"
    if [ -d "$PROJECT_DIR/generated_templates" ]; then
        ls -la "$PROJECT_DIR/generated_templates/"
    else
        log_warning "No hay archivos generados aún"
    fi
}

# Ver logs del servicio
show_logs() {
    log_info "Logs del servicio:"
    sudo journalctl -u "$SERVICE_NAME" --no-pager -f
}

# Desinstalar servicio
uninstall_service() {
    log_info "Desinstalando servicio..."
    
    stop_service
    
    # Remover archivos
    sudo rm -f "/etc/systemd/system/$SERVICE_NAME.service"
    sudo rm -f "/usr/local/bin/excel_updater_cron.sh"
    
    # Remover de crontab
    crontab -l 2>/dev/null | grep -v "excel_updater_cron.sh" | crontab -
    
    # Recargar systemd
    sudo systemctl daemon-reload
    
    log_success "Servicio desinstalado"
}

# Ejecutar actualización manual
run_manual_update() {
    log_info "Ejecutando actualización manual..."
    
    cd "$PROJECT_DIR"
    export PYTHONPATH="$PROJECT_DIR"
    
    python3 "$PYTHON_SCRIPT" --force --save
    
    log_success "Actualización manual completada"
}

# Función principal
main() {
    case "${1:-help}" in
        "install")
            install_service
            ;;
        "start")
            start_service
            ;;
        "stop")
            stop_service
            ;;
        "status")
            show_status
            ;;
        "logs")
            show_logs
            ;;
        "uninstall")
            uninstall_service
            ;;
        "update")
            run_manual_update
            ;;
        "help"|*)
            echo "Uso: $0 [install|start|stop|status|logs|uninstall|update]"
            echo ""
            echo "Comandos:"
            echo "  install   - Instalar el servicio completo"
            echo "  start     - Iniciar el servicio"
            echo "  stop      - Detener el servicio"
            echo "  status    - Ver estado del servicio"
            echo "  logs      - Ver logs en tiempo real"
            echo "  uninstall - Desinstalar el servicio"
            echo "  update    - Ejecutar actualización manual"
            echo ""
            echo "Ejemplos:"
            echo "  $0 install    # Instalar servicio"
            echo "  $0 start      # Iniciar monitoreo automático"
            echo "  $0 update     # Actualización manual inmediata"
            ;;
    esac
}

# Ejecutar función principal
main "$@"
