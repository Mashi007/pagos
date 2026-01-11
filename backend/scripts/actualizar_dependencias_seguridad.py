#!/usr/bin/env python3
"""
Script para actualizar dependencias con vulnerabilidades de seguridad
Basado en resultados de pip-audit
"""
import subprocess
import sys
from pathlib import Path

# Versiones seguras según pip-audit
SECURE_VERSIONS = {
    "aiohttp": ">=3.13.3",
    "starlette": ">=0.49.1",
    "mcp": ">=1.23.0",
    "pip": ">=25.3",
}

# Paquetes que requieren actualización de dependencias principales
# FastAPI debe actualizarse para incluir starlette>=0.49.1
# httpx debe actualizarse para incluir aiohttp>=3.13.3
MAIN_PACKAGES_TO_UPDATE = {
    "fastapi": ">=0.121.2",  # Ya está en base.txt pero verificar compatibilidad
    "httpx": ">=0.28.1",  # Ya está en base.txt
}


def run_command(cmd: list[str], check: bool = True) -> tuple[int, str, str]:
    """Ejecuta un comando y retorna el resultado"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=check,
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return e.returncode, e.stdout, e.stderr


def check_package_installed(package: str) -> bool:
    """Verifica si un paquete está instalado"""
    returncode, _, _ = run_command([sys.executable, "-m", "pip", "show", package], check=False)
    return returncode == 0


def update_package(package: str, version: str) -> bool:
    """Actualiza un paquete a la versión especificada"""
    print(f"📦 Actualizando {package}{version}...")
    returncode, stdout, stderr = run_command(
        [sys.executable, "-m", "pip", "install", "--upgrade", f"{package}{version}"],
        check=False,
    )
    
    if returncode == 0:
        print(f"✅ {package} actualizado exitosamente")
        return True
    else:
        print(f"❌ Error actualizando {package}: {stderr}")
        return False


def main():
    """Función principal"""
    print("🔒 ACTUALIZACIÓN DE DEPENDENCIAS DE SEGURIDAD")
    print("=" * 60)
    
    # 1. Actualizar pip primero
    print("\n1️⃣ Actualizando pip...")
    update_package("pip", SECURE_VERSIONS["pip"])
    
    # 2. Actualizar paquetes principales
    print("\n2️⃣ Actualizando paquetes principales...")
    for package, version in MAIN_PACKAGES_TO_UPDATE.items():
        if check_package_installed(package):
            update_package(package, version)
        else:
            print(f"⚠️ {package} no está instalado, omitiendo...")
    
    # 3. Actualizar dependencias directas vulnerables (si están instaladas)
    print("\n3️⃣ Actualizando dependencias vulnerables...")
    for package, version in SECURE_VERSIONS.items():
        if package == "pip":  # Ya actualizado
            continue
        if check_package_installed(package):
            update_package(package, version)
        else:
            print(f"ℹ️ {package} no está instalado directamente (probablemente dependencia indirecta)")
    
    # 4. Verificar vulnerabilidades restantes
    print("\n4️⃣ Verificando vulnerabilidades restantes...")
    returncode, stdout, stderr = run_command(
        [sys.executable, "-m", "pip_audit", "--format=text"],
        check=False,
    )
    
    if returncode == 0:
        print("✅ Verificación completada:")
        print(stdout)
    else:
        print("⚠️ pip-audit no disponible o encontró vulnerabilidades:")
        print(stderr)
    
    print("\n" + "=" * 60)
    print("✅ Actualización completada")
    print("\n📝 Próximos pasos:")
    print("1. Ejecutar tests: pytest")
    print("2. Verificar que la aplicación funciona correctamente")
    print("3. Revisar vulnerabilidades de ecdsa (sin fix disponible)")


if __name__ == "__main__":
    main()
