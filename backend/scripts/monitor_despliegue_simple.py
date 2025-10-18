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
            print("OK - Frontend disponible")
            return True
        else:
            print(f"WARNING - Frontend respondiendo con status: {response.status_code}")
            return False
    except Exception as e:
        print(f"ERROR - Frontend no disponible: {e}")
        return False

def verificar_backend():
    """Verificar si el backend está disponible"""
    try:
        response = requests.get("https://pagos-f2qf.onrender.com/api/v1/health", timeout=10)
        if response.status_code == 200:
            print("OK - Backend disponible")
            return True
        else:
            print(f"WARNING - Backend respondiendo con status: {response.status_code}")
            return False
    except Exception as e:
        print(f"ERROR - Backend no disponible: {e}")
        return False

def verificar_bd():
    """Verificar si la base de datos está disponible"""
    try:
        response = requests.get("https://pagos-f2qf.onrender.com/api/v1/concesionarios/test-no-auth", timeout=10)
        if response.status_code == 200:
            print("OK - Base de datos disponible")
            return True
        elif response.status_code == 503:
            print("WARNING - Base de datos temporalmente no disponible")
            return False
        else:
            print(f"WARNING - BD respondiendo con status: {response.status_code}")
            return False
    except Exception as e:
        print(f"ERROR - Error verificando BD: {e}")
        return False

def monitorear_despliegue():
    """Monitorear el estado del despliegue"""
    print("MONITOREANDO ESTADO DEL DESPLIEGUE")
    print("=" * 50)
    
    max_intentos = 10
    intervalo = 30  # segundos
    
    for intento in range(max_intentos):
        print(f"\n--- Verificacion {intento + 1}/{max_intentos} ---")
        print(f"Tiempo: {time.strftime('%H:%M:%S')}")
        
        # Verificar frontend
        frontend_ok = verificar_frontend()
        
        # Verificar backend
        backend_ok = verificar_backend()
        
        # Verificar BD
        bd_ok = verificar_bd()
        
        # Resumen
        print(f"\nEstado actual:")
        print(f"  Frontend: {'OK' if frontend_ok else 'ERROR'}")
        print(f"  Backend: {'OK' if backend_ok else 'ERROR'}")
        print(f"  Base de datos: {'OK' if bd_ok else 'ERROR'}")
        
        # Si todo está funcionando
        if frontend_ok and backend_ok and bd_ok:
            print("\nSISTEMA COMPLETAMENTE FUNCIONAL!")
            print("Puedes usar la aplicacion normalmente")
            return True
        
        # Si es el último intento
        if intento == max_intentos - 1:
            print("\nTiempo de monitoreo completado")
            print("El sistema puede seguir desplegandose en segundo plano")
            return False
        
        # Esperar antes del siguiente intento
        print(f"\nEsperando {intervalo} segundos...")
        time.sleep(intervalo)
    
    return False

def main():
    """Función principal"""
    print("MONITOR DE DESPLIEGUE - RAPICREDIT")
    print("=" * 60)
    print("Este script monitoreara el estado del despliegue")
    print("y te notificara cuando todo este funcionando")
    print()
    
    resultado = monitorear_despliegue()
    
    if resultado:
        print("\nMONITOREO EXITOSO")
        print("El sistema esta completamente operativo")
    else:
        print("\nMONITOREO COMPLETADO")
        print("El sistema puede seguir desplegandose")
        print("Verifica manualmente en unos minutos")

if __name__ == "__main__":
    main()
