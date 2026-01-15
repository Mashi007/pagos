#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para verificar que el Chat AI solo usa las 4 tablas permitidas:
- clientes
- prestamos
- cuotas
- pagos
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
    _obtener_inventario_campos_bd,
    _obtener_resumen_bd,
)
from app.db.session import SessionLocal

def verificar_tablas_en_inventario():
    """Verifica que el inventario solo incluya las 4 tablas permitidas"""
    print("=" * 70)
    print("VERIFICACIÓN DE TABLAS EN INVENTARIO")
    print("=" * 70)
    
    db = SessionLocal()
    try:
        inventario = _obtener_inventario_campos_bd(db)
        
        tablas_permitidas = ["clientes", "prestamos", "cuotas", "pagos"]
        tablas_no_permitidas = [
            "notificaciones", "users", "concesionarios", "analistas",
            "configuracion_sistema", "documentos_ai", "auditorias",
            "prestamos_evaluacion", "prestamos_auditoria", "pagos_auditoria",
        ]
        
        tablas_encontradas_permitidas = []
        tablas_encontradas_no_permitidas = []
        
        inventario_lower = inventario.lower()
        
        for tabla in tablas_permitidas:
            if f"tabla: {tabla}" in inventario_lower or f"tabla: {tabla.upper()}" in inventario_lower:
                tablas_encontradas_permitidas.append(tabla)
        
        for tabla in tablas_no_permitidas:
            if f"tabla: {tabla}" in inventario_lower or f"tabla: {tabla.upper()}" in inventario_lower:
                tablas_encontradas_no_permitidas.append(tabla)
        
        print(f"\n✅ Tablas PERMITIDAS encontradas ({len(tablas_encontradas_permitidas)}/4):")
        for tabla in tablas_permitidas:
            estado = "✅" if tabla in tablas_encontradas_permitidas else "❌"
            print(f"   {estado} {tabla}")
        
        if tablas_encontradas_no_permitidas:
            print(f"\n❌ Tablas NO PERMITIDAS encontradas ({len(tablas_encontradas_no_permitidas)}):")
            for tabla in tablas_encontradas_no_permitidas:
                print(f"   ❌ {tabla}")
        else:
            print(f"\n✅ No se encontraron tablas no permitidas")
        
        # Verificar mensaje de restricción
        tiene_restriccion = "solo puede consultar estas 4 tablas" in inventario_lower or "tablas permitidas" in inventario_lower
        print(f"\n📋 Mensaje de restricción presente: {'✅ SÍ' if tiene_restriccion else '❌ NO'}")
        
        return len(tablas_encontradas_permitidas) == 4 and len(tablas_encontradas_no_permitidas) == 0 and tiene_restriccion
        
    finally:
        db.close()

def verificar_system_prompt():
    """Verifica que el system prompt mencione las restricciones de tablas"""
    print("\n" + "=" * 70)
    print("VERIFICACIÓN DE SYSTEM PROMPT")
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
        
        palabras_clave = [
            "solo puede consultar estas 4 tablas",
            "clientes",
            "prestamos",
            "cuotas",
            "pagos",
            "consultas cruzadas",
            "joins",
        ]
        
        encontradas = []
        no_encontradas = []
        
        prompt_lower = system_prompt.lower()
        
        for palabra in palabras_clave:
            if palabra in prompt_lower:
                encontradas.append(palabra)
            else:
                no_encontradas.append(palabra)
        
        print(f"\n✅ Palabras clave encontradas ({len(encontradas)}/{len(palabras_clave)}):")
        for palabra in encontradas:
            print(f"   ✅ {palabra}")
        
        if no_encontradas:
            print(f"\n⚠️ Palabras clave NO encontradas ({len(no_encontradas)}):")
            for palabra in no_encontradas:
                print(f"   ⚠️ {palabra}")
        
        # Verificar que mencione las 4 tablas específicas
        tiene_4_tablas = all(tabla in prompt_lower for tabla in ["clientes", "prestamos", "cuotas", "pagos"])
        print(f"\n📋 Menciona las 4 tablas específicas: {'✅ SÍ' if tiene_4_tablas else '❌ NO'}")
        
        return len(encontradas) >= 5 and tiene_4_tablas
        
    finally:
        db.close()

def verificar_resumen_bd():
    """Verifica que el resumen de BD solo incluya las 4 tablas permitidas"""
    print("\n" + "=" * 70)
    print("VERIFICACIÓN DE RESUMEN DE BD")
    print("=" * 70)
    
    db = SessionLocal()
    try:
        resumen = _obtener_resumen_bd(db)
        
        tablas_permitidas = ["clientes", "prestamos", "cuotas", "pagos"]
        tablas_no_permitidas = [
            "notificaciones", "users", "concesionarios", "analistas",
            "configuracion_sistema", "documentos_ai",
        ]
        
        resumen_lower = resumen.lower()
        
        tablas_encontradas_permitidas = [t for t in tablas_permitidas if t in resumen_lower]
        tablas_encontradas_no_permitidas = [t for t in tablas_no_permitidas if t in resumen_lower]
        
        print(f"\n✅ Tablas PERMITIDAS en resumen ({len(tablas_encontradas_permitidas)}/4):")
        for tabla in tablas_permitidas:
            estado = "✅" if tabla in tablas_encontradas_permitidas else "❌"
            print(f"   {estado} {tabla}")
        
        if tablas_encontradas_no_permitidas:
            print(f"\n⚠️ Tablas NO PERMITIDAS en resumen ({len(tablas_encontradas_no_permitidas)}):")
            for tabla in tablas_encontradas_no_permitidas:
                print(f"   ⚠️ {tabla}")
        else:
            print(f"\n✅ No se encontraron tablas no permitidas en el resumen")
        
        return len(tablas_encontradas_permitidas) == 4 and len(tablas_encontradas_no_permitidas) == 0
        
    finally:
        db.close()

def main():
    """Función principal"""
    print("=" * 70)
    print("VERIFICACIÓN: SOLO 4 TABLAS PERMITIDAS")
    print("=" * 70)
    print("Tablas permitidas: clientes, prestamos, cuotas, pagos")
    
    # Verificar inventario
    inventario_ok = verificar_tablas_en_inventario()
    
    # Verificar system prompt
    prompt_ok = verificar_system_prompt()
    
    # Verificar resumen BD
    resumen_ok = verificar_resumen_bd()
    
    # Resumen final
    print("\n" + "=" * 70)
    print("RESUMEN FINAL")
    print("=" * 70)
    
    verificaciones = {
        "Inventario solo 4 tablas": inventario_ok,
        "System prompt con restricciones": prompt_ok,
        "Resumen BD solo 4 tablas": resumen_ok,
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
        print("  - Solo usar las 4 tablas: clientes, prestamos, cuotas, pagos")
        print("  - Permitir consultas cruzadas entre estas 4 tablas")
        print("  - NO usar otras tablas del sistema")
        return 0
    else:
        print("\n⚠️ ALGUNAS VERIFICACIONES FALLARON")
        print("Revisa los detalles arriba")
        return 1

if __name__ == "__main__":
    sys.exit(main())
