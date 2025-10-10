#!/usr/bin/env python3
"""
Script de Verificación de Configuración Railway
Sistema de Préstamos y Cobranza

Uso:
    python verify_config.py

Este script verifica que todas las variables de entorno críticas
estén configuradas correctamente antes de deployar a Railway.
"""

import os
import sys
from typing import Dict, List, Tuple

# Colores para terminal
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header():
    """Imprime el header del script"""
    print(f"\n{BLUE}{'='*60}")
    print("🔍 Verificación de Configuración Railway")
    print("Sistema de Préstamos y Cobranza v1.0.0")
    print(f"{'='*60}{RESET}\n")

def check_required_vars() -> Tuple[List[str], List[str]]:
    """
    Verifica variables críticas requeridas
    Retorna: (encontradas, faltantes)
    """
    required_vars = [
        "DATABASE_URL",
        "SECRET_KEY",
        "ENVIRONMENT",
    ]
    
    found = []
    missing = []
    
    print(f"{BLUE}📋 Variables CRÍTICAS:{RESET}")
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # Ocultar valores sensibles
            if var in ["DATABASE_URL", "SECRET_KEY"]:
                display_value = "*" * 20
            else:
                display_value = value
            print(f"  {GREEN}✓{RESET} {var:30} = {display_value}")
            found.append(var)
        else:
            print(f"  {RED}✗{RESET} {var:30} = {RED}FALTANTE{RESET}")
            missing.append(var)
    
    return found, missing

def check_performance_vars() -> Tuple[List[str], List[str]]:
    """
    Verifica variables de performance
    Retorna: (encontradas, faltantes)
    """
    performance_vars = {
        "UVICORN_TIMEOUT_KEEP_ALIVE": "120",
        "UVICORN_TIMEOUT_GRACEFUL_SHUTDOWN": "30",
        "UVICORN_WORKERS": "1",
    }
    
    found = []
    missing = []
    
    print(f"\n{BLUE}⚡ Variables de PERFORMANCE:{RESET}")
    for var, recommended in performance_vars.items():
        value = os.getenv(var)
        if value:
            if value != recommended:
                print(f"  {YELLOW}⚠{RESET} {var:40} = {value} (recomendado: {recommended})")
            else:
                print(f"  {GREEN}✓{RESET} {var:40} = {value}")
            found.append(var)
        else:
            print(f"  {RED}✗{RESET} {var:40} = {RED}FALTANTE{RESET} (recomendado: {recommended})")
            missing.append(var)
    
    return found, missing

def check_db_pool_vars() -> Tuple[List[str], List[str]]:
    """
    Verifica variables de pool de base de datos
    Retorna: (encontradas, faltantes)
    """
    db_pool_vars = {
        "DB_POOL_SIZE": "5",
        "DB_MAX_OVERFLOW": "10",
        "DB_POOL_TIMEOUT": "30",
        "DB_POOL_RECYCLE": "3600",
    }
    
    found = []
    missing = []
    
    print(f"\n{BLUE}🗄️  Variables de DATABASE POOL:{RESET}")
    for var, recommended in db_pool_vars.items():
        value = os.getenv(var)
        if value:
            if value != recommended:
                print(f"  {YELLOW}⚠{RESET} {var:30} = {value} (recomendado: {recommended})")
            else:
                print(f"  {GREEN}✓{RESET} {var:30} = {value}")
            found.append(var)
        else:
            print(f"  {RED}✗{RESET} {var:30} = {RED}FALTANTE{RESET} (recomendado: {recommended})")
            missing.append(var)
    
    return found, missing

def check_optional_vars() -> Tuple[List[str], List[str]]:
    """
    Verifica variables opcionales
    Retorna: (encontradas, faltantes)
    """
    optional_vars = [
        "DEBUG",
        "LOG_LEVEL",
        "PYTHONUNBUFFERED",
        "PORT",
        "HEALTH_CHECK_CACHE_DURATION",
        "ALLOWED_ORIGINS",
    ]
    
    found = []
    missing = []
    
    print(f"\n{BLUE}🔧 Variables OPCIONALES (pero recomendadas):{RESET}")
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"  {GREEN}✓{RESET} {var:30} = {value}")
            found.append(var)
        else:
            print(f"  {YELLOW}○{RESET} {var:30} = {YELLOW}No configurada{RESET}")
            missing.append(var)
    
    return found, missing

