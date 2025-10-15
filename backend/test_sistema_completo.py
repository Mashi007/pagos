"""
Script de Test Completo del Sistema
Verifica: Configuración, Rutas, Endpoints, Modelos, Migraciones
"""
import sys
import os
from pathlib import Path

# Colores para output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.CYAN}{Colors.BOLD}{'='*70}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}{text.center(70)}{Colors.RESET}")
    print(f"{Colors.CYAN}{Colors.BOLD}{'='*70}{Colors.RESET}\n")

def print_test(name, passed, details=""):
    status = f"{Colors.GREEN}✅ PASS{Colors.RESET}" if passed else f"{Colors.RED}❌ FAIL{Colors.RESET}"
    print(f"{status} | {name}")
    if details and not passed:
        print(f"       └─ {Colors.YELLOW}{details}{Colors.RESET}")

# ============================================================================
# TEST 1: CONFIGURACIÓN RAÍZ
# ============================================================================
def test_configuracion_raiz():
    print_header("TEST 1: CONFIGURACIÓN RAÍZ")
    
    tests = []
    
    # 1.1 Verificar app/main.py existe
    main_file = Path("app/main.py")
    tests.append(("main.py existe", main_file.exists(), f"No encontrado: {main_file}"))
    
    # 1.2 Verificar app/core/config.py existe
    config_file = Path("app/core/config.py")
    tests.append(("config.py existe", config_file.exists(), f"No encontrado: {config_file}"))
    
    # 1.3 Verificar app/db/session.py existe
    session_file = Path("app/db/session.py")
    tests.append(("session.py existe", session_file.exists(), f"No encontrado: {session_file}"))
    
    # 1.4 Verificar alembic.ini existe
    alembic_ini = Path("alembic.ini")
    tests.append(("alembic.ini existe", alembic_ini.exists(), f"No encontrado: {alembic_ini}"))
    
    # 1.5 Verificar requirements.txt existe
    requirements = Path("requirements.txt")
    tests.append(("requirements.txt existe", requirements.exists(), f"No encontrado: {requirements}"))
    
    for name, passed, details in tests:
        print_test(name, passed, details)
    
    passed_count = sum(1 for _, p, _ in tests if p)
    total_count = len(tests)
    print(f"\n{Colors.BOLD}Resultado: {passed_count}/{total_count} tests pasados{Colors.RESET}")
    
    return passed_count == total_count

# ============================================================================
# TEST 2: ESTRUCTURA DE MODELOS
# ============================================================================
def test_estructura_modelos():
    print_header("TEST 2: ESTRUCTURA DE MODELOS")
    
    tests = []
    
    modelos_requeridos = [
        "cliente.py",
        "user.py",
        "asesor.py",
        "concesionario.py",
        "modelo_vehiculo.py",
        "prestamo.py",
        "pago.py",
        "amortizacion.py",
        "notificacion.py",
        "auditoria.py"
    ]
    
    models_dir = Path("app/models")
    
    for modelo in modelos_requeridos:
        modelo_path = models_dir / modelo
        tests.append((f"Modelo {modelo}", modelo_path.exists(), f"No encontrado: {modelo_path}"))
    
    for name, passed, details in tests:
        print_test(name, passed, details)
    
    # Verificar contenido de modelos críticos
    print(f"\n{Colors.BOLD}Verificando integridad de modelos...{Colors.RESET}")
    
    # Cliente debe tener asesor_config_id, NO asesor_id
    cliente_path = models_dir / "cliente.py"
    if cliente_path.exists():
        with open(cliente_path, 'r', encoding='utf-8') as f:
            content = f.read()
            has_config_id = 'asesor_config_id' in content
            has_old_id = 'asesor_id = Column' in content and 'ForeignKey("users.id")' in content
            
            print_test("Cliente usa asesor_config_id", has_config_id, "No encontrado asesor_config_id")
            print_test("Cliente NO usa asesor_id obsoleto", not has_old_id, "Encontrado asesor_id con ForeignKey users.id")
    
    # User NO debe tener clientes_asignados
    user_path = models_dir / "user.py"
    if user_path.exists():
        with open(user_path, 'r', encoding='utf-8') as f:
            content = f.read()
            has_clientes = 'clientes_asignados' in content
            
            print_test("User NO tiene clientes_asignados", not has_clientes, "Encontrado clientes_asignados en User")
    
    passed_count = sum(1 for _, p, _ in tests if p)
    total_count = len(tests)
    print(f"\n{Colors.BOLD}Resultado: {passed_count}/{total_count} tests pasados{Colors.RESET}")
    
    return passed_count == total_count

