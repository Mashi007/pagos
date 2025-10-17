#!/usr/bin/env python3
"""
Script de prueba para verificar validate_password_strength
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.validators import validate_password_strength

def test_password_validation():
    """Probar la función de validación de contraseñas"""
    
    test_cases = [
        ("", False, "Contraseña vacía"),
        ("123", False, "Muy corta"),
        ("password", False, "Sin mayúscula ni número"),
        ("PASSWORD", False, "Sin minúscula ni número"),
        ("Password", False, "Sin número ni especial"),
        ("Password1", False, "Sin carácter especial"),
        ("Password1!", True, "Contraseña válida"),
        ("R@pi_2025**", True, "Contraseña válida compleja"),
        ("12345678", False, "Solo números"),
        ("abcdefgh", False, "Solo letras"),
        ("Password 1!", False, "Con espacio"),
        ("aaaPassword1!", False, "Caracteres repetidos"),
    ]
    
    print("🔐 PRUEBAS DE VALIDACIÓN DE CONTRASEÑAS")
    print("=" * 50)
    
    for password, expected, description in test_cases:
        is_valid, message = validate_password_strength(password)
        status = "✅" if is_valid == expected else "❌"
        
        print(f"{status} {description}")
        print(f"   Contraseña: '{password}'")
        print(f"   Esperado: {expected}, Obtenido: {is_valid}")
        if not is_valid:
            print(f"   Mensaje: {message}")
        print()

if __name__ == "__main__":
    test_password_validation()
