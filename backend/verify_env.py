#!/usr/bin/env python3
"""
Script de Verificación de Variables de Entorno
Sistema de Préstamos y Cobranza

Uso:
    python verify_env.py
    python verify_env.py --env production
"""
import os
import sys
from typing import Dict, List, Tuple
from dotenv import load_dotenv


class Colors:
    """Colores para terminal"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_colored(text: str, color: str):
    """Imprime texto con color"""
    print(f"{color}{text}{Colors.END}")


def mask_value(value: str, show_chars: int = 8) -> str:
    """Enmascara valores sensibles"""
    if not value:
        return "NO CONFIGURADA"
    
    if len(value) <= show_chars:
        return "*" * len(value)
    
    return value[:show_chars] + "..." + ("*" * 10)


def check_variables() -> Tuple[Dict[str, bool], Dict[str, bool]]:
    """
    Verifica variables de entorno
    
    Returns:
        Tuple con (required_status, optional_status)
    """
    # Variables REQUERIDAS
    required_vars = {
        "SECRET_KEY": "Clave secreta para JWT (mínimo 32 caracteres)",
        "DATABASE_URL": "URL de conexión a PostgreSQL",
        "ALLOWED_ORIGINS": "Orígenes permitidos para CORS",
        "ENVIRONMENT": "Ambiente (development/staging/production)",
    }
    
    # Variables RECOMENDADAS
    recommended_vars = {
        "SENTRY_DSN": "Error tracking con Sentry",
        "PROMETHEUS_ENABLED": "Métricas de Prometheus",
        "LOG_LEVEL": "Nivel de logging",
        "APP_VERSION": "Versión de la aplicación",
    }
    
    # Variables OPCIONALES
    optional_vars = {
        "REDIS_URL": "Cache con Redis",
        "SMTP_HOST": "Servidor SMTP para emails",
        "SMTP_USER": "Usuario SMTP",
        "SMTP_PASSWORD": "Password SMTP",
        "TWILIO_ACCOUNT_SID": "Twilio para SMS",
        "TWILIO_AUTH_TOKEN": "Token de Twilio",
    }
    
    print_colored("\n" + "="*60, Colors.BLUE)
    print_colored("🔍 VERIFICACIÓN DE VARIABLES DE ENTORNO", Colors.BOLD + Colors.BLUE)
    print_colored("="*60 + "\n", Colors.BLUE)
    
    # Verificar REQUERIDAS
    print_colored("✅ VARIABLES REQUERIDAS:", Colors.BOLD + Colors.GREEN)
    print_colored("-" * 60, Colors.GREEN)
    
    required_status = {}
    all_required_ok = True
    
    for var, description in required_vars.items():
        value = os.getenv(var)
        is_set = bool(value)
        required_status[var] = is_set
        
        if is_set:
            # Validaciones adicionales
            if var == "SECRET_KEY" and len(value) < 32:
                print_colored(f"  ⚠️  {var}", Colors.YELLOW)
                print_colored(f"      → {description}", Colors.YELLOW)
                print_colored(f"      → ADVERTENCIA: Menos de 32 caracteres", Colors.YELLOW)
                all_required_ok = False
            else:
                masked = mask_value(value)
                print_colored(f"  ✅ {var}: {masked}", Colors.GREEN)
                print_colored(f"      → {description}", Colors.GREEN)
        else:
            print_colored(f"  ❌ {var}: NO CONFIGURADA", Colors.RED)
            print_colored(f"      → {description}", Colors.RED)
            all_required_ok = False
    
    # Verificar RECOMENDADAS
    print_colored("\n⚙️  VARIABLES RECOMENDADAS:", Colors.BOLD + Colors.YELLOW)
    print_colored("-" * 60, Colors.YELLOW)
    
    for var, description in recommended_vars.items():
        value = os.getenv(var)
        is_set = bool(value)
        
        if is_set:
            masked = mask_value(value)
            print_colored(f"  ✅ {var}: {masked}", Colors.GREEN)
        else:
            print_colored(f"  ⚠️  {var}: No configurada", Colors.YELLOW)
        
        print_colored(f"      → {description}", Colors.YELLOW)
    
    # Verificar OPCIONALES
    print_colored("\n🔧 VARIABLES OPCIONALES:", Colors.BOLD + Colors.BLUE)
    print_colored("-" * 60, Colors.BLUE)
    
    optional_status = {}
    
    for var, description in optional_vars.items():
        value = os.getenv(var)
        is_set = bool(value)
        optional_status[var] = is_set
        
        status_icon = "✅" if is_set else "⚪"
        status_text = "Configurada" if is_set else "No configurada"
        
        print(f"  {status_icon} {var}: {status_text}")
        print(f"      → {description}")
    
    # Resumen
    print_colored("\n" + "="*60, Colors.BLUE)
    print_colored("📊 RESUMEN", Colors.BOLD + Colors.BLUE)
    print_colored("="*60, Colors.BLUE)
    
    required_count = sum(required_status.values())
    required_total = len(required_status)
    recommended_count = sum(1 for var in recommended_vars if os.getenv(var))
    recommended_total = len(recommended_vars)
    optional_count = sum(optional_status.values())
    optional_total = len(optional_status)
    
    print(f"\n  Requeridas:    {required_count}/{required_total}")
    print(f"  Recomendadas:  {recommended_count}/{recommended_total}")
    print(f"  Opcionales:    {optional_count}/{optional_total}")
    
    if all_required_ok:
        print_colored("\n✅ Todas las variables requeridas están configuradas correctamente", Colors.GREEN)
    else:
        print_colored("\n❌ Hay variables requeridas sin configurar o con problemas", Colors.RED)
    
    # Validaciones adicionales
    print_colored("\n🔍 VALIDACIONES ADICIONALES:", Colors.BOLD + Colors.BLUE)
    print_colored("-" * 60, Colors.BLUE)
    
    validations_ok = True
    
    # Validar SECRET_KEY
    secret_key = os.getenv("SECRET_KEY")
    if secret_key:
        if len(secret_key) < 32:
            print_colored("  ❌ SECRET_KEY debe tener al menos 32 caracteres", Colors.RED)
            validations_ok = False
        elif secret_key == "your-secret-key-here-change-this-in-production":
            print_colored("  ⚠️  SECRET_KEY usa el valor por defecto - CAMBIAR EN PRODUCCIÓN", Colors.YELLOW)
            validations_ok = False
        else:
            print_colored("  ✅ SECRET_KEY: Longitud correcta", Colors.GREEN)
    
    # Validar ENVIRONMENT
    env = os.getenv("ENVIRONMENT")
    valid_envs = ["development", "staging", "production"]
    if env:
        if env in valid_envs:
            print_colored(f"  ✅ ENVIRONMENT: {env}", Colors.GREEN)
        else:
            print_colored(f"  ⚠️  ENVIRONMENT: '{env}' no es estándar (usar: {', '.join(valid_envs)})", Colors.YELLOW)
    
    # Validar DEBUG en producción
    debug = os.getenv("DEBUG", "false").lower()
    if env == "production" and debug == "true":
        print_colored("  ⚠️  DEBUG=true en producción - DEBERÍA SER false", Colors.YELLOW)
        validations_ok = False
    else:
        print_colored(f"  ✅ DEBUG: {debug}", Colors.GREEN)
    
    # Validar ALLOWED_ORIGINS
    origins = os.getenv("ALLOWED_ORIGINS")
    if origins:
        origins_list = [o.strip() for o in origins.split(",")]
        print_colored(f"  ✅ ALLOWED_ORIGINS: {len(origins_list)} origen(es) configurado(s)", Colors.GREEN)
        for origin in origins_list:
            print(f"      - {origin}")
    
    # Recomendaciones
    print_colored("\n💡 RECOMENDACIONES:", Colors.BOLD + Colors.YELLOW)
    print_colored("-" * 60, Colors.YELLOW)
    
    if not os.getenv("SENTRY_DSN"):
        print_colored("  • Configurar Sentry para tracking de errores en producción", Colors.YELLOW)
        print("    → https://sentry.io (gratis hasta 5K errores/mes)")
    
    if not os.getenv("REDIS_URL"):
        print_colored("  • Considerar agregar Redis para cache y mejor performance", Colors.YELLOW)
        print("    → En Railway: Add Plugin → Redis")
    
    if env == "production" and not os.getenv("SMTP_HOST"):
        print_colored("  • Configurar SMTP para notificaciones por email", Colors.YELLOW)
        print("    → Gmail App Password o SendGrid")
    
    print_colored("\n" + "="*60 + "\n", Colors.BLUE)
    
    return required_status, optional_status


def generate_env_template():
    """Genera un template de .env con las variables faltantes"""
    print_colored("\n📝 Generando template .env.missing...", Colors.BLUE)
    
    missing = []
    
    required_vars = [
        ("SECRET_KEY", "openssl rand -hex 32"),
        ("DATABASE_URL", "postgresql://user:pass@host:5432/db"),
        ("ALLOWED_ORIGINS", "http://localhost:3000"),
        ("ENVIRONMENT", "development"),
    ]
    
    for var, example in required_vars:
        if not os.getenv(var):
            missing.append(f"{var}={example}")
    
    if missing:
        with open(".env.missing", "w") as f:
            f.write("# Variables faltantes - Copiar a .env\n")
            f.write("# " + "="*50 + "\n\n")
            for line in missing:
                f.write(line + "\n")
        
        print_colored("✅ Archivo .env.missing creado con variables faltantes", Colors.GREEN)
    else:
        print_colored("✅ No hay variables faltantes", Colors.GREEN)


def main():
    """Función principal"""
    # Cargar .env si existe
    env_file = ".env"
    
    # Verificar argumentos
    if len(sys.argv) > 1:
        if sys.argv[1] == "--env":
            env_name = sys.argv[2] if len(sys.argv) > 2 else "production"
            env_file = f".env.{env_name}"
    
    if os.path.exists(env_file):
        load_dotenv(env_file)
        print_colored(f"📁 Cargando variables desde: {env_file}", Colors.BLUE)
    else:
        print_colored(f"⚠️  Archivo {env_file} no encontrado", Colors.YELLOW)
        print_colored("   Verificando variables de entorno del sistema", Colors.YELLOW)
    
    # Ejecutar verificación
    check_variables()
    
    # Preguntar si generar template
    if not os.path.exists(".env"):
        response = input("\n¿Generar template .env.missing con variables faltantes? (s/n): ")
        if response.lower() in ['s', 'si', 'y', 'yes']:
            generate_env_template()


if __name__ == "__main__":
    main()
