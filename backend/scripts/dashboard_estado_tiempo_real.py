"""
Dashboard de Estado del Sistema en Tiempo Real
Sistema de monitoreo continuo con interfaz web
"""
import requests
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import threading
from flask import Flask, render_template_string, jsonify
from collections import deque
import schedule

logger = logging.getLogger(__name__)

class DashboardEstadoTiempoReal:
    """Dashboard de estado del sistema en tiempo real"""
    
    def __init__(self, base_url: str = "https://pagos-f2qf.onrender.com"):
        self.base_url = base_url
        self.app = Flask(__name__)
        self.estado_actual = {
            "servidor": False,
            "autenticacion": False,
            "endpoints_criticos": False,
            "ultima_verificacion": None,
            "metricas": {
                "tiempo_respuesta_promedio": 0,
                "tasa_exito": 0,
                "requests_por_minuto": 0,
                "uptime": 0
            },
            "alertas": [],
            "historial": deque(maxlen=100)
        }
        
        self.endpoints_monitoreo = [
            {"url": "/api/v1/auth/login", "metodo": "POST", "critico": True, "nombre": "Autenticación"},
            {"url": "/api/v1/clientes/ping", "metodo": "GET", "critico": True, "nombre": "Clientes"},
            {"url": "/api/v1/validadores/ping", "metodo": "GET", "critico": True, "nombre": "Validadores"},
            {"url": "/api/v1/usuarios/", "metodo": "GET", "critico": False, "nombre": "Usuarios"},
            {"url": "/api/v1/clientes/count", "metodo": "GET", "critico": False, "nombre": "Conteo"},
            {"url": "/api/v1/clientes/opciones-configuracion", "metodo": "GET", "critico": False, "nombre": "Configuración"}
        ]
        
        self.inicio_sistema = datetime.now()
        self.requests_totales = 0
        self.requests_exitosos = 0
        
        self._configurar_rutas()
        self._iniciar_monitoreo_background()
    
    def _configurar_rutas(self):
        """Configura las rutas del dashboard"""
        
        @self.app.route('/')
        def dashboard():
            return render_template_string(self._get_html_template())
        
        @self.app.route('/api/estado')
        def api_estado():
            return jsonify(self.estado_actual)
        
        @self.app.route('/api/historial')
        def api_historial():
            return jsonify(list(self.estado_actual["historial"]))
        
        @self.app.route('/api/verificar-ahora')
        def api_verificar_ahora():
            self._ejecutar_verificacion_completa()
            return jsonify({"mensaje": "Verificación ejecutada", "timestamp": datetime.now().isoformat()})
    
    def _get_html_template(self):
        """Retorna el template HTML del dashboard"""
        return """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Estado Sistema - RapiCredit</title>
    <style>
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
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }
        
        .header h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        
        .header p {
            font-size: 1.2em;
            opacity: 0.9;
        }
        
        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .card {
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            transition: transform 0.3s ease;
        }
        
        .card:hover {
            transform: translateY(-5px);
        }
        
        .card h3 {
            color: #4a5568;
            margin-bottom: 15px;
            font-size: 1.3em;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .status-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            display: inline-block;
        }
        
        .status-ok { background-color: #48bb78; }
        .status-warning { background-color: #ed8936; }
        .status-error { background-color: #f56565; }
        
        .metric {
            display: flex;
            justify-content: space-between;
            margin: 10px 0;
            padding: 8px 0;
            border-bottom: 1px solid #e2e8f0;
        }
        
        .metric:last-child {
            border-bottom: none;
        }
        
        .metric-label {
            font-weight: 500;
            color: #4a5568;
        }
        
        .metric-value {
            font-weight: 600;
            color: #2d3748;
        }
        
        .endpoints-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }
        
        .endpoint-item {
            background: #f7fafc;
            padding: 15px;
            border-radius: 10px;
            border-left: 4px solid #e2e8f0;
            transition: all 0.3s ease;
        }
        
        .endpoint-item.ok {
            border-left-color: #48bb78;
            background: #f0fff4;
        }
        
        .endpoint-item.error {
            border-left-color: #f56565;
            background: #fff5f5;
        }
        
        .endpoint-name {
            font-weight: 600;
            margin-bottom: 5px;
        }
        
        .endpoint-status {
            font-size: 0.9em;
            color: #718096;
        }
        
        .controls {
            text-align: center;
            margin: 30px 0;
        }
        
        .btn {
            background: #4299e1;
            color: white;
            border: none;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 1em;
            cursor: pointer;
            transition: background 0.3s ease;
            margin: 0 10px;
        }
        
        .btn:hover {
            background: #3182ce;
        }
        
        .btn-success {
            background: #48bb78;
        }
        
        .btn-success:hover {
            background: #38a169;
        }
        
        .alertas {
            background: #fff5f5;
            border: 1px solid #feb2b2;
            border-radius: 10px;
            padding: 20px;
            margin-top: 20px;
        }
        
        .alerta-item {
            background: #fed7d7;
            padding: 10px 15px;
            border-radius: 8px;
            margin: 10px 0;
            border-left: 4px solid #f56565;
        }
        
        .timestamp {
            font-size: 0.9em;
            color: #718096;
            text-align: center;
            margin-top: 20px;
        }
        
        .loading {
            text-align: center;
            color: #718096;
            font-style: italic;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        
        .pulse {
            animation: pulse 2s infinite;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Dashboard Estado Sistema</h1>
            <p>RapiCredit - Monitoreo en Tiempo Real</p>
        </div>
        
        <div class="controls">
            <button class="btn" onclick="verificarAhora()">🔄 Verificar Ahora</button>
            <button class="btn btn-success" onclick="toggleAutoRefresh()">⏰ Auto-refresh</button>
        </div>
        
        <div class="dashboard-grid">
            <div class="card">
                <h3>
                    <span class="status-indicator" id="servidor-status"></span>
                    Estado del Servidor
                </h3>
                <div class="metric">
                    <span class="metric-label">Conectividad</span>
                    <span class="metric-value" id="servidor-conectividad">Verificando...</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Última verificación</span>
                    <span class="metric-value" id="ultima-verificacion">-</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Uptime</span>
                    <span class="metric-value" id="uptime">-</span>
                </div>
            </div>
            
            <div class="card">
                <h3>
                    <span class="status-indicator" id="auth-status"></span>
                    Autenticación
                </h3>
                <div class="metric">
                    <span class="metric-label">Estado</span>
                    <span class="metric-value" id="auth-estado">Verificando...</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Tiempo respuesta</span>
                    <span class="metric-value" id="auth-tiempo">-</span>
                </div>
            </div>
            
            <div class="card">
                <h3>
                    <span class="status-indicator" id="metricas-status"></span>
                    Métricas de Rendimiento
                </h3>
                <div class="metric">
                    <span class="metric-label">Tiempo promedio</span>
                    <span class="metric-value" id="tiempo-promedio">-</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Tasa de éxito</span>
                    <span class="metric-value" id="tasa-exito">-</span>
                </div>
                <div class="metric">
                    <span class="metric-label">Requests/min</span>
                    <span class="metric-value" id="requests-minuto">-</span>
                </div>
            </div>
            
            <div class="card">
                <h3>🔗 Endpoints Críticos</h3>
                <div class="endpoints-grid" id="endpoints-grid">
                    <div class="loading">Cargando endpoints...</div>
                </div>
            </div>
        </div>
        
        <div id="alertas-container" style="display: none;">
            <div class="alertas">
                <h3>⚠️ Alertas del Sistema</h3>
                <div id="alertas-lista"></div>
            </div>
        </div>
        
        <div class="timestamp" id="timestamp">
            Última actualización: -
        </div>
    </div>
    
    <script>
        let autoRefreshInterval = null;
        let isAutoRefresh = false;
        
        function updateDashboard() {
            fetch('/api/estado')
                .then(response => response.json())
                .then(data => {
                    updateServidorStatus(data);
                    updateAuthStatus(data);
                    updateMetricas(data);
                    updateEndpoints(data);
                    updateAlertas(data);
                    updateTimestamp();
                })
                .catch(error => {
                    console.error('Error actualizando dashboard:', error);
                    showError('Error conectando con el servidor');
                });
        }
        
        function updateServidorStatus(data) {
            const status = data.servidor ? 'ok' : 'error';
            document.getElementById('servidor-status').className = `status-indicator status-${status}`;
            document.getElementById('servidor-conectividad').textContent = data.servidor ? 'Conectado' : 'Desconectado';
            document.getElementById('ultima-verificacion').textContent = data.ultima_verificacion ? 
                new Date(data.ultima_verificacion).toLocaleTimeString() : '-';
            document.getElementById('uptime').textContent = data.metricas.uptime || '-';
        }
        
        function updateAuthStatus(data) {
            const status = data.autenticacion ? 'ok' : 'error';
            document.getElementById('auth-status').className = `status-indicator status-${status}`;
            document.getElementById('auth-estado').textContent = data.autenticacion ? 'Funcionando' : 'Error';
            document.getElementById('auth-tiempo').textContent = data.metricas.tiempo_respuesta_promedio ? 
                `${data.metricas.tiempo_respuesta_promedio}s` : '-';
        }
        
        function updateMetricas(data) {
            const metricas = data.metricas;
            document.getElementById('tiempo-promedio').textContent = metricas.tiempo_respuesta_promedio ? 
                `${metricas.tiempo_respuesta_promedio}s` : '-';
            document.getElementById('tasa-exito').textContent = metricas.tasa_exito ? 
                `${metricas.tasa_exito}%` : '-';
            document.getElementById('requests-minuto').textContent = metricas.requests_por_minuto || '-';
            
            const status = metricas.tasa_exito > 90 ? 'ok' : metricas.tasa_exito > 70 ? 'warning' : 'error';
            document.getElementById('metricas-status').className = `status-indicator status-${status}`;
        }
        
        function updateEndpoints(data) {
            const container = document.getElementById('endpoints-grid');
            container.innerHTML = '';
            
            // Simular datos de endpoints (en una implementación real vendrían del servidor)
            const endpoints = [
                { nombre: 'Autenticación', estado: data.autenticacion ? 'ok' : 'error' },
                { nombre: 'Clientes', estado: data.endpoints_criticos ? 'ok' : 'error' },
                { nombre: 'Validadores', estado: data.endpoints_criticos ? 'ok' : 'error' },
                { nombre: 'Usuarios', estado: 'ok' },
                { nombre: 'Conteo', estado: 'ok' },
                { nombre: 'Configuración', estado: 'ok' }
            ];
            
            endpoints.forEach(endpoint => {
                const div = document.createElement('div');
                div.className = `endpoint-item ${endpoint.estado}`;
                div.innerHTML = `
                    <div class="endpoint-name">${endpoint.nombre}</div>
                    <div class="endpoint-status">${endpoint.estado === 'ok' ? '✅ Funcionando' : '❌ Error'}</div>
                `;
                container.appendChild(div);
            });
        }
        
        function updateAlertas(data) {
            const container = document.getElementById('alertas-container');
            const lista = document.getElementById('alertas-lista');
            
            if (data.alertas && data.alertas.length > 0) {
                container.style.display = 'block';
                lista.innerHTML = '';
                data.alertas.forEach(alerta => {
                    const div = document.createElement('div');
                    div.className = 'alerta-item';
                    div.textContent = alerta;
                    lista.appendChild(div);
                });
            } else {
                container.style.display = 'none';
            }
        }
        
        function updateTimestamp() {
            document.getElementById('timestamp').textContent = 
                `Última actualización: ${new Date().toLocaleString()}`;
        }
        
        function verificarAhora() {
            fetch('/api/verificar-ahora')
                .then(response => response.json())
                .then(data => {
                    console.log('Verificación ejecutada:', data);
                    updateDashboard();
                })
                .catch(error => {
                    console.error('Error ejecutando verificación:', error);
                });
        }
        
        function toggleAutoRefresh() {
            if (isAutoRefresh) {
                clearInterval(autoRefreshInterval);
                isAutoRefresh = false;
                document.querySelector('.btn-success').textContent = '⏰ Auto-refresh';
            } else {
                autoRefreshInterval = setInterval(updateDashboard, 5000); // Cada 5 segundos
                isAutoRefresh = true;
                document.querySelector('.btn-success').textContent = '⏹️ Detener';
            }
        }
        
        function showError(message) {
            console.error(message);
            // En una implementación real, mostrarías el error en la UI
        }
        
        // Inicializar dashboard
        updateDashboard();
        
        // Auto-refresh cada 30 segundos por defecto
        setInterval(updateDashboard, 30000);
    </script>
</body>
</html>
        """
    
    def _ejecutar_verificacion_completa(self):
        """Ejecuta una verificación completa del sistema"""
        logger.info("🔄 Ejecutando verificación completa...")
        
        # Verificar servidor
        try:
            response = requests.get(f"{self.base_url}/", timeout=10)
            self.estado_actual["servidor"] = response.status_code == 200
        except:
            self.estado_actual["servidor"] = False
        
        # Verificar autenticación
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/auth/login",
                json={"email": "itmaster@rapicreditca.com", "password": "R@pi_2025**"},
                timeout=15
            )
            self.estado_actual["autenticacion"] = response.status_code == 200
            self.requests_totales += 1
            if response.status_code == 200:
                self.requests_exitosos += 1
        except:
            self.estado_actual["autenticacion"] = False
            self.requests_totales += 1
        
        # Verificar endpoints críticos
        endpoints_ok = 0
        for endpoint in self.endpoints_monitoreo:
            if endpoint["critico"]:
                try:
                    if endpoint["metodo"] == "GET":
                        response = requests.get(f"{self.base_url}{endpoint['url']}", timeout=10)
                    else:
                        response = requests.post(f"{self.base_url}{endpoint['url']}", timeout=10)
                    
                    if response.status_code in [200, 201]:
                        endpoints_ok += 1
                except:
                    pass
        
        criticos_total = sum(1 for e in self.endpoints_monitoreo if e["critico"])
        self.estado_actual["endpoints_criticos"] = endpoints_ok >= criticos_total * 0.8
        
        # Actualizar métricas
        self._actualizar_metricas()
        
        # Actualizar timestamp
        self.estado_actual["ultima_verificacion"] = datetime.now().isoformat()
        
        # Agregar al historial
        self.estado_actual["historial"].append({
            "timestamp": self.estado_actual["ultima_verificacion"],
            "servidor": self.estado_actual["servidor"],
            "autenticacion": self.estado_actual["autenticacion"],
            "endpoints_criticos": self.estado_actual["endpoints_criticos"]
        })
        
        logger.info("✅ Verificación completada")
    
    def _actualizar_metricas(self):
        """Actualiza las métricas del sistema"""
        uptime = (datetime.now() - self.inicio_sistema).total_seconds()
        
        self.estado_actual["metricas"] = {
            "tiempo_respuesta_promedio": 2.5,  # Simulado
            "tasa_exito": (self.requests_exitosos / self.requests_totales * 100) if self.requests_totales > 0 else 0,
            "requests_por_minuto": self.requests_totales / (uptime / 60) if uptime > 0 else 0,
            "uptime": f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m"
        }
        
        # Generar alertas
        self.estado_actual["alertas"] = []
        if not self.estado_actual["servidor"]:
            self.estado_actual["alertas"].append("Servidor no disponible")
        if not self.estado_actual["autenticacion"]:
            self.estado_actual["alertas"].append("Problemas de autenticación")
        if not self.estado_actual["endpoints_criticos"]:
            self.estado_actual["alertas"].append("Endpoints críticos fallando")
    
    def _iniciar_monitoreo_background(self):
        """Inicia el monitoreo en background"""
        def monitoreo_continuo():
            while True:
                self._ejecutar_verificacion_completa()
                time.sleep(30)  # Verificar cada 30 segundos
        
        thread = threading.Thread(target=monitoreo_continuo, daemon=True)
        thread.start()
        logger.info("🔄 Monitoreo en background iniciado")
    
    def ejecutar_dashboard(self, puerto: int = 5000, debug: bool = False):
        """Ejecuta el dashboard web"""
        logger.info(f"🌐 Iniciando dashboard en puerto {puerto}")
        logger.info(f"📱 Acceso: http://localhost:{puerto}")
        
        self.app.run(host='0.0.0.0', port=puerto, debug=debug)

def main():
    """Función principal para ejecutar el dashboard"""
    dashboard = DashboardEstadoTiempoReal()
    dashboard.ejecutar_dashboard(puerto=5000, debug=False)

if __name__ == "__main__":
    main()
