# backend/scripts/monitoreo_continuo_despliegue.py
"""
CUARTO ENFOQUE: MONITOREO CONTINUO DEL DESPLIEGUE
Monitorear en tiempo real el estado del despliegue y verificar cuando esté listo
"""
import os
import sys
import logging
import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MonitorDespliegue:
    def __init__(self):
        self.backend_url = "https://pagos-f2qf.onrender.com"
        self.frontend_url = "https://rapicredit.onrender.com"
        self.credentials = {
            "email": "itmaster@rapicreditca.com",
            "password": "R@pi_2025**",
            "remember": True
        }
        self.max_intentos = 20  # Máximo 20 intentos (10 minutos)
        self.intervalo = 30  # 30 segundos entre intentos
        
    def verificar_servidor(self) -> Tuple[bool, str]:
        """Verificar si el servidor responde"""
        try:
            response = requests.get(f"{self.backend_url}/", timeout=10)
            if response.status_code in [200, 404, 405]:
                return True, f"Servidor activo (Status: {response.status_code})"
            else:
                return False, f"Servidor inactivo (Status: {response.status_code})"
        except Exception as e:
            return False, f"Error conectando: {str(e)}"
    
    def verificar_login(self) -> Tuple[bool, str, str]:
        """Verificar si el login funciona"""
        try:
            response = requests.post(
                f"{self.backend_url}/api/v1/auth/login",
                json=self.credentials,
                headers={'Content-Type': 'application/json'},
                timeout=15
            )
            
            if response.status_code == 200:
                login_data = response.json()
                access_token = login_data.get('access_token')
                user_data = login_data.get('user', {})
                
                if access_token and user_data.get('is_admin'):
                    return True, "Login exitoso", access_token
                else:
                    return False, "Login falló - datos incompletos", ""
            else:
                return False, f"Login falló (Status: {response.status_code})", ""
                
        except Exception as e:
            return False, f"Error en login: {str(e)}", ""
    
    def verificar_analistas(self, access_token: str) -> Tuple[bool, str]:
        """Verificar si el endpoint analistas funciona"""
        try:
            headers = {
                'Authorization': f'Bearer {access_token}',
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
            
            response = requests.get(
                f"{self.backend_url}/api/v1/analistas",
                headers=headers,
                params={'limit': 100},
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                total = data.get('total', 0)
                return True, f"Analistas funcionando ({total} items)"
            elif response.status_code == 405:
                return False, "Error 405 Method Not Allowed - Correcciones no aplicadas"
            else:
                return False, f"Error {response.status_code}: {response.text[:100]}"
                
        except Exception as e:
            return False, f"Error verificando analistas: {str(e)}"
    
    def verificar_frontend(self) -> Tuple[bool, str]:
        """Verificar si el frontend responde"""
        try:
            response = requests.get(f"{self.frontend_url}/", timeout=10)
            if response.status_code == 200:
                return True, "Frontend activo"
            else:
                return False, f"Frontend inactivo (Status: {response.status_code})"
        except Exception as e:
            return False, f"Error conectando frontend: {str(e)}"
    
    def verificar_endpoints_criticos(self, access_token: str) -> Dict[str, Tuple[bool, str]]:
        """Verificar endpoints críticos"""
        endpoints = {
            "usuarios": "/api/v1/users",
            "concesionarios": "/api/v1/concesionarios", 
            "modelos_vehiculos": "/api/v1/modelos-vehiculos"
        }
        
        results = {}
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        for name, endpoint in endpoints.items():
            try:
                response = requests.get(
                    f"{self.backend_url}{endpoint}",
                    headers=headers,
                    params={'limit': 10},
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    total = data.get('total', 0)
                    results[name] = (True, f"{total} items")
                else:
                    results[name] = (False, f"Status {response.status_code}")
                    
            except Exception as e:
                results[name] = (False, f"Error: {str(e)}")
        
        return results
    
    def monitoreo_continuo(self):
        """Monitoreo continuo del despliegue"""
        logger.info("🔄 CUARTO ENFOQUE: MONITOREO CONTINUO DEL DESPLIEGUE")
        logger.info("=" * 80)
        logger.info(f"📅 Fecha y hora: {datetime.now()}")
        logger.info("🎯 Objetivo: Monitorear en tiempo real hasta que el despliegue esté completo")
        logger.info(f"⏰ Intervalo: {self.intervalo} segundos")
        logger.info(f"🔄 Máximo intentos: {self.max_intentos}")
        logger.info("=" * 80)
        
        intento = 0
        despliegue_completo = False
        
        while intento < self.max_intentos and not despliegue_completo:
            intento += 1
            logger.info(f"\n🔄 INTENTO {intento}/{self.max_intentos}")
            logger.info("-" * 50)
            
            # 1. Verificar servidor
            servidor_ok, servidor_msg = self.verificar_servidor()
            logger.info(f"🌐 Servidor: {'✅' if servidor_ok else '❌'} {servidor_msg}")
            
            if not servidor_ok:
                logger.info("⏰ Servidor no disponible, esperando...")
                time.sleep(self.intervalo)
                continue
            
            # 2. Verificar login
            login_ok, login_msg, access_token = self.verificar_login()
            logger.info(f"🔐 Login: {'✅' if login_ok else '❌'} {login_msg}")
            
            if not login_ok:
                logger.info("⏰ Login no disponible, esperando...")
                time.sleep(self.intervalo)
                continue
            
            # 3. Verificar analistas (CRÍTICO)
            analistas_ok, analistas_msg = self.verificar_analistas(access_token)
            logger.info(f"🔍 Analistas: {'✅' if analistas_ok else '❌'} {analistas_msg}")
            
            # 4. Verificar frontend
            frontend_ok, frontend_msg = self.verificar_frontend()
            logger.info(f"🌐 Frontend: {'✅' if frontend_ok else '❌'} {frontend_msg}")
            
            # 5. Verificar endpoints críticos
            logger.info("🔍 Endpoints críticos:")
            endpoints_results = self.verificar_endpoints_criticos(access_token)
            for name, (ok, msg) in endpoints_results.items():
                logger.info(f"   {name}: {'✅' if ok else '❌'} {msg}")
            
            # 6. Evaluar estado del despliegue
            endpoints_criticos_ok = all(ok for ok, _ in endpoints_results.values())
            
            if servidor_ok and login_ok and analistas_ok and frontend_ok and endpoints_criticos_ok:
                logger.info("\n🎉 DESPLIEGUE COMPLETO DETECTADO!")
                logger.info("=" * 80)
                logger.info("✅ TODOS LOS COMPONENTES FUNCIONANDO:")
                logger.info("   🌐 Servidor backend activo")
                logger.info("   🔐 Sistema de autenticación funcional")
                logger.info("   🔍 Endpoint analistas funcionando")
                logger.info("   🌐 Frontend activo")
                logger.info("   🔍 Todos los endpoints críticos funcionando")
                logger.info("\n🎯 CONCLUSIÓN: El problema de analistas está RESUELTO")
                logger.info("🎯 El sistema está completamente operativo")
                despliegue_completo = True
                break
            else:
                logger.info(f"\n⏰ Despliegue aún en progreso... Esperando {self.intervalo} segundos")
                time.sleep(self.intervalo)
        
        # Resultado final
        if despliegue_completo:
            logger.info("\n✅ MONITOREO EXITOSO:")
            logger.info("   🎯 El despliegue se completó correctamente")
            logger.info("   🎯 Todas las correcciones fueron aplicadas")
            logger.info("   🎯 El error 405 Method Not Allowed está resuelto")
            logger.info("   🎯 El sistema está listo para uso")
            return True
        else:
            logger.error("\n❌ MONITOREO FALLIDO:")
            logger.error(f"   🔍 Despliegue no completado después de {self.max_intentos} intentos")
            logger.error("   🔍 Se requiere intervención manual")
            logger.error("   🔍 Verificar logs de Render para más detalles")
            return False

def main():
    monitor = MonitorDespliegue()
    return monitor.monitoreo_continuo()

if __name__ == "__main__":
    main()
