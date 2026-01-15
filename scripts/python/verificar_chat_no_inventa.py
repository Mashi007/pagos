#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar que el Chat AI no inventa información
y solo usa datos de la base de datos
"""

import sys
import io
from pathlib import Path

# Configurar encoding para Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Agregar backend al path para imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from app.api.v1.endpoints.configuracion import (
    _construir_system_prompt_default,
    _validar_pregunta_es_sobre_bd,
    _obtener_resumen_bd,
)
from app.db.session import SessionLocal

def verificar_system_prompt():
    """Verifica que el system prompt tenga restricciones claras sobre no inventar"""
    print("=" * 70)
    print("VERIFICACIÓN DEL SYSTEM PROMPT")
    print("=" * 70)
    
    db = SessionLocal()
    try:
        resumen_bd = _obtener_resumen_bd(db)
        
        system_prompt = _construir_system_prompt_default(
            resumen_bd=resumen_bd,
            info_cliente_buscado="",
            datos_adicionales="",
            info_esquema="",
            contexto_documentos="",
            consultas_dinamicas="",
        )
        
        # Verificar palabras clave críticas
        palabras_criticas = [
            "PROHIBIDO INVENTAR",
            "PROHIBICIÓN ABSOLUTA",
            "NO inventes",
            "NO uses tu conocimiento",
            "SOLO puedes usar",
            "ÚNICA fuente",
            "No tengo esa información",
        ]
        
        encontradas = []
        no_encontradas = []
        
        for palabra in palabras_criticas:
            if palabra.lower() in system_prompt.lower():
                encontradas.append(palabra)
            else:
                no_encontradas.append(palabra)
        
        print(f"\n✅ Palabras críticas encontradas ({len(encontradas)}/{len(palabras_criticas)}):")
        for palabra in encontradas:
            print(f"   ✅ {palabra}")
        
        if no_encontradas:
            print(f"\n❌ Palabras críticas NO encontradas ({len(no_encontradas)}):")
            for palabra in no_encontradas:
                print(f"   ❌ {palabra}")
        
        # Verificar longitud del prompt
        print(f"\n📊 Longitud del system prompt: {len(system_prompt):,} caracteres")
        
        # Mostrar sección crítica
        print("\n" + "=" * 70)
        print("SECCIÓN CRÍTICA DEL PROMPT (primeros 500 caracteres):")
        print("=" * 70)
        print(system_prompt[:500])
        print("...")
        
        return len(no_encontradas) == 0
        
    finally:
        db.close()

def verificar_validacion_preguntas():
    """Verifica que la validación de preguntas funcione correctamente"""
    print("\n" + "=" * 70)
    print("VERIFICACIÓN DE VALIDACIÓN DE PREGUNTAS")
    print("=" * 70)
    
    # Preguntas válidas (sobre BD)
    preguntas_validas = [
        "cuantos prestamos hay",
        "cual es el nombre del cliente con cedula v123456789",
        "cuantos pagos se hicieron hoy",
        "total de clientes",
        "prestamos aprobados",
    ]
    
    # Preguntas inválidas (no sobre BD)
    preguntas_invalidas = [
        "como se hace un pastel",
        "que tiempo hace hoy",
        "cual es la capital de venezuela",
        "historia de los prestamos",
    ]
    
    print("\n✅ Probando preguntas VÁLIDAS (deben pasar):")
    todas_validas_ok = True
    for pregunta in preguntas_validas:
        try:
            _validar_pregunta_es_sobre_bd(pregunta)
            print(f"   ✅ '{pregunta}' → VÁLIDA")
        except Exception as e:
            print(f"   ❌ '{pregunta}' → RECHAZADA (ERROR: {e})")
            todas_validas_ok = False
    
    print("\n❌ Probando preguntas INVÁLIDAS (deben ser rechazadas):")
    todas_invalidas_ok = True
    for pregunta in preguntas_invalidas:
        try:
            _validar_pregunta_es_sobre_bd(pregunta)
            print(f"   ❌ '{pregunta}' → ACEPTADA (ERROR: debería ser rechazada)")
            todas_invalidas_ok = False
        except Exception:
            print(f"   ✅ '{pregunta}' → RECHAZADA (correcto)")
    
    return todas_validas_ok and todas_invalidas_ok

def main():
    """Función principal"""
    print("=" * 70)
    print("VERIFICACIÓN: CHAT AI NO DEBE INVENTAR INFORMACIÓN")
    print("=" * 70)
    
    # Verificar system prompt
    prompt_ok = verificar_system_prompt()
    
    # Verificar validación de preguntas
    validacion_ok = verificar_validacion_preguntas()
    
    # Resumen final
    print("\n" + "=" * 70)
    print("RESUMEN FINAL")
    print("=" * 70)
    
    verificaciones = {
        "System prompt con restricciones": prompt_ok,
        "Validación de preguntas": validacion_ok,
    }
    
    for nombre, resultado in verificaciones.items():
        estado = "✅ OK" if resultado else "❌ FALLO"
        print(f"{nombre:40} {estado}")
    
    total_ok = sum(1 for v in verificaciones.values() if v)
    total_total = len(verificaciones)
    
    print("\n" + "-" * 70)
    print(f"Total: {total_ok}/{total_total} verificaciones exitosas")
    
    if total_ok == total_total:
        print("\n✅ CONFIGURACIÓN CORRECTA")
        print("El Chat AI está configurado para:")
        print("  - Solo usar datos de la base de datos")
        print("  - NO inventar información")
        print("  - Rechazar preguntas que no sean sobre la BD")
        return 0
    else:
        print("\n⚠️ ALGUNAS VERIFICACIONES FALLARON")
        print("Revisa los detalles arriba")
        return 1

if __name__ == "__main__":
    sys.exit(main())
