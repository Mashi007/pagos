#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script rápido de prueba de conexión con Gmail
Uso: py test_gmail_quick.py email password
"""

import smtplib
import sys
import io

# Configurar UTF-8 para Windows
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def main():
    if len(sys.argv) < 3:
        print("Uso: py test_gmail_quick.py <email> <password>")
        print("Ejemplo: py test_gmail_quick.py itmaster@rapicreditca.com R@pi_2025**")
        sys.exit(1)
    
    email = sys.argv[1]
    password = sys.argv[2].replace(" ", "").replace("\t", "")
    
    print("=" * 70)
    print("PRUEBA DE CONEXION REAL CON GMAIL")
    print("=" * 70)
    print(f"\nEmail: {email}")
    print(f"Servidor: smtp.gmail.com:587")
    print("\n" + "-" * 70)
    print("\n1. Creando conexion SMTP...")
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587, timeout=10)
        print("   [OK] Conexion TCP establecida")
        
        print("\n2. Iniciando TLS...")
        server.starttls()
        print("   [OK] TLS iniciado correctamente")
        
        print("\n3. Autenticando con Google...")
        print("   -> Enviando credenciales a Google...")
        server.login(email, password)
        print("   [OK] Google ACEPTO las credenciales")
        
        print("\n4. Cerrando conexion...")
        server.quit()
        print("   [OK] Conexion cerrada")
        
        print("\n" + "=" * 70)
        print("RESULTADO: CONEXION EXITOSA")
        print("=" * 70)
        print("\nGoogle/Google Workspace ACEPTO tu configuracion")
        print("El sistema esta vinculado y puede enviar emails")
        print("\n" + "=" * 70)
        return 0
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"\n   [ERROR] Google RECHAZO las credenciales")
        print(f"   Error: {str(e)}")
        print("\n" + "=" * 70)
        print("RESULTADO: GOOGLE RECHAZO LA CONEXION")
        print("=" * 70)
        print("\nEsto demuestra que SI se conecto a Google")
        print("(Google rechazo porque las credenciales son incorrectas)")
        print("\nPosibles causas:")
        print("  1. NO tienes 2FA activado")
        print("  2. Estás usando contraseña normal (no App Password)")
        print("  3. La App Password es incorrecta o fue revocada")
        return 1
        
    except Exception as e:
        print(f"\n   [ERROR] {str(e)}")
        print("\n" + "=" * 70)
        print("RESULTADO: ERROR DE CONEXION")
        print("=" * 70)
        print("\nEsto demuestra que SI intento conectarse a Google")
        return 1

if __name__ == "__main__":
    sys.exit(main())

