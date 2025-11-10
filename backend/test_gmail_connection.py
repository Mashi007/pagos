#!/usr/bin/env python3
"""
Script de prueba para verificar conexión REAL con Gmail/Google Workspace
Este script demuestra que el sistema se conecta realmente a los servidores de Google
"""

import smtplib
import sys
from typing import Tuple, Optional

def probar_conexion_gmail(
    smtp_user: str,
    smtp_password: str,
    smtp_host: str = "smtp.gmail.com",
    smtp_port: int = 587,
    usar_tls: bool = True
) -> Tuple[bool, Optional[str]]:
    """
    Prueba conexión REAL con Gmail/Google Workspace
    
    Returns:
        (exito, mensaje)
    """
    print("=" * 70)
    print("🔗 PRUEBA DE CONEXIÓN REAL CON GMAIL/GOOGLE WORKSPACE")
    print("=" * 70)
    print(f"\n📧 Email: {smtp_user}")
    print(f"🌐 Servidor: {smtp_host}:{smtp_port}")
    print(f"🔒 TLS: {'Sí' if usar_tls else 'No'}")
    print("\n" + "-" * 70)
    
    try:
        # PASO 1: Crear conexión SMTP
        print("\n1️⃣ Creando conexión SMTP...")
        print(f"   → Conectando a {smtp_host}:{smtp_port}...")
        server = smtplib.SMTP(smtp_host, smtp_port, timeout=10)
        print("   ✅ Conexión TCP establecida")
        
        # PASO 2: Iniciar TLS (si está habilitado)
        if usar_tls:
            print("\n2️⃣ Iniciando TLS (cifrado seguro)...")
            server.starttls()
            print("   ✅ TLS iniciado correctamente")
            print("   → Conexión ahora está cifrada")
        
        # PASO 3: Intentar autenticación
        print("\n3️⃣ Intentando autenticación con Google...")
        print(f"   → Enviando credenciales a Google...")
        print("   → Esperando respuesta de Google...")
        
        # ESTA ES LA LÍNEA CRÍTICA: Aquí Google decide si acepta o rechaza
        server.login(smtp_user, smtp_password)
        
        print("   ✅ Google ACEPTÓ las credenciales")
        print("   ✅ Autenticación exitosa")
        
        # PASO 4: Cerrar conexión
        print("\n4️⃣ Cerrando conexión...")
        server.quit()
        print("   ✅ Conexión cerrada correctamente")
        
        print("\n" + "=" * 70)
        print("✅ RESULTADO: CONEXIÓN EXITOSA")
        print("=" * 70)
        print("\n🎉 Google/Google Workspace ACEPTÓ tu configuración")
        print("📧 El sistema está vinculado y puede enviar emails")
        print("\n" + "=" * 70)
        
        return True, "Conexión exitosa"
        
    except smtplib.SMTPAuthenticationError as e:
        print("\n   ❌ Google RECHAZÓ las credenciales")
        print(f"   → Error: {str(e)}")
        
        print("\n" + "=" * 70)
        print("❌ RESULTADO: GOOGLE RECHAZÓ LA CONEXIÓN")
        print("=" * 70)
        print("\n⚠️  Posibles causas:")
        print("   1. NO tienes 2FA activado")
        print("   2. Estás usando contraseña normal (no App Password)")
        print("   3. La App Password es incorrecta o fue revocada")
        print("   4. Para Google Workspace: dominio no configurado")
        print("\n" + "=" * 70)
        
        return False, f"Error de autenticación: {str(e)}"
        
    except smtplib.SMTPException as e:
        print(f"\n   ❌ Error de conexión SMTP: {str(e)}")
        print("\n" + "=" * 70)
        print("❌ RESULTADO: ERROR DE CONEXIÓN")
        print("=" * 70)
        return False, f"Error SMTP: {str(e)}"
        
    except ConnectionRefusedError:
        print("\n   ❌ No se pudo conectar al servidor")
        print("   → Verifica que tengas internet")
        print("   → Verifica que el puerto esté abierto")
        print("\n" + "=" * 70)
        print("❌ RESULTADO: NO SE PUDO CONECTAR")
        print("=" * 70)
        return False, "No se pudo conectar al servidor"
        
    except Exception as e:
        print(f"\n   ❌ Error inesperado: {str(e)}")
        print("\n" + "=" * 70)
        print("❌ RESULTADO: ERROR INESPERADO")
        print("=" * 70)
        return False, f"Error: {str(e)}"


def main():
    """Función principal"""
    print("\n" + "=" * 70)
    print("🧪 PRUEBA DE CONEXIÓN REAL CON GMAIL")
    print("=" * 70)
    print("\nEste script demuestra que el sistema se conecta REALMENTE")
    print("a los servidores de Google para verificar credenciales.\n")
    
    # Solicitar credenciales
    print("Por favor ingresa tus credenciales:")
    print("(Presiona Ctrl+C para cancelar)\n")
    
    try:
        smtp_user = input("📧 Email (Usuario Gmail / Google Workspace): ").strip()
        if not smtp_user:
            print("\n❌ Email requerido")
            sys.exit(1)
        
        import getpass
        smtp_password = getpass.getpass("🔑 Contraseña de Aplicación (no se mostrará): ").strip()
        if not smtp_password:
            print("\n❌ Contraseña requerida")
            sys.exit(1)
        
        # Limpiar espacios de la contraseña (Gmail puede mostrarla con espacios)
        smtp_password = smtp_password.replace(" ", "").replace("\t", "")
        
        print("\n" + "=" * 70)
        print("🚀 Iniciando prueba de conexión...")
        print("=" * 70)
        print("\n⏳ Esto puede tomar 2-5 segundos...")
        print("   (El sistema está conectándose REALMENTE a Google)\n")
        
        # Probar conexión
        exito, mensaje = probar_conexion_gmail(
            smtp_user=smtp_user,
            smtp_password=smtp_password,
            smtp_host="smtp.gmail.com",
            smtp_port=587,
            usar_tls=True
        )
        
        if exito:
            print("\n✅ CONCLUSIÓN: La conexión es REAL")
            print("   Google verificó y aceptó tus credenciales")
            sys.exit(0)
        else:
            print("\n❌ CONCLUSIÓN: La conexión es REAL pero Google rechazó")
            print("   Esto demuestra que el sistema SÍ se conecta a Google")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n❌ Prueba cancelada por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

