# backend/scripts/verificar_autenticacion_frontend_analistas.py
"""
VERIFICAR AUTENTICACIÓN EN FRONTEND PARA ANALISTAS
Verificar que el frontend esté enviando la autenticación correctamente
"""
import logging
import requests
import json
from typing import Dict, Any

# Constantes de configuración
REQUEST_TIMEOUT = 15
SEPARATOR_LENGTH = 50

# Configurar logging
logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


class VerificarAutenticacionFrontendAnalistas:

    def __init__(self):
        self.frontend_url = "https://rapicredit.onrender.com"
        self.backend_url = "https://rapicredit.onrender.com"
        self.credentials = {
            "email": "itmaster@rapicreditca.com",
            "password": "admin123"
        }

    def hacer_login(self) -> Dict[str, Any]:
        """Hacer login y obtener token"""
        logger.info("REALIZANDO LOGIN")
        logger.info("-" * SEPARATOR_LENGTH)
        try:
            response = requests.post(
                f"{self.backend_url}/api/v1/auth/login",
                json=self.credentials,
                headers={"Content-Type": "application/json"},
                timeout=REQUEST_TIMEOUT
            )
            if response.status_code == 200:
                data = response.json()
                access_token = data.get("access_token")
                user_info = data.get("user", {})
                logger.info(f"   📊 Usuario: {user_info.get('email', 'N/A')}")
                logger.info(
                    f"   📊 Rol: {'Administrador' if user_info.get('is_admin') else 'Usuario'}"
                )
                return {"status": "success", "access_token": access_token, "user": user_info}
            else:
                logger.error(f"   ❌ Login falló: {response.status_code}")
                logger.error(f"   📊 Respuesta: {response.text[:200]}")
                return {"status": "error", "status_code": response.status_code}

        except Exception as e:
            logger.error(f"   ❌ Error en login: {e}")
            return {"status": "error", "error": str(e)}

    def probar_endpoint_principal_con_auth(self, access_token: str) -> Dict[str, Any]:
        """Probar endpoint principal analistas con autenticación"""
        logger.info("🔍 PROBANDO ENDPOINT PRINCIPAL CON AUTENTICACIÓN")
        logger.info("-" * 50)
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        try:
            logger.info("   🔍 Probando: /api/v1/analistas/")
            response = requests.get(
                f"{self.backend_url}/api/v1/analistas/",
                headers=headers,
                timeout=REQUEST_TIMEOUT
            )
            logger.info(f"   📊 Status Code: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                logger.info("   ✅ ÉXITO: Endpoint principal funciona con autenticación")
                logger.info(f"   📊 Total analistas: {data.get('total', 0)}")
                logger.info(f"   📊 Items: {len(data.get('items', []))}")
                if data.get("items"):
                    primer_analista = data["items"][0]
                    logger.info(
                        f"   📊 Primer analista: {primer_analista.get('nombre', 'N/A')}"
                    )
                return {"status": "success", "data": data}
            else:
                logger.error("   ❌ FALLO: Endpoint principal")
                logger.error(f"   📊 Respuesta: {response.text[:200]}")
                return {"status": "error", "status_code": response.status_code}

        except Exception as e:
            logger.error(f"   ❌ ERROR: Endpoint principal - {e}")
            return {"status": "error", "error": str(e)}

    def probar_endpoint_sin_auth(self) -> Dict[str, Any]:
        """Probar endpoint principal analistas sin autenticación"""
        logger.info("🔍 PROBANDO ENDPOINT PRINCIPAL SIN AUTENTICACIÓN")
        logger.info("-" * 50)
        try:
            logger.info("   🔍 Probando: /api/v1/analistas/ (sin auth)")
            response = requests.get(
                f"{self.backend_url}/api/v1/analistas/",
                timeout=REQUEST_TIMEOUT
            )
            logger.info(f"   📊 Status Code: {response.status_code}")
            if response.status_code == 403:
                logger.info("   ✅ ESPERADO: Endpoint requiere autenticación (403)")
                logger.info(f"   📊 Respuesta: {response.text[:200]}")
                return {"status": "expected", "status_code": 403}
            elif response.status_code == 200:
                logger.error("   ❌ INESPERADO: Endpoint funciona sin autenticación")
                logger.error(f"   📊 Respuesta: {response.text[:200]}")
                return {"status": "unexpected", "status_code": 200}
            else:
                logger.error("   ❌ FALLO: Status inesperado")
                logger.error(f"   📊 Respuesta: {response.text[:200]}")
                return {"status": "error", "status_code": response.status_code}

        except Exception as e:
            logger.error(f"   ❌ ERROR: Endpoint sin auth - {e}")
            return {"status": "error", "error": str(e)}

    def verificar_frontend_url(self) -> Dict[str, Any]:
        """Verificar que el frontend esté disponible"""
        logger.info("🌐 VERIFICANDO FRONTEND")
        logger.info("-" * 50)
        try:
            logger.info("   🔍 Probando: Frontend URL")
            response = requests.get(self.frontend_url, timeout=REQUEST_TIMEOUT)
            logger.info(f"   📊 Status Code: {response.status_code}")
            if response.status_code == 200:
                logger.info("   ✅ Frontend disponible")
                return {"status": "success", "status_code": response.status_code}
            else:
                logger.error(f"   ❌ Frontend no disponible: {response.status_code}")
                return {"status": "error", "status_code": response.status_code}

        except Exception as e:
            logger.error(f"   ❌ Error verificando frontend: {e}")
            return {"status": "error", "error": str(e)}

    def ejecutar_verificacion_autenticacion_frontend(self):
        """Ejecutar verificación completa de autenticación frontend"""
        logger.info("🔍 VERIFICACIÓN DE AUTENTICACIÓN EN FRONTEND PARA ANALISTAS")
        logger.info("=" * 80)
        logger.info("")

        logger.info("=" * 80)
        # 1. Verificar frontend
        logger.info("\n🌐 1. VERIFICANDO FRONTEND")
        logger.info("-" * 50)
        frontend = self.verificar_frontend_url()
        # 2. Probar endpoint sin autenticación
        logger.info("\n🔍 2. PROBANDO ENDPOINT SIN AUTENTICACIÓN")
        logger.info("-" * 50)
        sin_auth = self.probar_endpoint_sin_auth()
        # 3. Hacer login
        logger.info("\n🔐 3. REALIZANDO LOGIN")
        logger.info("-" * 50)
        login = self.hacer_login()
        if login["status"] != "success":
            logger.error("❌ Login falló, abortando verificación")
            return
        access_token = login["access_token"]

        # 4. Probar endpoint con autenticación
        logger.info("\n🔍 4. PROBANDO ENDPOINT CON AUTENTICACIÓN")
        logger.info("-" * 50)
        con_auth = self.probar_endpoint_principal_con_auth(access_token)
        # 5. Resumen final
        logger.info("\n📊 RESUMEN FINAL")
        logger.info("=" * 80)
        if sin_auth["status"] == "expected" and con_auth["status"] == "success":
            logger.info("🎉 AUTENTICACIÓN FUNCIONANDO CORRECTAMENTE")
            logger.info("   ✅ Endpoint requiere autenticación (403 sin auth)")
            logger.info("   ✅ Endpoint funciona con autenticación (200 con auth)")
            logger.info("")
            logger.info("")
        elif sin_auth["status"] == "unexpected":
            logger.error("❌ PROBLEMA DE SEGURIDAD")
            logger.error("   📊 Endpoint funciona sin autenticación (no debería)")
            logger.error("   💡 SOLUCIÓN: Revisar configuración de autenticación")
        else:
            logger.error("❌ PROBLEMA CONFIRMADO")
            logger.error(f"   📊 Sin auth: {sin_auth.get('status', 'N/A')}")
            logger.error(f"   📊 Con auth: {con_auth.get('status', 'N/A')}")
            logger.error("   💡 Se requiere investigación adicional")


def main():
    verificador = VerificarAutenticacionFrontendAnalistas()
    return verificador.ejecutar_verificacion_autenticacion_frontend()


if __name__ == "__main__":
    main()
