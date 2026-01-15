#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para probar el flujo completo de búsqueda por cédula en Chat AI
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

from sqlalchemy import text
from app.db.session import SessionLocal
from app.api.v1.endpoints.configuracion import (
    _extraer_cedula_de_pregunta,
    _obtener_info_cliente_por_cedula,
    _validar_pregunta_es_sobre_bd,
)

def main():
    """Función principal"""
    print("=" * 70)
    print("PRUEBA COMPLETA: BÚSQUEDA POR CÉDULA")
    print("=" * 70)
    print()
    
    pregunta = "CUAL ES EL NOMBRE QUE TIENEN CEDULA v123456789"
    print(f"Pregunta: {pregunta}")
    print()
    
    db = SessionLocal()
    
    try:
        # Paso 1: Validar pregunta
        print("1. VALIDANDO PREGUNTA...")
        try:
            _validar_pregunta_es_sobre_bd(pregunta)
            print("✅ Pregunta válida (pasa validación)")
        except Exception as e:
            print(f"❌ Pregunta rechazada: {e}")
            return
        
        print()
        
        # Paso 2: Extraer cédula
        print("2. EXTRAYENDO CÉDULA...")
        cedula_extraida = _extraer_cedula_de_pregunta(pregunta)
        if cedula_extraida:
            print(f"✅ Cédula extraída: {cedula_extraida}")
        else:
            print("❌ No se pudo extraer cédula")
            return
        
        print()
        
        # Paso 3: Buscar cliente en BD
        print("3. BUSCANDO CLIENTE EN BASE DE DATOS...")
        print(f"   Buscando cédula: {cedula_extraida}")
        
        # Verificar si existe en BD
        from app.models.cliente import Cliente
        cliente = db.query(Cliente).filter(Cliente.cedula == cedula_extraida).first()
        
        if not cliente:
            print(f"   ⚠️ No encontrado con cédula exacta: {cedula_extraida}")
            
            # Intentar sin prefijo
            if cedula_extraida and cedula_extraida[0].upper() in ['V', 'E', 'J', 'Z']:
                cedula_sin_prefijo = cedula_extraida[1:]
                print(f"   Intentando sin prefijo: {cedula_sin_prefijo}")
                cliente = db.query(Cliente).filter(Cliente.cedula == cedula_sin_prefijo).first()
                if cliente:
                    print(f"   ✅ Encontrado sin prefijo: {cedula_sin_prefijo}")
                    cedula_extraida = cedula_sin_prefijo
        
        if cliente:
            print(f"✅ Cliente encontrado:")
            print(f"   Nombre: {cliente.nombres}")
            print(f"   Cédula: {cliente.cedula}")
            print(f"   Estado: {cliente.estado}")
        else:
            print("❌ Cliente NO encontrado en BD")
            print("   (Esto es normal si la cédula no existe en la BD)")
        
        print()
        
        # Paso 4: Obtener información completa
        print("4. OBTENIENDO INFORMACIÓN COMPLETA...")
        try:
            info_cliente = _obtener_info_cliente_por_cedula(cedula_extraida, db)
            print("✅ Información obtenida:")
            print("-" * 70)
            print(info_cliente[:500])  # Mostrar primeros 500 caracteres
            if len(info_cliente) > 500:
                print(f"... (total: {len(info_cliente)} caracteres)")
            print("-" * 70)
        except Exception as e:
            print(f"❌ Error obteniendo información: {e}")
            import traceback
            traceback.print_exc()
            return
        
        print()
        print("=" * 70)
        print("RESUMEN")
        print("=" * 70)
        print("✅ Validación de pregunta: OK")
        print("✅ Extracción de cédula: OK")
        print("✅ Búsqueda en BD: OK")
        print("✅ Información obtenida: OK")
        print()
        print("El flujo completo funciona correctamente.")
        print("Si el Chat AI no responde, el problema puede estar en:")
        print("  1. La llamada a OpenAI API")
        print("  2. El timeout de la respuesta")
        print("  3. El manejo de errores en el frontend")
        
    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()
