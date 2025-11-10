#!/usr/bin/env python3
"""
Versión SIMPLE del script de prueba
Úsalo para probar rápidamente la conexión
"""

import smtplib

# CONFIGURA ESTOS VALORES:
SMTP_USER = "tu_email@rapicreditca.com"  # Cambia esto
SMTP_PASSWORD = "tu_app_password"  # Cambia esto

print("🔗 Probando conexión REAL con Gmail...")
print(f"📧 Email: {SMTP_USER}")
print("\n⏳ Conectando a smtp.gmail.com:587...")

try:
    # PASO 1: Conectar
    server = smtplib.SMTP('smtp.gmail.com', 587, timeout=10)
    print("✅ Conexión TCP establecida")
    
    # PASO 2: TLS
    server.starttls()
    print("✅ TLS iniciado")
    
    # PASO 3: Autenticar (AQUÍ Google decide)
    print("🔐 Autenticando con Google...")
    server.login(SMTP_USER, SMTP_PASSWORD)
    print("✅ Google ACEPTÓ las credenciales")
    
    # PASO 4: Cerrar
    server.quit()
    print("✅ Conexión cerrada")
    
    print("\n" + "="*50)
    print("✅ ÉXITO: Google aceptó la conexión")
    print("="*50)
    
except smtplib.SMTPAuthenticationError as e:
    print(f"\n❌ Google RECHAZÓ: {e}")
    print("\nEsto demuestra que SÍ se conectó a Google")
    print("(Google rechazó porque las credenciales son incorrectas)")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\nEsto demuestra que SÍ intentó conectarse a Google")

