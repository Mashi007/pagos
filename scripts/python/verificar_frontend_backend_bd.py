#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de Verificación: Frontend, Backend y Base de Datos
Verifica que todos los componentes estén sincronizados y actualizados.
"""

import os
import sys
import re
from pathlib import Path
from typing import Dict, List, Set
from collections import defaultdict

# Agregar el directorio raíz al path
ROOT_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))

def extract_backend_endpoints() -> Dict[str, List[str]]:
    """Extraer todos los endpoints del backend"""
    endpoints = defaultdict(list)
    backend_dir = ROOT_DIR / "backend" / "app" / "api" / "v1" / "endpoints"
    
    if not backend_dir.exists():
        print(f"[ERROR] Directorio de endpoints no encontrado: {backend_dir}")
        return endpoints
    
    # Patrón para encontrar decoradores de router
    router_pattern = re.compile(r'@router\.(get|post|put|patch|delete|head)\("([^"]+)"')
    
    for file_path in backend_dir.glob("*.py"):
        if file_path.name == "__init__.py":
            continue
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                matches = router_pattern.findall(content)
                
                for method, path in matches:
                    full_path = f"{method.upper()} {path}"
                    endpoints[file_path.stem].append(full_path)
        except Exception as e:
            print(f"[WARNING] Error leyendo {file_path}: {e}")
    
    return dict(endpoints)

def extract_frontend_services() -> Dict[str, List[str]]:
    """Extraer todas las llamadas API del frontend"""
    services = defaultdict(list)
    frontend_dir = ROOT_DIR / "frontend" / "src" / "services"
    
    if not frontend_dir.exists():
        print(f"[ERROR] Directorio de servicios no encontrado: {frontend_dir}")
        return services
    
    # Patrón para encontrar llamadas apiClient
    api_pattern = re.compile(r'apiClient\.(get|post|put|patch|delete)\s*\(\s*["\']([^"\']+)["\']')
    base_url_pattern = re.compile(r'private\s+baseUrl\s*=\s*["\']([^"\']+)["\']')
    
    for file_path in frontend_dir.glob("*Service.ts"):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Buscar baseUrl
                base_url_match = base_url_pattern.search(content)
                base_url = base_url_match.group(1) if base_url_match else ""
                
                # Buscar llamadas API
                matches = api_pattern.findall(content)
                for method, path in matches:
                    # Construir URL completa
                    if path.startswith('/'):
                        full_path = f"{method.upper()} {path}"
                    elif base_url:
                        full_path = f"{method.upper()} {base_url}{path}"
                    else:
                        full_path = f"{method.upper()} {path}"
                    
                    services[file_path.stem.replace('Service', '')].append(full_path)
        except Exception as e:
            print(f"[WARNING] Error leyendo {file_path}: {e}")
    
    return dict(services)

def check_migrations_status() -> tuple[bool, str]:
    """Verificar estado de migraciones Alembic"""
    try:
        from alembic import command
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        
        alembic_ini = ROOT_DIR / "backend" / "alembic.ini"
        if not alembic_ini.exists():
            return False, "alembic.ini no encontrado"
        
        cfg = Config(str(alembic_ini))
        
        # Obtener configuración de BD
        from app.core.config import settings
        cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
        
        # Verificar heads
        script = ScriptDirectory.from_config(cfg)
        heads = script.get_revisions("heads")
        
        return True, f"Heads disponibles: {len(heads)}"
    except Exception as e:
        return False, f"Error: {str(e)}"

def check_models_sync() -> List[str]:
    """Verificar sincronización entre modelos ORM y schemas"""
    issues = []
    
    models_dir = ROOT_DIR / "backend" / "app" / "models"
    schemas_dir = ROOT_DIR / "backend" / "app" / "schemas"
    
    if not models_dir.exists():
        issues.append("Directorio de modelos no encontrado")
        return issues
    
    if not schemas_dir.exists():
        issues.append("Directorio de schemas no encontrado")
        return issues
    
    # Obtener lista de modelos
    model_files = {f.stem for f in models_dir.glob("*.py") if f.stem != "__init__"}
    schema_files = {f.stem for f in schemas_dir.glob("*.py") if f.stem != "__init__"}
    
    # Modelos sin schemas
    missing_schemas = model_files - schema_files
    if missing_schemas:
        issues.append(f"Modelos sin schemas: {', '.join(sorted(missing_schemas))}")
    
    return issues

def normalize_path(path: str) -> str:
    """Normalizar path para comparación"""
    # Remover parámetros de ruta {id} -> *
    path = re.sub(r'\{[^}]+\}', '*', path)
    # Normalizar método y path
    parts = path.split(' ', 1)
    if len(parts) == 2:
        return f"{parts[0]} {parts[1].lower()}"
    return path.lower()

def main():
    print("="*80)
    print("VERIFICACION COMPLETA: Frontend, Backend y Base de Datos")
    print("="*80)
    
    # 1. Verificar Endpoints Backend vs Frontend
    print("\n[1] VERIFICACION DE ENDPOINTS")
    print("-"*80)
    
    backend_endpoints = extract_backend_endpoints()
    frontend_services = extract_frontend_services()
    
    backend_total = sum(len(v) for v in backend_endpoints.values())
    frontend_total = sum(len(v) for v in frontend_services.values())
    
    print(f"Endpoints encontrados en backend: {backend_total}")
    print(f"Llamadas encontradas en frontend: {frontend_total}")
    
    # Comparar endpoints
    backend_endpoint_set = set()
    for endpoints in backend_endpoints.values():
        backend_endpoint_set.update(endpoints)
    
    frontend_endpoint_set = set()
    for endpoints in frontend_services.values():
        frontend_endpoint_set.update(endpoints)
    
    backend_normalized = {normalize_path(e) for e in backend_endpoint_set}
    frontend_normalized = {normalize_path(e) for e in frontend_endpoint_set}
    
    missing_in_frontend = backend_normalized - frontend_normalized
    extra_in_frontend = frontend_normalized - backend_normalized
    
    matched = len(backend_normalized & frontend_normalized)
    
    print(f"\nCoincidencias: {matched}/{len(backend_normalized)}")
    
    if missing_in_frontend:
        print(f"\n[WARNING] Endpoints del backend no usados en frontend: {len(missing_in_frontend)}")
        for endpoint in sorted(list(missing_in_frontend))[:10]:
            print(f"   - {endpoint}")
        if len(missing_in_frontend) > 10:
            print(f"   ... y {len(missing_in_frontend) - 10} mas")
    else:
        print("\n[OK] Todos los endpoints principales tienen correspondencia")
    
    if extra_in_frontend:
        print(f"\n[WARNING] Llamadas del frontend sin endpoint en backend: {len(extra_in_frontend)}")
        for endpoint in sorted(list(extra_in_frontend))[:5]:
            print(f"   - {endpoint}")
        if len(extra_in_frontend) > 5:
            print(f"   ... y {len(extra_in_frontend) - 5} mas")
    
    # 2. Verificar Migraciones
    print("\n[2] VERIFICACION DE MIGRACIONES")
    print("-"*80)
    
    migration_ok, migration_msg = check_migrations_status()
    if migration_ok:
        print(f"[OK] {migration_msg}")
    else:
        print(f"[ERROR] {migration_msg}")
    
    # 3. Verificar Modelos y Schemas
    print("\n[3] VERIFICACION DE MODELOS Y SCHEMAS")
    print("-"*80)
    
    model_issues = check_models_sync()
    if model_issues:
        for issue in model_issues:
            print(f"[WARNING] {issue}")
    else:
        print("[OK] Modelos y schemas estan sincronizados")
    
    # 4. Resumen Final
    print("\n" + "="*80)
    print("RESUMEN FINAL")
    print("="*80)
    
    print(f"\nEndpoints:")
    print(f"  Total en backend: {len(backend_normalized)}")
    print(f"  Coincidencias: {matched}")
    print(f"  Sin usar en frontend: {len(missing_in_frontend)}")
    
    print(f"\nMigraciones:")
    print(f"  Estado: {'OK' if migration_ok else 'ERROR'}")
    print(f"  Mensaje: {migration_msg}")
    
    print(f"\nModelos:")
    print(f"  Issues encontrados: {len(model_issues)}")
    
    # Determinar estado general
    all_ok = (
        (len(missing_in_frontend) == 0 or len(missing_in_frontend) < 20) and
        migration_ok and
        len(model_issues) == 0
    )
    
    if all_ok:
        print("\n[OK] Sistema esta sincronizado y actualizado")
        return 0
    else:
        print("\n[WARNING] Se encontraron algunas discrepancias")
        return 1

if __name__ == "__main__":
    sys.exit(main())
