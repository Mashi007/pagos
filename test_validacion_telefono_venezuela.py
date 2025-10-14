#!/usr/bin/env python3
"""
Test para validar la nueva configuración de teléfonos venezolanos
Formato: +58 + 10 dígitos (primer dígito no puede ser 0)
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.validators_service import ValidadorTelefono

def test_telefonos_validos():
    """Test de teléfonos válidos"""
    print("🧪 TESTING TELÉFONOS VÁLIDOS")
    print("=" * 50)
    
    casos_validos = [
        ("1234567890", "10 dígitos sin prefijo"),
        ("581234567890", "58 + 10 dígitos"),
        ("+581234567890", "+58 + 10 dígitos completo"),
        ("4241234567", "10 dígitos locales"),
        ("4141234567", "10 dígitos locales"),
        ("4161234567", "10 dígitos locales"),
    ]
    
    for telefono, descripcion in casos_validos:
        resultado = ValidadorTelefono.validar_y_formatear_telefono(telefono, "VENEZUELA")
        estado = "✅ VÁLIDO" if resultado["valido"] else "❌ INVÁLIDO"
        print(f"{estado} {telefono:15} ({descripcion})")
        if resultado["valido"]:
            print(f"    Formateado: {resultado['valor_formateado']}")
        else:
            print(f"    Error: {resultado['error']}")

def test_telefonos_invalidos():
    """Test de teléfonos inválidos"""
    print("\n🚫 TESTING TELÉFONOS INVÁLIDOS")
    print("=" * 50)
    
    casos_invalidos = [
        ("0123456789", "Empieza por 0"),
        ("5810123456789", "58 + número que empieza por 0"),
        ("+580123456789", "+58 + número que empieza por 0"),
        ("123456789", "9 dígitos (muy corto)"),
        ("12345678901", "11 dígitos (muy largo)"),
        ("58123456789", "58 + 9 dígitos"),
        ("+58123456789", "+58 + 9 dígitos"),
        ("5812345678901", "58 + 11 dígitos"),
        ("+5812345678901", "+58 + 11 dígitos"),
        ("", "Vacío"),
        ("abc1234567890", "Contiene letras"),
        ("+591234567890", "Código de país incorrecto"),
    ]
    
    for telefono, descripcion in casos_invalidos:
        resultado = ValidadorTelefono.validar_y_formatear_telefono(telefono, "VENEZUELA")
        estado = "✅ VÁLIDO" if resultado["valido"] else "❌ INVÁLIDO"
        print(f"{estado} {telefono:15} ({descripcion})")
        if resultado["valido"]:
            print(f"    ⚠️  Debería ser inválido pero fue aceptado!")
        else:
            print(f"    Error: {resultado['error']}")

def test_formateo():
    """Test de formateo automático"""
    print("\n🔄 TESTING FORMATEO AUTOMÁTICO")
    print("=" * 50)
    
    casos_formateo = [
        ("1234567890", "Debe agregar +58"),
        ("581234567890", "Debe agregar +"),
        ("+581234567890", "Ya está correcto"),
        ("58-123-456-7890", "Debe limpiar guiones"),
        ("58 123 456 7890", "Debe limpiar espacios"),
    ]
    
    for telefono, descripcion in casos_formateo:
        resultado = ValidadorTelefono.validar_y_formatear_telefono(telefono, "VENEZUELA")
        if resultado["valido"]:
            print(f"✅ {telefono:15} → {resultado['valor_formateado']} ({descripcion})")
            if resultado.get("cambio_realizado"):
                print(f"    Cambio realizado: {resultado['valor_original']} → {resultado['valor_formateado']}")
        else:
            print(f"❌ {telefono:15} ({descripcion}) - Error: {resultado['error']}")

def test_requisitos_especificos():
    """Test de requisitos específicos"""
    print("\n📋 TESTING REQUISITOS ESPECÍFICOS")
    print("=" * 50)
    
    requisitos = [
        ("1234567890", "Empieza por +58", "✓"),
        ("1234567890", "10 dígitos total", "✓"),
        ("1234567890", "Primer dígito no es 0", "✓"),
        ("0123456789", "Primer dígito no es 0", "✗"),
        ("123456789", "10 dígitos total", "✗"),
    ]
    
    for telefono, requisito, esperado in requisitos:
        resultado = ValidadorTelefono.validar_y_formatear_telefono(telefono, "VENEZUELA")
        if resultado["valido"]:
            cumplidos = resultado.get("requisitos_cumplidos", {})
            estado = "✅" if esperado == "✓" else "❌"
            print(f"{estado} {telefono:12} - {requisito}: {estado}")
        else:
            print(f"❌ {telefono:12} - {requisito}: Error - {resultado['error']}")

if __name__ == "__main__":
    print("🇻🇪 TEST DE VALIDACIÓN DE TELÉFONOS VENEZOLANOS")
    print("Nuevos requisitos: +58 + 10 dígitos (primer dígito no puede ser 0)")
    print("=" * 70)
    
    test_telefonos_validos()
    test_telefonos_invalidos()
    test_formateo()
    test_requisitos_especificos()
    
    print("\n" + "=" * 70)
    print("🏁 TEST COMPLETADO")
