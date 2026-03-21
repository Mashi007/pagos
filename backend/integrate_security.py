"""
Script de Integración - Agregar Middlewares de Seguridad FASE 1 a main.py
"""

import os

# Ruta del archivo
main_py_path = r"backend\app\main.py"

# Leer contenido actual
with open(main_py_path, "r", encoding="utf-8") as f:
    content = f.read()

# 1. AGREGAR IMPORTS DE SEGURIDAD (después de los imports existentes)
imports_section = """from app.middleware.audit_middleware import AuditMiddleware
from app.middleware.validador_sobre_aplicacion import ValidadorSobreAplicacionMiddleware
from app.services.liquidado_scheduler import liquidado_scheduler"""

new_imports = """from app.middleware.audit_middleware import AuditMiddleware
from app.middleware.validador_sobre_aplicacion import ValidadorSobreAplicacionMiddleware
from app.services.liquidado_scheduler import liquidado_scheduler

# Importar middlewares de seguridad FASE 1
from app.middleware.security_headers import (
    SecurityHeadersMiddleware,
    ContentSecurityPolicyMiddleware,
    RequestIdMiddleware,
)
# Importar router de autenticación con CSRF
from app.api.v1.endpoints import auth_csrf_cookies"""

if imports_section in content:
    content = content.replace(imports_section, new_imports)
    print("✅ Imports de seguridad agregados")
else:
    print("⚠️ No se encontró la sección de imports esperada")

# 2. AGREGAR MIDDLEWARES (en orden correcto)
middleware_section = """app.add_middleware(RequestLogMiddleware)

# Middleware: Validación en tiempo real de sobre-aplicaciones
app.add_middleware(ValidadorSobreAplicacionMiddleware)

# Auditoría automática: registra todos los POST/PUT/DELETE/PATCH en tabla auditoria
app.add_middleware(AuditMiddleware)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    expose_headers=["X-Total-Count", "X-Page-Count"],
    max_age=3600,
)"""

new_middleware = """app.add_middleware(RequestLogMiddleware)

# Middleware: Validación en tiempo real de sobre-aplicaciones
app.add_middleware(ValidadorSobreAplicacionMiddleware)

# Auditoría automática: registra todos los POST/PUT/DELETE/PATCH en tabla auditoria
app.add_middleware(AuditMiddleware)

# ========== MIDDLEWARES DE SEGURIDAD FASE 1 ==========
# IMPORTANTE: Orden correcto de middlewares (de abajo hacia arriba)
# RequestIdMiddleware debe estar al final (primero en ejecución)
app.add_middleware(RequestIdMiddleware)

# SecurityHeadersMiddleware: Agrega headers OWASP
app.add_middleware(SecurityHeadersMiddleware)

# ContentSecurityPolicyMiddleware: CSP headers
app.add_middleware(ContentSecurityPolicyMiddleware)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With", "X-CSRF-Token"],
    expose_headers=["X-Total-Count", "X-Page-Count"],
    max_age=3600,
)
# ================================================"""

if middleware_section in content:
    content = content.replace(middleware_section, new_middleware)
    print("✅ Middlewares de seguridad agregados")
else:
    print("⚠️ No se encontró la sección de middlewares esperada")

# 3. AGREGAR ROUTER DE AUTENTICACIÓN (después de api_router)
router_section = """# Incluir routers
app.include_router(api_router, prefix=settings.API_V1_STR)

# Incluir endpoint del scheduler de LIQUIDADO"""

new_router_section = """# Incluir routers
app.include_router(api_router, prefix=settings.API_V1_STR)

# ========== ROUTER DE AUTENTICACIÓN CON CSRF (FASE 1) ==========
# Endpoints: GET /auth/login-form, POST /auth/login, POST /auth/logout
app.include_router(auth_csrf_cookies.router, prefix=settings.API_V1_STR)
# ========================================================

# Incluir endpoint del scheduler de LIQUIDADO"""

if router_section in content:
    content = content.replace(router_section, new_router_section)
    print("✅ Router de autenticación agregado")
else:
    print("⚠️ No se encontró la sección de routers esperada")

# Guardar archivo actualizado
with open(main_py_path, "w", encoding="utf-8") as f:
    f.write(content)

print("\n✅ INTEGRACIÓN COMPLETADA")
print("\n📋 Cambios realizados:")
print("   1. Imports de seguridad agregados")
print("   2. Middlewares de seguridad integrados (orden correcto)")
print("   3. Router de autenticación con CSRF agregado")
print("\n🔒 Security improvements:")
print("   ✅ CSRF Token Protection")
print("   ✅ Secure Cookies (httpOnly, Secure, SameSite)")
print("   ✅ CSP Headers")
print("   ✅ OWASP Security Headers")
print("\n📝 Próximo paso: Crear tabla csrf_tokens en BD")
print("   Ejecutar el SQL en GUIA_INTEGRACION_FASE1.md")