def check_database_url_format():
    """Verifica el formato de DATABASE_URL"""
    print(f"\n{BLUE}🔍 Verificación de DATABASE_URL:{RESET}")
    
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print(f"  {RED}✗ DATABASE_URL no está configurada{RESET}")
        return False
    
    # Verificar formato básico
    if not db_url.startswith("postgresql://"):
        print(f"  {RED}✗ DATABASE_URL debe empezar con 'postgresql://'{RESET}")
        return False
    
    # Verificar componentes básicos
    try:
        if "@" in db_url and ":" in db_url:
            print(f"  {GREEN}✓ Formato parece correcto (postgresql://...){RESET}")
            return True
        else:
            print(f"  {YELLOW}⚠ Formato puede estar incorrecto{RESET}")
            return False
    except:
        print(f"  {RED}✗ Error analizando DATABASE_URL{RESET}")
        return False

def print_summary(
    critical_found: List[str],
    critical_missing: List[str],
    perf_found: List[str],
    perf_missing: List[str],
    pool_found: List[str],
    pool_missing: List[str],
    optional_found: List[str],
    optional_missing: List[str]
):
    """Imprime resumen final"""
    print(f"\n{BLUE}{'='*60}")
    print("📊 RESUMEN")
    print(f"{'='*60}{RESET}\n")
    
    total_found = len(critical_found) + len(perf_found) + len(pool_found) + len(optional_found)
    total_missing = len(critical_missing) + len(perf_missing) + len(pool_missing)
    
    print(f"Variables encontradas:    {GREEN}{total_found}{RESET}")
    print(f"Variables críticas faltantes: {RED}{len(critical_missing) + len(perf_missing) + len(pool_missing)}{RESET}")
    print(f"Variables opcionales faltantes: {YELLOW}{len(optional_missing)}{RESET}")
    
    # Estado general
    print(f"\n{BLUE}Estado General:{RESET}")
    if len(critical_missing) > 0:
        print(f"  {RED}✗ CRÍTICO - Faltan variables requeridas{RESET}")
        print(f"    Variables faltantes: {', '.join(critical_missing)}")
    elif len(perf_missing) > 0 or len(pool_missing) > 0:
        print(f"  {YELLOW}⚠ ADVERTENCIA - Faltan variables de optimización{RESET}")
        all_missing = perf_missing + pool_missing
        print(f"    Variables faltantes: {', '.join(all_missing)}")
    else:
        print(f"  {GREEN}✓ EXCELENTE - Todas las variables críticas configuradas{RESET}")
    
    # Recomendaciones
    print(f"\n{BLUE}Recomendaciones:{RESET}")
    if len(critical_missing) > 0:
        print(f"  {RED}1. Añade las variables críticas antes de deployar{RESET}")
    if len(perf_missing) > 0 or len(pool_missing) > 0:
        print(f"  {YELLOW}2. Añade las variables de optimización para mejor performance{RESET}")
    if len(optional_missing) > 0:
        print(f"  3. Considera añadir variables opcionales para mejor control")
    
    if len(critical_missing) == 0 and len(perf_missing) == 0 and len(pool_missing) == 0:
        print(f"  {GREEN}✓ Tu configuración está lista para producción!{RESET}")
    
    print()

def main():
    """Función principal"""
    print_header()
    
    # Verificar variables por categoría
    critical_found, critical_missing = check_required_vars()
    perf_found, perf_missing = check_performance_vars()
    pool_found, pool_missing = check_db_pool_vars()
    optional_found, optional_missing = check_optional_vars()
    
    # Verificaciones especiales
    check_database_url_format()
    
    # Resumen
    print_summary(
        critical_found, critical_missing,
        perf_found, perf_missing,
        pool_found, pool_missing,
        optional_found, optional_missing
    )
    
    # Exit code
    if len(critical_missing) > 0:
        sys.exit(1)  # Error crítico
    elif len(perf_missing) > 0 or len(pool_missing) > 0:
        sys.exit(2)  # Warning
    else:
        sys.exit(0)  # Success

if __name__ == "__main__":
    main()
