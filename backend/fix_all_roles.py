"""
Script para reemplazar TODAS las referencias a roles antiguos por USER
"""
import os
import re

# Archivos a procesar
archivos = [
    "app/api/v1/endpoints/validadores.py",
    "app/db/init_db.py",
    "app/api/v1/endpoints/modelos_vehiculos.py",
    "app/api/v1/endpoints/dashboard.py",
    "app/api/v1/endpoints/sql_direct.py",
    "app/api/v1/endpoints/sql_delete_admin.py",
    "app/api/v1/endpoints/delete_wrong_admin.py",
    "app/api/v1/endpoints/clean_system.py",
    "app/api/v1/endpoints/users.py",
    "app/api/v1/endpoints/solicitudes.py",
    "app/api/v1/endpoints/notificaciones.py",
    "app/services/notification_multicanal_service.py",
    "app/models/configuracion_sistema.py",
    "app/api/v1/endpoints/emergency_fix.py",
    "app/api/v1/endpoints/fix_roles.py",
    "app/api/v1/endpoints/configuracion.py",
    "app/api/v1/endpoints/setup_inicial.py",
    "app/api/v1/endpoints/scheduler_notificaciones.py",
    "app/api/v1/endpoints/pagos.py",
    "app/api/v1/endpoints/notificaciones_multicanal.py",
    "app/api/v1/endpoints/inteligencia_artificial.py",
    "app/api/v1/endpoints/conciliacion.py",
    "app/api/v1/endpoints/auth.py",
]

# Patrones de reemplazo
reemplazos = [
    # Listas de roles
    (r'\["ADMINISTRADOR_GENERAL",\s*"GERENTE",\s*"COBRANZAS"\]', '["USER"]'),
    (r'\["ADMINISTRADOR_GENERAL",\s*"COBRANZAS"\]', '["USER"]'),
    (r'\["ADMINISTRADOR_GENERAL",\s*"GERENTE"\]', '["USER"]'),
    (r'\["ADMINISTRADOR_GENERAL"\]', '["USER"]'),
    (r'\["COBRANZAS"\]', '["USER"]'),
    (r'\["GERENTE"\]', '["USER"]'),
    
    # Strings individuales (en comparaciones)
    (r'== "ADMINISTRADOR_GENERAL"', '== "USER"'),
    (r'!= "ADMINISTRADOR_GENERAL"', '!= "USER"'),
    (r'== \'ADMINISTRADOR_GENERAL\'', '== \'USER\''),
    (r'!= \'ADMINISTRADOR_GENERAL\'', '!= \'USER\''),
    
    (r'== "COBRANZAS"', '== "USER"'),
    (r'!= "COBRANZAS"', '!= "USER"'),
    (r'== \'COBRANZAS\'', '== \'USER\''),
    
    (r'== "GERENTE"', '== "USER"'),
    (r'!= "GERENTE"', '!= "USER"'),
    (r'== \'GERENTE\'', '== \'USER\''),
    
    # In clauses con listas
    (r'\.in_\(\["ADMINISTRADOR_GENERAL",\s*"GERENTE",\s*"COBRANZAS"\]\)', '.in_(["USER"])'),
    (r'\.in_\(\["ADMINISTRADOR_GENERAL",\s*"COBRANZAS"\]\)', '.in_(["USER"])'),
    (r'\.in_\(\["ADMINISTRADOR_GENERAL",\s*"GERENTE"\]\)', '.in_(["USER"])'),
    (r'\.in_\(\["ADMINISTRADOR_GENERAL"\]\)', '.in_(["USER"])'),
    
    # user_role in [...]
    (r'user_role in \["ADMINISTRADOR_GENERAL",\s*"GERENTE",\s*"COBRANZAS"\]', 'user_role in ["USER"]'),
    (r'user_role in \["ADMINISTRADOR_GENERAL",\s*"COBRANZAS"\]', 'user_role in ["USER"]'),
    (r'user_role in \["ADMINISTRADOR_GENERAL"\]', 'user_role in ["USER"]'),
    
    # rol in [...]
    (r'rol in \["ADMINISTRADOR_GENERAL",\s*"GERENTE",\s*"COBRANZAS"\]', 'rol in ["USER"]'),
    (r'rol in \["ADMINISTRADOR_GENERAL",\s*"COBRANZAS"\]', 'rol in ["USER"]'),
    (r'rol in \["ADMINISTRADOR_GENERAL"\]', 'rol in ["USER"]'),
    
    # not in [...]
    (r'not in \["ADMINISTRADOR_GENERAL",\s*"GERENTE",\s*"COBRANZAS"\]', 'not in ["USER"]'),
    (r'not in \["ADMINISTRADOR_GENERAL",\s*"COBRANZAS"\]', 'not in ["USER"]'),
    (r'not in \["ADMINISTRADOR_GENERAL"\]', 'not in ["USER"]'),
]

total_cambios = 0

for archivo in archivos:
    ruta_completa = os.path.join(os.path.dirname(__file__), archivo)
    
    if not os.path.exists(ruta_completa):
        print(f"⚠️  Archivo no existe: {archivo}")
        continue
    
    try:
        with open(ruta_completa, 'r', encoding='utf-8') as f:
            contenido = f.read()
        
        contenido_original = contenido
        cambios_archivo = 0
        
        for patron, reemplazo in reemplazos:
            contenido_nuevo = re.sub(patron, reemplazo, contenido)
            if contenido_nuevo != contenido:
                cambios_archivo += contenido.count(re.findall(patron, contenido).__len__() if re.findall(patron, contenido) else 0)
                contenido = contenido_nuevo
        
        if contenido != contenido_original:
            with open(ruta_completa, 'w', encoding='utf-8') as f:
                f.write(contenido)
            
            # Contar cambios reales
            cambios = len(re.findall(r'ADMINISTRADOR_GENERAL|GERENTE|COBRANZAS', contenido_original)) - len(re.findall(r'ADMINISTRADOR_GENERAL|GERENTE|COBRANZAS', contenido))
            print(f"✅ {archivo}: {cambios} reemplazos")
            total_cambios += cambios
        else:
            print(f"⚪ {archivo}: Sin cambios")
    
    except Exception as e:
        print(f"❌ Error en {archivo}: {e}")

print(f"\n🎯 TOTAL: {total_cambios} reemplazos en {len(archivos)} archivos")

