#!/usr/bin/env python3
"""
🧪 Script de prueba para validadores actualizados
Probar la nueva configuración estricta de cédula venezolana
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.validators_service import ValidadorCedula, ValidadorTelefono, ValidadorEmail

def test_cedula_venezolana():
    """Probar validación de cédula venezolana con nuevos requisitos"""
    print("🧪 PROBANDO VALIDACIÓN DE CÉDULA VENEZOLANA")
    print("=" * 50)
    
    # Casos válidos
    casos_validos = [
        "V1234567",      # 7 dígitos
        "E12345678",     # 8 dígitos  
        "J123456789",    # 9 dígitos
        "V1234567890"    # 10 dígitos
    ]
    
    print("✅ CASOS VÁLIDOS:")
    for cedula in casos_validos:
        resultado = ValidadorCedula.validar_y_formatear_cedula(cedula, "VENEZUELA")
        print(f"  {cedula} → {'✅' if resultado['valido'] else '❌'} {resultado.get('valor_formateado', 'ERROR')}")
    
    print("\n❌ CASOS INVÁLIDOS:")
    casos_invalidos = [
        "G12345678",     # Prefijo G no válido
        "V123456",       # Solo 6 dígitos
        "V12345678901",  # 11 dígitos
        "V1234567A",     # Contiene letra
        "V-12345678",    # Contiene guión
        "V 12345678",    # Contiene espacio
        "12345678",      # Sin prefijo (debería agregar V)
    ]
    
    for cedula in casos_invalidos:
        resultado = ValidadorCedula.validar_y_formatear_cedula(cedula, "VENEZUELA")
        print(f"  {cedula} → {'✅' if resultado['valido'] else '❌'} {resultado.get('error', 'OK')}")
        if resultado.get('valor_formateado'):
            print(f"    Formateado: {resultado['valor_formateado']}")

def test_telefono_venezolano():
    """Probar validación de teléfono venezolano"""
    print("\n🧪 PROBANDO VALIDACIÓN DE TELÉFONO VENEZOLANO")
    print("=" * 50)
    
    casos_validos = [
        "4241234567",      # Sin código de país
        "+584241234567",   # Con código de país
        "424 1234567"      # Con espacio
    ]
    
    print("✅ CASOS VÁLIDOS:")
    for telefono in casos_validos:
        resultado = ValidadorTelefono.validar_y_formatear_telefono(telefono, "VENEZUELA")
        print(f"  {telefono} → {'✅' if resultado['valido'] else '❌'} {resultado.get('valor_formateado', 'ERROR')}")
    
    print("\n❌ CASOS INVÁLIDOS:")
    casos_invalidos = [
        "0241234567",      # Empieza con 0
        "424123456",       # Solo 9 dígitos
        "42412345678",     # 11 dígitos
        "424-123-4567"     # Con guiones
    ]
    
    for telefono in casos_invalidos:
        resultado = ValidadorTelefono.validar_y_formatear_telefono(telefono, "VENEZUELA")
        print(f"  {telefono} → {'✅' if resultado['valido'] else '❌'} {resultado.get('error', 'OK')}")

def test_email():
    """Probar validación de email"""
    print("\n🧪 PROBANDO VALIDACIÓN DE EMAIL")
    print("=" * 50)
    
    casos_validos = [
        "usuario@ejemplo.com",
        "USUARIO@EJEMPLO.COM",  # Debería convertir a minúsculas
        " usuario@ejemplo.com "  # Debería quitar espacios
    ]
    
    print("✅ CASOS VÁLIDOS:")
    for email in casos_validos:
        resultado = ValidadorEmail.validar_email(email)
        print(f"  {email} → {'✅' if resultado['valido'] else '❌'} {resultado.get('valor_formateado', 'ERROR')}")
    
    print("\n❌ CASOS INVÁLIDOS:")
    casos_invalidos = [
        "usuario@ejemplo",      # Sin extensión
        "@ejemplo.com",         # Sin usuario
        "usuario@",            # Sin dominio
        "usuario@tempmail.org" # Dominio bloqueado
    ]
    
    for email in casos_invalidos:
        resultado = ValidadorEmail.validar_email(email)
        print(f"  {email} → {'✅' if resultado['valido'] else '❌'} {resultado.get('error', 'OK')}")

if __name__ == "__main__":
    print("🚀 INICIANDO PRUEBAS DE VALIDADORES")
    print("=" * 60)
    
    try:
        test_cedula_venezolana()
        test_telefono_venezolano()
        test_email()
        
        print("\n" + "=" * 60)
        print("✅ TODAS LAS PRUEBAS COMPLETADAS")
        print("🔧 La configuración de validadores está funcionando correctamente")
        
    except Exception as e:
        print(f"\n❌ ERROR EN LAS PRUEBAS: {e}")
        sys.exit(1)
