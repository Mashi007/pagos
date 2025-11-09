#!/usr/bin/env python3
"""
Script para generar el hash de una contraseña
Útil para crear scripts SQL directos
"""

import sys
import os

# Agregar el directorio del backend al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.security import get_password_hash

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python generar_hash_password.py <password>")
        print("\nEjemplo:")
        print("  python generar_hash_password.py Casa1803+")
        sys.exit(1)

    password = sys.argv[1]
    hashed = get_password_hash(password)

    print(f"\nContraseña: {password}")
    print(f"Hash: {hashed}\n")
    print("SQL para actualizar en la base de datos:")
    print("-" * 80)
    print("UPDATE users")
    print(f"SET hashed_password = '{hashed}',")
    print("    updated_at = NOW()")
    print("WHERE email = 'itmaster@rapicreditca.com';")
    print("-" * 80)
