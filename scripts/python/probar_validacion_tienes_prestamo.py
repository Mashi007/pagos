#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para probar que la validación acepta preguntas como "Tienes prestamo V123456789"
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

from app.api.v1.endpoints.configuracion import _validar_pregunta_es_sobre_bd

def main():
    """Función principal"""
    print("=" * 70)
    print("PRUEBA DE VALIDACIÓN: PREGUNTAS CON 'TIENES PRESTAMO'")
    print("=" * 70)
    print()
    
    # Casos de prueba específicos
    casos_prueba = [
        ("Tienes prestamo V123456789", True, "Pregunta específica del usuario"),
        ("tienes prestamo v123456789", True, "Minúsculas"),
        ("Tiene prestamo V123456789", True, "Singular"),
        ("Tienes prestamo", True, "Sin cédula pero con palabra clave"),
        ("Tienes cliente V123456789", True, "Con cliente"),
        ("Tienes pago V123456789", True, "Con pago"),
        ("Tienes cuota V123456789", True, "Con cuota"),
        ("Tienes prestamo?", True, "Con signo de interrogación"),
        ("¿Tienes prestamo V123456789?", True, "Con signos de interrogación"),
    ]
    
    print("Probando preguntas que DEBEN ser VÁLIDAS:\n")
    todas_ok = True
    
    for pregunta, esperado, descripcion in casos_prueba:
        try:
            _validar_pregunta_es_sobre_bd(pregunta)
            resultado = True
            estado = "✅" if resultado == esperado else "❌"
            print(f"{estado} '{pregunta}'")
            print(f"   Descripción: {descripcion}")
            print(f"   Resultado: VÁLIDA (esperado: {'VÁLIDA' if esperado else 'RECHAZADA'})")
            if resultado != esperado:
                todas_ok = False
        except Exception as e:
            resultado = False
            estado = "❌" if resultado == esperado else "✅"
            print(f"{estado} '{pregunta}'")
            print(f"   Descripción: {descripcion}")
            print(f"   Resultado: RECHAZADA - {e}")
            if resultado != esperado:
                todas_ok = False
        print()
    
    print("=" * 70)
    if todas_ok:
        print("✅ TODAS LAS PRUEBAS PASARON")
        print("La validación acepta correctamente preguntas con 'tienes prestamo'")
        return 0
    else:
        print("❌ ALGUNAS PRUEBAS FALLARON")
        print("Revisa los resultados arriba")
        return 1

if __name__ == "__main__":
    sys.exit(main())
