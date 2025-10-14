#!/usr/bin/env python3
"""
Test para validar la nueva configuración de cédulas venezolanas
Prefijos: V, E, J
Longitud: 7-10 dígitos
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.validators_service import ValidadorCedula

def test_cedulas_validas():
    """Test de cédulas válidas"""
    print("🧪 TESTING CÉDULAS VÁLIDAS")
    print("=" * 50)
    
    casos_validos = [
        ("1234567", "7 dígitos sin prefijo"),
        ("12345678", "8 dígitos sin prefijo"),
        ("123456789", "9 dígitos sin prefijo"),
        ("1234567890", "10 dígitos sin prefijo"),
        ("V1234567", "V + 7 dígitos"),
        ("V12345678", "V + 8 dígitos"),
        ("V123456789", "V + 9 dígitos"),
        ("V1234567890", "V + 10 dígitos"),
        ("E1234567", "E + 7 dígitos"),
        ("E12345678", "E + 8 dígitos"),
        ("E123456789", "E + 9 dígitos"),
        ("E1234567890", "E + 10 dígitos"),
        ("J1234567", "J + 7 dígitos"),
        ("J12345678", "J + 8 dígitos"),
        ("J123456789", "J + 9 dígitos"),
        ("J1234567890", "J + 10 dígitos"),
    ]
    
    for cedula, descripcion in casos_validos:
        resultado = ValidadorCedula.validar_y_formatear_cedula(cedula, "VENEZUELA")
        estado = "✅ VÁLIDA" if resultado["valido"] else "❌ INVÁLIDA"
        print(f"{estado} {cedula:12} ({descripcion})")
        if not resultado["valido"]:
            print(f"    Error: {resultado['error']}")

def test_cedulas_invalidas():
    """Test de cédulas inválidas"""
    print("\n🚫 TESTING CÉDULAS INVÁLIDAS")
    print("=" * 50)
    
    casos_invalidos = [
        ("123456", "6 dígitos (muy corto)"),
        ("12345678901", "11 dígitos (muy largo)"),
        ("G12345678", "Prefijo G no válido"),
        ("A12345678", "Prefijo A no válido"),
        ("V123456a", "Contiene letra en dígitos"),
        ("V123456@", "Contiene símbolo en dígitos"),
        ("", "Vacía"),
        ("V", "Solo prefijo"),
        ("12345ab", "Mezcla de números y letras"),
    ]
    
    for cedula, descripcion in casos_invalidos:
        resultado = ValidadorCedula.validar_y_formatear_cedula(cedula, "VENEZUELA")
        estado = "✅ VÁLIDA" if resultado["valido"] else "❌ INVÁLIDA"
        print(f"{estado} {cedula:12} ({descripcion})")
        if resultado["valido"]:
            print(f"    ⚠️  Debería ser inválida pero fue aceptada!")
        else:
            print(f"    Error: {resultado['error']}")

def test_formateo():
    """Test de formateo automático"""
    print("\n🔄 TESTING FORMATEO AUTOMÁTICO")
    print("=" * 50)
    
    casos_formateo = [
        ("1234567", "Debe agregar prefijo V"),
        ("v1234567", "Debe convertir a mayúscula"),
        ("V-1234567", "Debe quitar guión"),
        ("V 1234567", "Debe quitar espacio"),
        ("V_1234567", "Debe quitar guión bajo"),
    ]
    
    for cedula, descripcion in casos_formateo:
        resultado = ValidadorCedula.validar_y_formatear_cedula(cedula, "VENEZUELA")
        if resultado["valido"]:
            print(f"✅ {cedula:12} → {resultado['valor_formateado']} ({descripcion})")
            if resultado.get("cambio_realizado"):
                print(f"    Cambio realizado: {resultado['valor_original']} → {resultado['valor_formateado']}")
        else:
            print(f"❌ {cedula:12} ({descripcion}) - Error: {resultado['error']}")

def test_tipos_cedula():
    """Test de tipos de cédula"""
    print("\n🏷️  TESTING TIPOS DE CÉDULA")
    print("=" * 50)
    
    tipos = [
        ("V12345678", "Venezolano"),
        ("E12345678", "Extranjero"),
        ("J12345678", "Jurídico"),
    ]
    
    for cedula, tipo_esperado in tipos:
        resultado = ValidadorCedula.validar_y_formatear_cedula(cedula, "VENEZUELA")
        if resultado["valido"]:
            tipo_real = resultado.get("tipo", "Desconocido")
            estado = "✅" if tipo_real == tipo_esperado else "❌"
            print(f"{estado} {cedula} → Tipo: {tipo_real} (esperado: {tipo_esperado})")
        else:
            print(f"❌ {cedula} - Error: {resultado['error']}")

if __name__ == "__main__":
    print("🇻🇪 TEST DE VALIDACIÓN DE CÉDULAS VENEZOLANAS")
    print("Nuevos requisitos: V/E/J + 7-10 dígitos del 0-9")
    print("=" * 60)
    
    test_cedulas_validas()
    test_cedulas_invalidas()
    test_formateo()
    test_tipos_cedula()
    
    print("\n" + "=" * 60)
    print("🏁 TEST COMPLETADO")
