#!/usr/bin/env python3
"""
Script para monitorear el estado del despliegue
"""
import requests
import time
import json

def verificar_frontend():
    """Verificar si el frontend está disponible"""
    try:
        response = requests.get("https://rapicredit.onrender.com", timeout=10)
        if response.status_code == 200:
            print("✅ Frontend disponible")
            return True
        else:
            print(f"⚠️ Frontend respondiendo con status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Frontend no disponible: {e}")
        return False

def verificar_backend():
    """Verificar si el backend está disponible"""
    try:
        response = requests.get("https://pagos-f2qf.onrender.com/api/v1/health", timeout=10)
        if response.status_code == 200:
            print("✅ Backend disponible")
            return True
        else:
            print(f"⚠️ Backend respondiendo con status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Backend no disponible: {e}")
        return False

def verificar_bd():
    """Verificar si la base de datos está disponible"""
    try:
        response = requests.get("https://pagos-f2qf.onrender.com/api/v1/concesionarios/test-no-auth", timeout=10)
        if response.status_code == 200:
            print("✅ Base de datos disponible")
            return True
        elif response.status_code == 503:
            print("⚠️ Base de datos temporalmente no disponible")
            return False
        else:
            print(f"⚠️ BD respondiendo con status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error verificando BD: {e}")
        return False

def monitorear_despliegue():
    """Monitorear el estado del despliegue"""
    print("MONITOREANDO ESTADO DEL DESPLIEGUE")
    print("=" * 50)
    
    max_intentos = 20
    intervalo = 30  # segundos
    
    for intento in range(max_intentos):
        print(f"\n--- Verificación {intento + 1}/{max_intentos} ---")
        print(f"Tiempo: {time.strftime('%H:%M:%S')}")
        
        # Verificar frontend
        frontend_ok = verificar_frontend()
        
        # Verificar backend
        backend_ok = verificar_backend()
        
        # Verificar BD
        bd_ok = verificar_bd()
        
        # Resumen
        print(f"\nEstado actual:")
        print(f"  Frontend: {'✅' if frontend_ok else '❌'}")
        print(f"  Backend: {'✅' if backend_ok else '❌'}")
        print(f"  Base de datos: {'✅' if bd_ok else '❌'}")
        
        # Si todo está funcionando
        if frontend_ok and backend_ok and bd_ok:
            print("\n🎉 ¡SISTEMA COMPLETAMENTE FUNCIONAL!")
            print("Puedes usar la aplicación normalmente")
            return True
        
        # Si es el último intento
        if intento == max_intentos - 1:
            print("\n⏰ Tiempo de monitoreo completado")
            print("El sistema puede seguir desplegándose en segundo plano")
            return False
        
        # Esperar antes del siguiente intento
        print(f"\nEsperando {intervalo} segundos...")
        time.sleep(intervalo)
    
    return False

def main():
    """Función principal"""
    print("MONITOR DE DESPLIEGUE - RAPICREDIT")
    print("=" * 60)
    print("Este script monitoreará el estado del despliegue")
    print("y te notificará cuando todo esté funcionando")
    print()
    
    resultado = monitorear_despliegue()
    
    if resultado:
        print("\n✅ MONITOREO EXITOSO")
        print("El sistema está completamente operativo")
    else:
        print("\n⏳ MONITOREO COMPLETADO")
        print("El sistema puede seguir desplegándose")
        print("Verifica manualmente en unos minutos")

if __name__ == "__main__":
    main()
