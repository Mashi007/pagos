#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para probar la función de extracción de cédula del Chat AI
"""

import sys
import io
import re
from pathlib import Path

# Configurar encoding para Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Agregar backend al path para imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

def _extraer_cedula_de_pregunta(pregunta: str):
    """
    Extrae cédula/documento de la pregunta usando regex.
    Retorna la cédula encontrada o None.
    
    Mejorado para capturar:
    - Cédulas con prefijo (V, E, J, Z) en mayúsculas o minúsculas
    - Cédulas después de palabras como "cedula", "tienen", "con", etc.
    - Formato flexible: "cedula v123456789" o "cedula: v123456789"
    """
    # Patrón mejorado: captura cédulas con prefijo V/E/J/Z (mayúsculas o minúsculas) seguido de números
    # También captura solo números si no hay prefijo
    patrones = [
        # Patrón 1: "cedula/cédula/documento" seguido de espacios/":" y luego la cédula (con o sin prefijo)
        # Captura: "cedula v123456789" -> "v123456789"
        r"(?:cedula|cédula|documento|dni|ci)[\s:]+([vVeEjJzZ]\d{7,10}|\d{7,10})",
        # Patrón 2: "tienen/con" seguido de "cedula" y luego la cédula
        # Captura: "tienen cedula v123456789" -> "v123456789"
        r"(?:tienen|con|tiene)[\s]+(?:cedula|cédula|documento)[\s]+([vVeEjJzZ]\d{7,10}|\d{7,10})",
        # Patrón 3: Buscar directamente cédulas venezolanas (V/E/J/Z seguido de números)
        # Captura: "v123456789" -> "v123456789"
        r"\b([vVeEjJzZ]\d{7,10})\b",
        # Patrón 4: Buscar cédulas después de "que tiene" o "que tienen"
        # Captura: "que tiene cedula v123456789" -> "v123456789"
        r"(?:que\s+)?(?:tiene|tienen)[\s]+(?:cedula|cédula|documento)[\s]+([vVeEjJzZ]\d{7,10}|\d{7,10})",
    ]
    
    for patron in patrones:
        match_cedula = re.search(patron, pregunta, re.IGNORECASE)
        if match_cedula:
            cedula = match_cedula.group(1).strip()
            # Normalizar: convertir a mayúsculas el prefijo si existe
            if cedula and len(cedula) > 0 and cedula[0].lower() in ['v', 'e', 'j', 'z']:
                cedula = cedula[0].upper() + cedula[1:]
            print(f"✅ Cédula detectada con patrón '{patron}': {cedula}")
            return cedula
    
    print("❌ No se detectó cédula")
    return None

def main():
    """Función principal"""
    print("=" * 70)
    print("PRUEBA DE EXTRACCIÓN DE CÉDULA")
    print("=" * 70)
    print()
    
    # Casos de prueba
    casos_prueba = [
        "CUAL ES EL NOMBRE QUE TIENEN CEDULA v123456789",
        "DIME COMO SE LLAMA EL CLIENTE QUE TIENE CEDULA v123456789",
        "¿Cuál es el nombre del cliente con cédula V123456789?",
        "Buscar cliente cedula: v123456789",
        "Cliente con documento v123456789",
        "v123456789",
        "cedula v123456789",
        "que tiene cedula v123456789",
    ]
    
    for i, pregunta in enumerate(casos_prueba, 1):
        print(f"\n[{i}] Pregunta: {pregunta}")
        print("-" * 70)
        resultado = _extraer_cedula_de_pregunta(pregunta)
        if resultado:
            print(f"✅ Resultado: {resultado}")
        else:
            print("❌ No se detectó cédula")
    
    print("\n" + "=" * 70)
    print("PRUEBA COMPLETADA")
    print("=" * 70)

if __name__ == "__main__":
    main()
