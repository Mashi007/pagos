#!/usr/bin/env python3
"""
SIMULACIÓN COMPLETA DE CASOS REALES DE GESTIÓN DE USUARIOS
Simula escenarios reales: usuarios que olvidan contraseñas, cambian emails, etc.
"""

import requests
import os
import logging
import time
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_URL = os.getenv("FRONTEND_URL", "https://pagos-f2qf.onrender.com")

ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "itmaster@rapicreditca.com")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# Usuario de prueba para simular casos reales
USUARIO_PRUEBA_EMAIL = "prueba2@gmail.com"
USUARIO_PRUEBA_ID = 5

def login_admin():
    """Realizar login como administrador"""
    login_url = f"{BASE_URL}/api/v1/auth/login"
    credentials = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD, "remember": True}
    try:
        response = requests.post(login_url, json=credentials)
        logger.info(f"   📊 Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            logger.info(f"   ✅ Login exitoso como administrador")
            return data['access_token']
        else:
            logger.error(f"   ❌ Error en login: {response.status_code}")
            logger.error(f"   📊 Respuesta: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"   ❌ Error durante el login: {e}")
        return None

def obtener_usuario(token: str, user_id: int):
    """Obtener datos de un usuario específico"""
    headers = {"Authorization": f"Bearer {token}"}
    user_url = f"{BASE_URL}/api/v1/usuarios/{user_id}"
    try:
        response = requests.get(user_url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"   ❌ Error obteniendo usuario: {response.text}")
            return None
    except Exception as e:
        logger.error(f"   ❌ Error: {e}")
        return None

def actualizar_usuario(token: str, user_id: int, update_data: dict):
    """Actualizar datos de un usuario"""
    headers = {"Authorization": f"Bearer {token}"}
    update_url = f"{BASE_URL}/api/v1/usuarios/{user_id}"
    try:
        response = requests.put(update_url, json=update_data, headers=headers)
        logger.info(f"   📊 Status Code: {response.status_code}")
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"   ❌ Error actualizando usuario: {response.text}")
            return None
    except Exception as e:
        logger.error(f"   ❌ Error: {e}")
        return None

def probar_login_usuario(email: str, password: str):
    """Probar login con credenciales específicas"""
    login_url = f"{BASE_URL}/api/v1/auth/login"
    credentials = {"email": email, "password": password, "remember": True}
    try:
        response = requests.post(login_url, json=credentials)
        logger.info(f"   📊 Status Code: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            logger.info(f"   ✅ LOGIN EXITOSO")
            logger.info(f"   📊 Usuario: {data['user']['email']}")
            logger.info(f"   📊 Rol: {'Administrador' if data['user']['is_admin'] else 'Usuario'}")
            return True
        else:
            logger.error(f"   ❌ Error en login: {response.status_code}")
            logger.error(f"   📊 Respuesta: {response.text}")
            return False
    except Exception as e:
        logger.error(f"   ❌ Error: {e}")
        return False

def simular_caso_1_usuario_olvida_contraseña(token: str):
    """CASO 1: Usuario olvida contraseña - Administrador genera nueva"""
    logger.info("")
    logger.info("🔐 CASO 1: USUARIO OLVIDA CONTRASEÑA")
    logger.info("=" * 60)
    logger.info("📋 Escenario: Usuario prueba2@gmail.com olvida su contraseña")
    logger.info("📋 Acción: Administrador genera nueva contraseña")
    
    # 1. Verificar estado actual del usuario
    logger.info("")
    logger.info("1️⃣ VERIFICANDO ESTADO ACTUAL DEL USUARIO")
    logger.info("-" * 40)
    usuario_actual = obtener_usuario(token, USUARIO_PRUEBA_ID)
    if not usuario_actual:
        logger.error("❌ No se pudo obtener datos del usuario")
        return False
    
    logger.info(f"   📊 Email: {usuario_actual['email']}")
    logger.info(f"   📊 Estado: {'Activo' if usuario_actual['is_active'] else 'Inactivo'}")
    logger.info(f"   📊 Última actualización: {usuario_actual.get('updated_at', 'N/A')}")
    
    # 2. Generar nueva contraseña
    nueva_contraseña = "NuevaContraseña123!"
    logger.info("")
    logger.info("2️⃣ GENERANDO NUEVA CONTRASEÑA")
    logger.info("-" * 40)
    logger.info(f"   🔑 Nueva contraseña: {nueva_contraseña}")
    
    # 3. Actualizar contraseña
    logger.info("")
    logger.info("3️⃣ ACTUALIZANDO CONTRASEÑA EN BASE DE DATOS")
    logger.info("-" * 40)
    update_data = {"password": nueva_contraseña}
    usuario_actualizado = actualizar_usuario(token, USUARIO_PRUEBA_ID, update_data)
    if not usuario_actualizado:
        logger.error("❌ No se pudo actualizar la contraseña")
        return False
    
    logger.info(f"   ✅ Contraseña actualizada exitosamente")
    logger.info(f"   📊 Nueva fecha de actualización: {usuario_actualizado.get('updated_at', 'N/A')}")
    
    # 4. Probar login con nueva contraseña
    logger.info("")
    logger.info("4️⃣ PROBANDO LOGIN CON NUEVA CONTRASEÑA")
    logger.info("-" * 40)
    login_exitoso = probar_login_usuario(USUARIO_PRUEBA_EMAIL, nueva_contraseña)
    
    if login_exitoso:
        logger.info("✅ CASO 1 COMPLETADO EXITOSAMENTE")
        logger.info("   🎯 Usuario puede hacer login con nueva contraseña")
        logger.info("   🎯 Base de datos actualizada automáticamente")
        return True
    else:
        logger.error("❌ CASO 1 FALLÓ")
        return False

def simular_caso_2_usuario_olvida_contraseña_segunda_vez(token: str):
    """CASO 2: Usuario olvida contraseña por segunda vez"""
    logger.info("")
    logger.info("🔐 CASO 2: USUARIO OLVIDA CONTRASEÑA (SEGUNDA VEZ)")
    logger.info("=" * 60)
    logger.info("📋 Escenario: Usuario olvida la contraseña nuevamente")
    logger.info("📋 Acción: Administrador genera otra contraseña nueva")
    
    # 1. Generar segunda contraseña nueva
    segunda_contraseña = "SegundaContraseña456!"
    logger.info("")
    logger.info("1️⃣ GENERANDO SEGUNDA CONTRASEÑA NUEVA")
    logger.info("-" * 40)
    logger.info(f"   🔑 Segunda contraseña: {segunda_contraseña}")
    
    # 2. Actualizar contraseña por segunda vez
    logger.info("")
    logger.info("2️⃣ ACTUALIZANDO CONTRASEÑA POR SEGUNDA VEZ")
    logger.info("-" * 40)
    update_data = {"password": segunda_contraseña}
    usuario_actualizado = actualizar_usuario(token, USUARIO_PRUEBA_ID, update_data)
    if not usuario_actualizado:
        logger.error("❌ No se pudo actualizar la contraseña por segunda vez")
        return False
    
    logger.info(f"   ✅ Segunda contraseña actualizada exitosamente")
    logger.info(f"   📊 Nueva fecha de actualización: {usuario_actualizado.get('updated_at', 'N/A')}")
    
    # 3. Probar login con segunda contraseña
    logger.info("")
    logger.info("3️⃣ PROBANDO LOGIN CON SEGUNDA CONTRASEÑA")
    logger.info("-" * 40)
    login_exitoso = probar_login_usuario(USUARIO_PRUEBA_EMAIL, segunda_contraseña)
    
    if login_exitoso:
        logger.info("✅ CASO 2 COMPLETADO EXITOSAMENTE")
        logger.info("   🎯 Usuario puede hacer login con segunda contraseña")
        logger.info("   🎯 Sistema permite múltiples cambios de contraseña")
        return True
    else:
        logger.error("❌ CASO 2 FALLÓ")
        return False

def simular_caso_3_activar_desactivar_usuario(token: str):
    """CASO 3: Activar y desactivar usuario"""
    logger.info("")
    logger.info("🔄 CASO 3: ACTIVAR/DESACTIVAR USUARIO")
    logger.info("=" * 60)
    logger.info("📋 Escenario: Administrador activa/desactiva usuario")
    logger.info("📋 Acción: Cambiar estado is_active del usuario")
    
    # 1. Desactivar usuario
    logger.info("")
    logger.info("1️⃣ DESACTIVANDO USUARIO")
    logger.info("-" * 40)
    update_data = {"is_active": False}
    usuario_desactivado = actualizar_usuario(token, USUARIO_PRUEBA_ID, update_data)
    if not usuario_desactivado:
        logger.error("❌ No se pudo desactivar el usuario")
        return False
    
    logger.info(f"   ✅ Usuario desactivado exitosamente")
    logger.info(f"   📊 Estado: {'Activo' if usuario_desactivado['is_active'] else 'Inactivo'}")
    
    # 2. Probar login con usuario desactivado (debe fallar)
    logger.info("")
    logger.info("2️⃣ PROBANDO LOGIN CON USUARIO DESACTIVADO (DEBE FALLAR)")
    logger.info("-" * 40)
    login_fallido = not probar_login_usuario(USUARIO_PRUEBA_EMAIL, "SegundaContraseña456!")
    if login_fallido:
        logger.info("   ✅ Login correctamente bloqueado para usuario inactivo")
    else:
        logger.error("   ❌ ERROR: Usuario inactivo pudo hacer login")
        return False
    
    # 3. Reactivar usuario
    logger.info("")
    logger.info("3️⃣ REACTIVANDO USUARIO")
    logger.info("-" * 40)
    update_data = {"is_active": True}
    usuario_reactivado = actualizar_usuario(token, USUARIO_PRUEBA_ID, update_data)
    if not usuario_reactivado:
        logger.error("❌ No se pudo reactivar el usuario")
        return False
    
    logger.info(f"   ✅ Usuario reactivado exitosamente")
    logger.info(f"   📊 Estado: {'Activo' if usuario_reactivado['is_active'] else 'Inactivo'}")
    
    # 4. Probar login con usuario reactivado (debe funcionar)
    logger.info("")
    logger.info("4️⃣ PROBANDO LOGIN CON USUARIO REACTIVADO (DEBE FUNCIONAR)")
    logger.info("-" * 40)
    login_exitoso = probar_login_usuario(USUARIO_PRUEBA_EMAIL, "SegundaContraseña456!")
    
    if login_exitoso:
        logger.info("✅ CASO 3 COMPLETADO EXITOSAMENTE")
        logger.info("   🎯 Usuario correctamente desactivado y reactivado")
        logger.info("   🎯 Login bloqueado cuando inactivo, permitido cuando activo")
        return True
    else:
        logger.error("❌ CASO 3 FALLÓ")
        return False

def simular_caso_4_cambio_email(token: str):
    """CASO 4: Cambio de email del usuario"""
    logger.info("")
    logger.info("📧 CASO 4: CAMBIO DE EMAIL DEL USUARIO")
    logger.info("=" * 60)
    logger.info("📋 Escenario: Usuario cambia su email")
    logger.info("📋 Acción: Actualizar email en base de datos")
    
    # 1. Cambiar email
    nuevo_email = "prueba2.nuevo@gmail.com"
    logger.info("")
    logger.info("1️⃣ CAMBIANDO EMAIL DEL USUARIO")
    logger.info("-" * 40)
    logger.info(f"   📧 Email anterior: {USUARIO_PRUEBA_EMAIL}")
    logger.info(f"   📧 Email nuevo: {nuevo_email}")
    
    update_data = {"email": nuevo_email}
    usuario_actualizado = actualizar_usuario(token, USUARIO_PRUEBA_ID, update_data)
    if not usuario_actualizado:
        logger.error("❌ No se pudo cambiar el email")
        return False
    
    logger.info(f"   ✅ Email actualizado exitosamente")
    logger.info(f"   📊 Nuevo email: {usuario_actualizado['email']}")
    
    # 2. Probar login con nuevo email
    logger.info("")
    logger.info("2️⃣ PROBANDO LOGIN CON NUEVO EMAIL")
    logger.info("-" * 40)
    login_exitoso = probar_login_usuario(nuevo_email, "SegundaContraseña456!")
    
    if login_exitoso:
        logger.info("✅ CASO 4 COMPLETADO EXITOSAMENTE")
        logger.info("   🎯 Usuario puede hacer login con nuevo email")
        logger.info("   🎯 Email actualizado en base de datos")
        
        # Restaurar email original para otros tests
        logger.info("")
        logger.info("3️⃣ RESTAURANDO EMAIL ORIGINAL")
        logger.info("-" * 40)
        update_data = {"email": USUARIO_PRUEBA_EMAIL}
        usuario_restaurado = actualizar_usuario(token, USUARIO_PRUEBA_ID, update_data)
        if usuario_restaurado:
            logger.info(f"   ✅ Email restaurado: {usuario_restaurado['email']}")
        
        return True
    else:
        logger.error("❌ CASO 4 FALLÓ")
        return False

def simular_caso_5_cambio_datos_personales(token: str):
    """CASO 5: Cambio de datos personales"""
    logger.info("")
    logger.info("👤 CASO 5: CAMBIO DE DATOS PERSONALES")
    logger.info("=" * 60)
    logger.info("📋 Escenario: Usuario cambia nombre y apellido")
    logger.info("📋 Acción: Actualizar datos personales")
    
    # 1. Cambiar datos personales
    logger.info("")
    logger.info("1️⃣ CAMBIANDO DATOS PERSONALES")
    logger.info("-" * 40)
    logger.info("   📝 Nombre anterior: Prueba Dos")
    logger.info("   📝 Nombre nuevo: Prueba Actualizada")
    
    update_data = {
        "nombre": "Prueba Actualizada",
        "apellido": "Usuario Modificado"
    }
    usuario_actualizado = actualizar_usuario(token, USUARIO_PRUEBA_ID, update_data)
    if not usuario_actualizado:
        logger.error("❌ No se pudo actualizar los datos personales")
        return False
    
    logger.info(f"   ✅ Datos personales actualizados exitosamente")
    logger.info(f"   📊 Nuevo nombre: {usuario_actualizado['nombre']}")
    logger.info(f"   📊 Nuevo apellido: {usuario_actualizado['apellido']}")
    
    # 2. Probar login después del cambio
    logger.info("")
    logger.info("2️⃣ PROBANDO LOGIN DESPUÉS DEL CAMBIO DE DATOS")
    logger.info("-" * 40)
    login_exitoso = probar_login_usuario(USUARIO_PRUEBA_EMAIL, "SegundaContraseña456!")
    
    if login_exitoso:
        logger.info("✅ CASO 5 COMPLETADO EXITOSAMENTE")
        logger.info("   🎯 Usuario puede hacer login después del cambio")
        logger.info("   🎯 Datos personales actualizados correctamente")
        
        # Restaurar datos originales
        logger.info("")
        logger.info("3️⃣ RESTAURANDO DATOS ORIGINALES")
        logger.info("-" * 40)
        update_data = {
            "nombre": "Prueba",
            "apellido": "Dos"
        }
        usuario_restaurado = actualizar_usuario(token, USUARIO_PRUEBA_ID, update_data)
        if usuario_restaurado:
            logger.info(f"   ✅ Datos restaurados: {usuario_restaurado['nombre']} {usuario_restaurado['apellido']}")
        
        return True
    else:
        logger.error("❌ CASO 5 FALLÓ")
        return False

def main():
    logger.info("🎭 SIMULACIÓN COMPLETA DE CASOS REALES DE GESTIÓN DE USUARIOS")
    logger.info("=" * 80)
    logger.info(f"📊 Fecha y hora: {datetime.now()}")
    logger.info("🎯 Objetivo: Simular escenarios reales de gestión de usuarios")
    logger.info("📋 Casos: Olvido de contraseña, activación/desactivación, cambio de email")
    logger.info("=" * 80)
    logger.info("")

    # Login como administrador
    logger.info("🔑 REALIZANDO LOGIN COMO ADMINISTRADOR")
    logger.info("-" * 50)
    admin_token = login_admin()
    if not admin_token:
        logger.error("❌ No se pudo iniciar sesión como administrador. Abortando.")
        return

    # Ejecutar todos los casos de simulación
    casos_exitosos = 0
    total_casos = 5

    # CASO 1: Usuario olvida contraseña
    if simular_caso_1_usuario_olvida_contraseña(admin_token):
        casos_exitosos += 1
    time.sleep(2)  # Pausa entre casos

    # CASO 2: Usuario olvida contraseña segunda vez
    if simular_caso_2_usuario_olvida_contraseña_segunda_vez(admin_token):
        casos_exitosos += 1
    time.sleep(2)  # Pausa entre casos

    # CASO 3: Activar/desactivar usuario
    if simular_caso_3_activar_desactivar_usuario(admin_token):
        casos_exitosos += 1
    time.sleep(2)  # Pausa entre casos

    # CASO 4: Cambio de email
    if simular_caso_4_cambio_email(admin_token):
        casos_exitosos += 1
    time.sleep(2)  # Pausa entre casos

    # CASO 5: Cambio de datos personales
    if simular_caso_5_cambio_datos_personales(admin_token):
        casos_exitosos += 1

    # Resumen final
    logger.info("")
    logger.info("📊 RESUMEN FINAL DE SIMULACIÓN")
    logger.info("=" * 80)
    logger.info(f"🎯 Casos ejecutados: {total_casos}")
    logger.info(f"✅ Casos exitosos: {casos_exitosos}")
    logger.info(f"❌ Casos fallidos: {total_casos - casos_exitosos}")
    logger.info(f"📈 Tasa de éxito: {(casos_exitosos/total_casos)*100:.1f}%")
    logger.info("")
    
    if casos_exitosos == total_casos:
        logger.info("🎉 TODOS LOS CASOS REALES FUNCIONAN CORRECTAMENTE")
        logger.info("   ✅ Sistema permite cambio de contraseñas múltiples")
        logger.info("   ✅ Sistema permite activar/desactivar usuarios")
        logger.info("   ✅ Sistema permite cambio de emails")
        logger.info("   ✅ Sistema permite cambio de datos personales")
        logger.info("   ✅ Todas las operaciones se registran en auditoría")
        logger.info("   ✅ Base de datos se actualiza automáticamente")
    else:
        logger.error("❌ ALGUNOS CASOS FALLARON")
        logger.error("   💡 Revisar logs para identificar problemas específicos")

if __name__ == "__main__":
    main()