# ============================================================================
# TEST 3: ENDPOINTS REGISTRADOS
# ============================================================================
def test_endpoints_registrados():
    print_header("TEST 3: ENDPOINTS REGISTRADOS EN MAIN.PY")
    
    tests = []
    
    main_file = Path("app/main.py")
    
    if not main_file.exists():
        print_test("main.py existe", False, "No se puede verificar endpoints")
        return False
    
    with open(main_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    endpoints_requeridos = [
        ("Health", "health.router"),
        ("Auth", "auth.router"),
        ("Users", "users.router"),
        ("Clientes", "clientes.router"),
        ("Asesores", "asesores.router"),
        ("Concesionarios", "concesionarios.router"),
        ("Modelos Vehículos", "modelos_vehiculos.router"),
        ("Dashboard", "dashboard.router"),
        ("KPIs", "kpis.router"),
        ("Reportes", "reportes.router"),
        ("Pagos", "pagos.router"),
        ("Prestamos", "prestamos.router")
    ]
    
    for name, router in endpoints_requeridos:
        registered = f"include_router({router}" in content
        tests.append((f"Router {name}", registered, f"No registrado: {router}"))
    
    for name, passed, details in tests:
        print_test(name, passed, details)
    
    passed_count = sum(1 for _, p, _ in tests if p)
    total_count = len(tests)
    print(f"\n{Colors.BOLD}Resultado: {passed_count}/{total_count} tests pasados{Colors.RESET}")
    
    return passed_count == total_count

# ============================================================================
# TEST 4: RUTAS DE ENDPOINTS
# ============================================================================
def test_rutas_endpoints():
    print_header("TEST 4: CONSISTENCIA DE RUTAS")
    
    tests = []
    
    endpoints_dir = Path("app/api/v1/endpoints")
    
    # Verificar que archivos críticos existen
    archivos_criticos = [
        "clientes.py",
        "asesores.py",
        "concesionarios.py",
        "modelos_vehiculos.py",
        "dashboard.py",
        "kpis.py",
        "reportes.py"
    ]
    
    for archivo in archivos_criticos:
        archivo_path = endpoints_dir / archivo
        tests.append((f"Endpoint {archivo}", archivo_path.exists(), f"No encontrado: {archivo_path}"))
    
    # Verificar que usan asesor_config_id, NO asesor_id
    print(f"\n{Colors.BOLD}Verificando uso correcto de asesor_config_id...{Colors.RESET}")
    
    archivos_a_verificar = ["clientes.py", "dashboard.py", "kpis.py", "reportes.py"]
    
    for archivo in archivos_a_verificar:
        archivo_path = endpoints_dir / archivo
        if archivo_path.exists():
            with open(archivo_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Contar referencias incorrectas (excepto en parámetros de ruta como /{asesor_id})
                # y en comentarios
                lines = content.split('\n')
                bad_refs = 0
                for line in lines:
                    if 'asesor_id' in line and 'asesor_config_id' not in line:
                        # Ignorar comentarios y rutas path
                        if not line.strip().startswith('#') and '/{asesor_id}' not in line and '@router' not in line:
                            bad_refs += 1
                
                has_config = 'asesor_config_id' in content
                
                print_test(f"{archivo} usa asesor_config_id", has_config, "No usa asesor_config_id")
                print_test(f"{archivo} sin referencias incorrectas a asesor_id", bad_refs == 0, f"Encontradas {bad_refs} referencias")
    
    for name, passed, details in tests:
        print_test(name, passed, details)
    
    passed_count = sum(1 for _, p, _ in tests if p)
    total_count = len(tests)
    print(f"\n{Colors.BOLD}Resultado: {passed_count}/{total_count} tests pasados{Colors.RESET}")
    
    return passed_count == total_count

# ============================================================================
# TEST 5: SCHEMAS
# ============================================================================
def test_schemas():
    print_header("TEST 5: SCHEMAS PYDANTIC")
    
    tests = []
    
    schemas_dir = Path("app/schemas")
    
    # Verificar schemas críticos
    schemas_criticos = [
        "cliente.py",
        "user.py",
        "asesor.py",
        "auth.py",
        "pago.py",
        "prestamo.py"
    ]
    
    for schema in schemas_criticos:
        schema_path = schemas_dir / schema
        tests.append((f"Schema {schema}", schema_path.exists(), f"No encontrado: {schema_path}"))
    
    # Verificar cliente.py usa asesor_config_id
    cliente_schema = schemas_dir / "cliente.py"
    if cliente_schema.exists():
        with open(cliente_schema, 'r', encoding='utf-8') as f:
            content = f.read()
            has_config_id = 'asesor_config_id' in content
            # Verificar que NO tiene asesor_id sin asesor_config_id en la misma línea
            has_old_only = 'asesor_id:' in content and 'asesor_config_id' not in content.split('asesor_id:')[0].split('\n')[-1]
            
            print_test("Schema Cliente usa asesor_config_id", has_config_id, "No encontrado asesor_config_id")
    
    for name, passed, details in tests:
        print_test(name, passed, details)
    
    passed_count = sum(1 for _, p, _ in tests if p)
    total_count = len(tests)
    print(f"\n{Colors.BOLD}Resultado: {passed_count}/{total_count} tests pasados{Colors.RESET}")
    
    return passed_count == total_count

# ============================================================================
# TEST 6: MIGRACIONES
# ============================================================================
def test_migraciones():
    print_header("TEST 6: MIGRACIONES ALEMBIC")
    
    tests = []
    
    # Verificar directorio de migraciones
    migrations_dir = Path("alembic/versions")
    tests.append(("Directorio de migraciones", migrations_dir.exists(), f"No encontrado: {migrations_dir}"))
    
    if migrations_dir.exists():
        # Contar archivos de migración
        migration_files = list(migrations_dir.glob("*.py"))
        migration_files = [f for f in migration_files if f.name != "__pycache__"]
        
        tests.append(("Tiene migraciones", len(migration_files) > 0, "No hay archivos de migración"))
        
        # Buscar migración específica de asesor_id
        has_asesor_migration = False
        for mig_file in migration_files:
            if 'asesor' in mig_file.name.lower() or 'cliente' in mig_file.name.lower():
                with open(mig_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'asesor_id' in content or 'asesor_config_id' in content:
                        has_asesor_migration = True
                        print(f"  └─ Migración encontrada: {mig_file.name}")
        
        tests.append(("Migración para asesor_config_id", has_asesor_migration, "No encontrada migración relacionada"))
    
    for name, passed, details in tests:
        print_test(name, passed, details)
    
    passed_count = sum(1 for _, p, _ in tests if p)
    total_count = len(tests)
    print(f"\n{Colors.BOLD}Resultado: {passed_count}/{total_count} tests pasados{Colors.RESET}")
    
    return passed_count == total_count

# ============================================================================
# TEST 7: IMPORTS Y DEPENDENCIAS
# ============================================================================
def test_imports():
    print_header("TEST 7: IMPORTS Y DEPENDENCIAS")
    
    print(f"{Colors.YELLOW}Intentando importar módulos principales...{Colors.RESET}\n")
    
    tests = []
    
    # Cambiar al directorio backend si estamos en raíz
    if Path("backend").exists():
        os.chdir("backend")
    
    try:
        # Intentar imports básicos
        try:
            from app.core.config import settings
            tests.append(("Import app.core.config", True, ""))
        except Exception as e:
            tests.append(("Import app.core.config", False, str(e)))
        
        try:
            from app.db.session import get_db
            tests.append(("Import app.db.session", True, ""))
        except Exception as e:
            tests.append(("Import app.db.session", False, str(e)))
        
        try:
            from app.models.cliente import Cliente
            tests.append(("Import models.cliente", True, ""))
        except Exception as e:
            tests.append(("Import models.cliente", False, str(e)))
        
        try:
            from app.models.asesor import Asesor
            tests.append(("Import models.asesor", True, ""))
        except Exception as e:
            tests.append(("Import models.asesor", False, str(e)))
        
        try:
            from app.models.user import User
            tests.append(("Import models.user", True, ""))
        except Exception as e:
            tests.append(("Import models.user", False, str(e)))
        
    except Exception as e:
        print(f"{Colors.RED}Error general en imports: {e}{Colors.RESET}")
    
    for name, passed, details in tests:
        print_test(name, passed, details)
    
    passed_count = sum(1 for _, p, _ in tests if p)
    total_count = len(tests)
    print(f"\n{Colors.BOLD}Resultado: {passed_count}/{total_count} tests pasados{Colors.RESET}")
    
    return passed_count == total_count

# ============================================================================
# MAIN
# ============================================================================
def main():
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("╔════════════════════════════════════════════════════════════════════╗")
    print("║                  TEST SISTEMA COMPLETO                             ║")
    print("║              Sistema de Préstamos y Cobranza                       ║")
    print("╚════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.RESET}\n")
    
    # Cambiar al directorio backend si existe
    if Path("backend").exists():
        print(f"{Colors.YELLOW}📁 Cambiando a directorio backend...{Colors.RESET}")
        os.chdir("backend")
    
    results = []
    
    # Ejecutar tests
    results.append(("Configuración Raíz", test_configuracion_raiz()))
    results.append(("Estructura de Modelos", test_estructura_modelos()))
    results.append(("Endpoints Registrados", test_endpoints_registrados()))
    results.append(("Rutas de Endpoints", test_rutas_endpoints()))
    results.append(("Schemas Pydantic", test_schemas()))
    results.append(("Migraciones Alembic", test_migraciones()))
    results.append(("Imports y Dependencias", test_imports()))
    
    # Resumen final
    print_header("RESUMEN FINAL")
    
    for name, passed in results:
        status = f"{Colors.GREEN}✅ PASS{Colors.RESET}" if passed else f"{Colors.RED}❌ FAIL{Colors.RESET}"
        print(f"{status} | {name}")
    
    passed_count = sum(1 for _, p in results if p)
    total_count = len(results)
    
    print(f"\n{Colors.BOLD}")
    print(f"{'='*70}")
    print(f"RESULTADO GLOBAL: {passed_count}/{total_count} grupos de tests pasados")
    print(f"{'='*70}")
    print(f"{Colors.RESET}")
    
    if passed_count == total_count:
        print(f"{Colors.GREEN}{Colors.BOLD}🎉 TODOS LOS TESTS PASARON 🎉{Colors.RESET}\n")
        return 0
    else:
        print(f"{Colors.RED}{Colors.BOLD}⚠️  ALGUNOS TESTS FALLARON ⚠️{Colors.RESET}\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())

