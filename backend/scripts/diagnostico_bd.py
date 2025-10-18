#!/usr/bin/env python3
"""
Script para verificar estado de la base de datos y proporcionar soluciones
"""
import requests
import time
import json

def verificar_estado_servidor():
    """Verificar estado general del servidor"""
    print("VERIFICANDO ESTADO DEL SERVIDOR")
    print("=" * 40)
    
    base_url = "https://pagos-f2qf.onrender.com"
    
    try:
        # Probar endpoint de health
        print("1. Probando endpoint de health...")
        response = requests.get(f"{base_url}/api/v1/health", timeout=10)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            print("   OK - Servidor respondiendo")
            return True
        else:
            print(f"   ERROR - {response.text}")
            return False
            
    except Exception as e:
        print(f"ERROR - {e}")
        return False

def verificar_base_datos():
    """Verificar estado de la base de datos"""
    print("\nVERIFICANDO ESTADO DE BASE DE DATOS")
    print("=" * 40)
    
    base_url = "https://pagos-f2qf.onrender.com"
    
    try:
        # Probar endpoint que requiere BD
        print("1. Probando conexión a BD...")
        response = requests.get(f"{base_url}/api/v1/concesionarios/test-no-auth", timeout=10)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            print("   OK - Base de datos funcionando")
            return True
        elif response.status_code == 503:
            print("   ERROR - Base de datos temporalmente no disponible")
            return False
        else:
            print(f"   ERROR - {response.text}")
            return False
            
    except Exception as e:
        print(f"ERROR - {e}")
        return False

def proporcionar_soluciones():
    """Proporcionar soluciones al problema"""
    print("\nSOLUCIONES RECOMENDADAS")
    print("=" * 40)
    
    print("1. PROBLEMA IDENTIFICADO:")
    print("   - Error 503: Servicio de base de datos temporalmente no disponible")
    print("   - Esto afecta TODOS los endpoints que requieren BD")
    print()
    
    print("2. CAUSAS POSIBLES:")
    print("   - Render está reiniciando la base de datos")
    print("   - Límite de conexiones excedido")
    print("   - Base de datos en mantenimiento")
    print("   - Problema de red temporal")
    print()
    
    print("3. SOLUCIONES:")
    print("   a) ESPERAR 5-10 minutos para que Render reinicie la BD")
    print("   b) Verificar el dashboard de Render para el estado de la BD")
    print("   c) Si persiste, reiniciar manualmente el servicio en Render")
    print()
    
    print("4. VERIFICACION:")
    print("   - Ejecutar este script cada 2-3 minutos")
    print("   - Cuando el status cambie a 200, el sistema estará funcionando")
    print()

def monitorear_estado():
    """Monitorear el estado cada pocos minutos"""
    print("INICIANDO MONITOREO DEL ESTADO")
    print("=" * 40)
    
    base_url = "https://pagos-f2qf.onrender.com"
    max_intentos = 10
    intervalo = 30  # segundos
    
    for intento in range(max_intentos):
        print(f"\nIntento {intento + 1}/{max_intentos}")
        print(f"Esperando {intervalo} segundos...")
        
        try:
            response = requests.get(f"{base_url}/api/v1/concesionarios/test-no-auth", timeout=10)
            
            if response.status_code == 200:
                print("✅ BASE DE DATOS FUNCIONANDO!")
                print("El sistema está operativo")
                return True
            else:
                print(f"❌ Aún con problemas: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
        
        if intento < max_intentos - 1:
            time.sleep(intervalo)
    
    print("\n⚠️ Monitoreo completado sin éxito")
    print("Revisar manualmente el estado en Render")
    return False

def main():
    """Función principal"""
    print("DIAGNOSTICO DE PROBLEMAS DE BASE DE DATOS")
    print("=" * 60)
    
    # Verificar servidor
    servidor_ok = verificar_estado_servidor()
    
    if servidor_ok:
        # Verificar BD
        bd_ok = verificar_base_datos()
        
        if not bd_ok:
            # Proporcionar soluciones
            proporcionar_soluciones()
            
            # Preguntar si quiere monitorear
            print("¿Quieres iniciar monitoreo automático? (y/n): ", end="")
            respuesta = input().lower()
            
            if respuesta == 'y':
                monitorear_estado()
        else:
            print("\n✅ Sistema funcionando correctamente")
    else:
        print("\n❌ Servidor no responde")

if __name__ == "__main__":
    main()
