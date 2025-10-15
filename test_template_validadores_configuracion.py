#!/usr/bin/env python3
"""
Script para validar templates en validadores y configuracion
"""
import requests
import json

BASE_URL = "https://pagos-f2qf.onrender.com"
API_BASE = f"{BASE_URL}/api/v1"

# Credenciales (probando ambas opciones)
LOGIN_OPTIONS = [
    {"email": "admin@financiamiento.com", "password": "admin123"},
    {"email": "admin@rapicredit.com", "password": "admin123"}
]

def login():
    """Login y obtener token"""
    print("\n1. LOGIN")
    
    # Probar ambas credenciales
    for idx, creds in enumerate(LOGIN_OPTIONS, 1):
        try:
            print(f"\nProbando credenciales {idx}: {creds['email']}")
            response = requests.post(
                f"{API_BASE}/auth/login",
                json=creds,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                token = data.get("access_token")
                print(f"Login exitoso con {creds['email']}")
                return token
            else:
                print(f"Error: {response.status_code}")
                
        except Exception as e:
            print(f"Error: {e}")
    
    print("\nNo se pudo hacer login con ninguna credencial")
    return None

def test_validadores_configuracion(token):
    """Probar endpoint de configuracion de validadores"""
    print("\n2. VALIDADORES - CONFIGURACION")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(
            f"{API_BASE}/validadores/configuracion",
            headers=headers,
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\nEXISTE TEMPLATE DE CONFIGURACION")
            
            # Verificar estructura
            print("\nCOMPONENTES DEL TEMPLATE:")
            if "titulo" in data:
                print(f"- Titulo: {data['titulo']}")
            if "paises_soportados" in data:
                print(f"- Paises soportados: {len(data['paises_soportados'])} paises")
            if "validadores_disponibles" in data:
                print(f"- Validadores disponibles: {len(data['validadores_disponibles'])} validadores")
            if "reglas_negocio" in data:
                print(f"- Reglas de negocio: {len(data['reglas_negocio'])} reglas")
            if "configuracion_frontend" in data:
                print(f"- Configuracion frontend: {len(data['configuracion_frontend'])} configuraciones")
            
            # Validadores disponibles
            print("\nVALIDADORES DISPONIBLES:")
            if "validadores_disponibles" in data:
                for validador, info in data["validadores_disponibles"].items():
                    print(f"  - {validador}: {info.get('descripcion', 'Sin descripcion')}")
            
            # Paises soportados
            print("\nPAISES SOPORTADOS:")
            if "paises_soportados" in data:
                for pais, config in data["paises_soportados"].items():
                    print(f"  - {pais.upper()}")
            
            return True
            
        else:
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_validadores_ejemplos(token):
    """Probar endpoint de ejemplos de correccion"""
    print("\n3. VALIDADORES - EJEMPLOS DE CORRECCION")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(
            f"{API_BASE}/validadores/ejemplos-correccion",
            headers=headers,
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\nEXISTE TEMPLATE DE EJEMPLOS")
            
            if "ejemplos" in data:
                print(f"\nEJEMPLOS DISPONIBLES: {len(data['ejemplos'])} tipos")
                for tipo, ejemplo in data["ejemplos"].items():
                    print(f"  - {tipo}: {ejemplo.get('titulo', 'Sin titulo')}")
            
            if "herramientas_disponibles" in data:
                print(f"\nHERRAMIENTAS: {len(data['herramientas_disponibles'])} endpoints")
            
            return True
        else:
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_validadores_verificacion(token):
    """Probar endpoint de verificacion del sistema"""
    print("\n4. VALIDADORES - VERIFICACION DEL SISTEMA")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(
            f"{API_BASE}/validadores/verificacion-validadores",
            headers=headers,
            timeout=10
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\nEXISTE TEMPLATE DE VERIFICACION")
            
            if "validadores_implementados" in data:
                print(f"\nVALIDADORES IMPLEMENTADOS: {len(data['validadores_implementados'])} validadores")
                for validador, info in data["validadores_implementados"].items():
                    estado = info.get('estado', 'Sin estado')
                    print(f"  - {validador}: {estado}")
            
            if "funcionalidades_especiales" in data:
                print(f"\nFUNCIONALIDADES ESPECIALES: {len(data['funcionalidades_especiales'])} funcionalidades")
            
            if "endpoints_principales" in data:
                print(f"\nENDPOINTS PRINCIPALES: {len(data['endpoints_principales'])} endpoints")
            
            return True
        else:
            print(f"Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    print("=" * 70)
    print("VALIDACION: TEMPLATES EN VALIDADORES Y CONFIGURACION")
    print("=" * 70)
    
    # Login
    token = login()
    if not token:
        print("\nERROR: No se pudo obtener token")
        return
    
    # Tests
    config_ok = test_validadores_configuracion(token)
    ejemplos_ok = test_validadores_ejemplos(token)
    verificacion_ok = test_validadores_verificacion(token)
    
    # Resumen
    print("\n" + "=" * 70)
    print("RESUMEN DE VALIDACION")
    print("=" * 70)
    
    templates = []
    if config_ok:
        templates.append("CONFIGURACION")
    if ejemplos_ok:
        templates.append("EJEMPLOS DE CORRECCION")
    if verificacion_ok:
        templates.append("VERIFICACION DEL SISTEMA")
    
    print(f"\nTEMPLATES ENCONTRADOS: {len(templates)}/3")
    for template in templates:
        print(f"  - {template}")
    
    print("\nENDPOINTS DE VALIDADORES:")
    print("  - GET /api/v1/validadores/configuracion - Template de configuracion")
    print("  - GET /api/v1/validadores/ejemplos-correccion - Template de ejemplos")
    print("  - GET /api/v1/validadores/verificacion-validadores - Template de verificacion")
    print("  - POST /api/v1/validadores/validar-campo - Validacion en tiempo real")
    print("  - POST /api/v1/validadores/formatear-tiempo-real - Formateo automatico")
    
    print("\nINTEGRACION CON FORMULARIO NUEVO CLIENTE:")
    print("  - El formulario usa estos templates para:")
    print("    1. Obtener configuracion de validadores")
    print("    2. Validar campos en tiempo real")
    print("    3. Formatear datos automaticamente")
    print("    4. Mostrar ejemplos de correccion")
    
    if len(templates) == 3:
        print("\nRESULTADO: SI EXISTEN TEMPLATES EN VALIDADORES.CONFIGURACION")
        print("Todos los templates estan funcionando correctamente")
    else:
        print("\nRESULTADO: TEMPLATES PARCIALMENTE DISPONIBLES")
        print(f"{len(templates)}/3 templates funcionando")

if __name__ == "__main__":
    main()

