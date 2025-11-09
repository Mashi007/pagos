#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script simple para generar hash de contraseña usando bcrypt directamente
"""

import sys
import os
import bcrypt

# Agregar el directorio del backend al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python generar_hash_simple.py <password>")
        print("\nEjemplo:")
        print("  python generar_hash_simple.py Casa1803+")
        sys.exit(1)

    password = sys.argv[1]

    # Generar hash usando bcrypt directamente
    # bcrypt requiere bytes, no string
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    hashed_str = hashed.decode('utf-8')

    print("\n" + "=" * 80)
    print("HASH GENERADO")
    print("=" * 80)
    print(f"\nContrasena: {password}")
    print(f"Hash: {hashed_str}\n")
    print("=" * 80)
    print("SQL PARA EJECUTAR EN LA BASE DE DATOS:")
    print("=" * 80)
    print(f"\nUPDATE users")
    print(f"SET hashed_password = '{hashed_str}',")
    print(f"    updated_at = NOW()")
    print(f"WHERE email = 'itmaster@rapicreditca.com';")
    print("\nCOMMIT;")
    print("=" * 80)
