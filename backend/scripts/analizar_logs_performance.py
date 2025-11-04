#!/usr/bin/env python3
"""
Script para analizar logs y verificar el impacto de los índices críticos
"""
import requests
import time
from datetime import datetime
import json

# URL base del API
API_BASE_URL = "https://pagos-f2qf.onrender.com"

def test_endpoint_performance(endpoint, nombre):
    """Probar un endpoint y medir el tiempo de respuesta"""
    url = f"{API_BASE_URL}{endpoint}"
    
    print(f"\n{'='*70}")
    print(f"📊 TESTING: {nombre}")
    print(f"URL: {url}")
    print(f"{'='*70}")
    
    tiempos = []
    errores = 0
    
    # Hacer 3 requests para tener un promedio
    for i in range(3):
        try:
            inicio = time.time()
            response = requests.get(url, timeout=30)
            tiempo_respuesta = (time.time() - inicio) * 1000  # en milisegundos
            tiempos.append(tiempo_respuesta)
            
            status = "✅" if response.status_code == 200 else "⚠️"
            print(f"{status} Request {i+1}: {tiempo_respuesta:.2f}ms - Status: {response.status_code}")
            
            if response.status_code != 200:
                errores += 1
                print(f"   Response: {response.text[:200]}")
                
        except requests.exceptions.Timeout:
            print(f"❌ Request {i+1}: TIMEOUT (>30s)")
            errores += 1
        except Exception as e:
            print(f"❌ Request {i+1}: Error - {str(e)}")
            errores += 1
    
    if tiempos:
        promedio = sum(tiempos) / len(tiempos)
        minimo = min(tiempos)
        maximo = max(tiempos)
        
        print(f"\n📈 RESULTADOS:")
        print(f"   Promedio: {promedio:.2f}ms")
        print(f"   Mínimo: {minimo:.2f}ms")
        print(f"   Máximo: {maximo:.2f}ms")
        print(f"   Errores: {errores}/3")
        
        # Verificar si está dentro del objetivo
        if promedio < 500:
            print(f"   ✅ EXCELENTE: <500ms (objetivo cumplido)")
        elif promedio < 2000:
            print(f"   ⚠️ ACEPTABLE: <2s (mejora significativa)")
        elif promedio < 10000:
            print(f"   ⚠️ MEJORABLE: <10s (mejora parcial)")
        else:
            print(f"   ❌ CRÍTICO: >10s (requiere más optimización)")
        
        return {
            "endpoint": endpoint,
            "promedio": promedio,
            "minimo": minimo,
            "maximo": maximo,
            "errores": errores,
            "timestamp": datetime.now().isoformat()
        }
    
    return None

def main():
    """Ejecutar análisis de performance"""
    print("="*70)
    print("🚀 ANÁLISIS DE PERFORMANCE: Índices Críticos")
    print("="*70)
    print(f"⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 API Base: {API_BASE_URL}")
    print()
    
    # Endpoints críticos a probar
    endpoints = [
        ("/api/v1/notificaciones/estadisticas/resumen", "Estadísticas de Notificaciones (CRÍTICO)"),
        ("/api/v1/health/render", "Health Check"),
    ]
    
    resultados = []
    
    for endpoint, nombre in endpoints:
        resultado = test_endpoint_performance(endpoint, nombre)
        if resultado:
            resultados.append(resultado)
        time.sleep(1)  # Pausa entre requests
    
    # Resumen final
    print("\n" + "="*70)
    print("📊 RESUMEN FINAL")
    print("="*70)
    
    for resultado in resultados:
        endpoint = resultado["endpoint"]
        promedio = resultado["promedio"]
        
        # Comparar con baseline conocido (57 segundos para notificaciones)
        if "notificaciones" in endpoint:
            mejora = (57000 / promedio) if promedio > 0 else 0
            print(f"\n{endpoint}:")
            print(f"  ⏱️  Tiempo actual: {promedio:.2f}ms")
            print(f"  📈 Mejora vs baseline (57s): {mejora:.1f}x")
            if mejora > 100:
                print(f"  ✅ MEJORA ESPECTACULAR (>100x)")
            elif mejora > 10:
                print(f"  ✅ MEJORA SIGNIFICATIVA (>10x)")
            elif mejora > 2:
                print(f"  ⚠️ MEJORA MODERADA (>2x)")
            else:
                print(f"  ❌ MEJORA INSUFICIENTE (<2x)")
    
    print("\n" + "="*70)
    print("✅ Análisis completado")
    print("="*70)
    print("\n📝 PRÓXIMOS PASOS:")
    print("1. Verificar logs en Render Dashboard para ver creación de índices")
    print("2. Verificar que la migración se ejecutó correctamente")
    print("3. Monitorear tiempos de respuesta en producción")
    print("4. Si los tiempos aún son altos, revisar logs de queries en PostgreSQL")
    print()

if __name__ == "__main__":
    main()

