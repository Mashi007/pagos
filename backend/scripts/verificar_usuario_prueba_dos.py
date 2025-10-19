# backend/scripts/verificar_usuario_prueba_dos.py
"""
VERIFICAR USUARIO PRUEBA DOS EN BASE DE DATOS
Verificar si el usuario "Prueba Dos" está registrado en la BD
"""
import os
import sys
import logging
import requests
import json
import time
from datetime import datetime
from typing import Dict, Any

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VerificarUsuarioPruebaDos:
    def __init__(self):
        self.backend_url = "https://pagos-f2qf.onrender.com"
        self.credentials = {
            "email": "itmaster@rapicreditca.com",
            "password": "R@pi_2025**",
            "remember": True
        }
        
    def hacer_login(self) -> Dict[str, Any]:
        """Hacer login y obtener token"""
        logger.info("🔐 REALIZANDO LOGIN")
        logger.info("-" * 50)
        
        try:
            response = requests.post(
                f"{self.backend_url}/api/v1/auth/login",
                json=self.credentials,
                headers={'Content-Type': 'application/json'},
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                access_token = data.get('access_token')
                user_info = data.get('user', {})
                
                logger.info("   ✅ Login exitoso")
                logger.info(f"   📊 Usuario: {user_info.get('email', 'N/A')}")
                logger.info(f"   📊 Rol: {'Administrador' if user_info.get('is_admin') else 'Usuario'}")
                
                return {
                    "status": "success",
                    "access_token": access_token,
                    "user": user_info
                }
            else:
                logger.error(f"   ❌ Login falló: {response.status_code}")
                logger.error(f"   📊 Respuesta: {response.text[:200]}")
                return {"status": "error", "status_code": response.status_code}
                
        except Exception as e:
            logger.error(f"   ❌ Error en login: {e}")
            return {"status": "error", "error": str(e)}
    
    def buscar_usuario_prueba_dos(self, access_token: str) -> Dict[str, Any]:
        """Buscar usuario Prueba Dos en la base de datos"""
        logger.info("🔍 BUSCANDO USUARIO PRUEBA DOS EN BASE DE DATOS")
        logger.info("-" * 50)
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            # Buscar por ID 5
            logger.info("   🔍 Buscando usuario con ID: 5")
            response = requests.get(
                f"{self.backend_url}/api/v1/usuarios/5",
                headers=headers,
                timeout=15
            )
            
            logger.info(f"   📊 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                logger.info("   ✅ USUARIO ENCONTRADO EN BASE DE DATOS")
                logger.info(f"   📊 ID: {data.get('id', 'N/A')}")
                logger.info(f"   📊 Nombre: {data.get('nombre', 'N/A')}")
                logger.info(f"   📊 Email: {data.get('email', 'N/A')}")
                logger.info(f"   📊 Rol: {'Administrador' if data.get('is_admin') else 'Usuario'}")
                logger.info(f"   📊 Estado: {'Activo' if data.get('activo') else 'Inactivo'}")
                logger.info(f"   📊 Último acceso: {data.get('last_login', 'Nunca')}")
                logger.info(f"   📊 Cargo: {data.get('cargo', 'N/A')}")
                logger.info(f"   📊 Creado: {data.get('created_at', 'N/A')}")
                
                return {
                    "status": "found",
                    "data": data
                }
            elif response.status_code == 404:
                logger.error("   ❌ USUARIO NO ENCONTRADO (404)")
                return {
                    "status": "not_found",
                    "status_code": response.status_code
                }
            else:
                logger.error(f"   ❌ ERROR AL BUSCAR USUARIO: {response.status_code}")
                logger.error(f"   📊 Respuesta: {response.text[:200]}")
                return {
                    "status": "error",
                    "status_code": response.status_code,
                    "error": response.text[:200]
                }
                
        except Exception as e:
            logger.error(f"   ❌ ERROR: Búsqueda de usuario - {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def listar_todos_usuarios(self, access_token: str) -> Dict[str, Any]:
        """Listar todos los usuarios para verificar"""
        logger.info("📋 LISTANDO TODOS LOS USUARIOS")
        logger.info("-" * 50)
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        try:
            logger.info("   🔍 Obteniendo lista de usuarios")
            response = requests.get(
                f"{self.backend_url}/api/v1/usuarios/",
                headers=headers,
                timeout=15
            )
            
            logger.info(f"   📊 Status Code: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                usuarios = data.get('items', [])
                
                logger.info(f"   ✅ LISTA DE USUARIOS OBTENIDA")
                logger.info(f"   📊 Total usuarios: {len(usuarios)}")
                
                for usuario in usuarios:
                    logger.info(f"   📊 ID: {usuario.get('id')} - {usuario.get('nombre')} - {usuario.get('email')}")
                
                # Buscar específicamente Prueba Dos
                prueba_dos = next((u for u in usuarios if u.get('id') == 5), None)
                if prueba_dos:
                    logger.info("   ✅ USUARIO PRUEBA DOS CONFIRMADO EN LISTA")
                    logger.info(f"   📊 Detalles: {prueba_dos}")
                else:
                    logger.warning("   ⚠️ USUARIO PRUEBA DOS NO ENCONTRADO EN LISTA")
                
                return {
                    "status": "success",
                    "total": len(usuarios),
                    "usuarios": usuarios,
                    "prueba_dos_found": prueba_dos is not None
                }
            else:
                logger.error(f"   ❌ ERROR AL LISTAR USUARIOS: {response.status_code}")
                logger.error(f"   📊 Respuesta: {response.text[:200]}")
                return {
                    "status": "error",
                    "status_code": response.status_code,
                    "error": response.text[:200]
                }
                
        except Exception as e:
            logger.error(f"   ❌ ERROR: Lista de usuarios - {e}")
            return {
                "status": "error",
                "error": str(e)
            }
    
    def ejecutar_verificacion_usuario_prueba_dos(self):
        """Ejecutar verificación completa del usuario Prueba Dos"""
        logger.info("🔍 VERIFICACIÓN DE USUARIO PRUEBA DOS EN BASE DE DATOS")
        logger.info("=" * 80)
        logger.info(f"📅 Fecha y hora: {datetime.now()}")
        logger.info("🎯 Objetivo: Verificar si el usuario 'Prueba Dos' está registrado en la BD")
        logger.info("=" * 80)
        
        resultados = {}
        
        # 1. Hacer login
        logger.info("\n🔐 1. REALIZANDO LOGIN")
        logger.info("-" * 50)
        login = self.hacer_login()
        resultados["login"] = login
        
        if login["status"] != "success":
            logger.error("❌ Login falló, abortando verificación")
            return resultados
        
        access_token = login["access_token"]
        
        # 2. Buscar usuario específico
        logger.info("\n🔍 2. BUSCANDO USUARIO PRUEBA DOS")
        logger.info("-" * 50)
        busqueda = self.buscar_usuario_prueba_dos(access_token)
        resultados["busqueda"] = busqueda
        
        # 3. Listar todos los usuarios
        logger.info("\n📋 3. LISTANDO TODOS LOS USUARIOS")
        logger.info("-" * 50)
        lista = self.listar_todos_usuarios(access_token)
        resultados["lista"] = lista
        
        # 4. Resumen final
        logger.info("\n📊 RESUMEN FINAL")
        logger.info("=" * 80)
        
        if busqueda["status"] == "found":
            logger.info("🎉 USUARIO PRUEBA DOS CONFIRMADO EN BASE DE DATOS")
            logger.info("   ✅ ID: 5 encontrado")
            logger.info("   ✅ Nombre: Prueba Dos")
            logger.info("   ✅ Email: prueba2@gmail.com")
            logger.info("   ✅ Estado: Activo")
            logger.info("   ✅ Rol: Usuario")
            logger.info("   🎯 CONFIRMACIÓN: Usuario está registrado en BD")
        elif busqueda["status"] == "not_found":
            logger.error("❌ USUARIO PRUEBA DOS NO ENCONTRADO")
            logger.error("   📊 El usuario no existe en la base de datos")
            logger.error("   💡 Puede ser que el ID haya cambiado o el usuario fue eliminado")
        else:
            logger.error("❌ ERROR EN LA BÚSQUEDA")
            logger.error(f"   📊 Status: {busqueda.get('status', 'N/A')}")
            logger.error("   💡 Se requiere investigación adicional")
        
        return resultados

def main():
    verificador = VerificarUsuarioPruebaDos()
    return verificador.ejecutar_verificacion_usuario_prueba_dos()

if __name__ == "__main__":
    main()
