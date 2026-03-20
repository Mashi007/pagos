# -*- coding: utf-8 -*-
"""
Script de validacion: Verificar que el servicio de notificaciones con PDF esta correctamente integrado.
"""

import os
import sys

print("=" * 80)
print("VALIDACION DE INTEGRACION: Notificaciones LIQUIDADO con PDF")
print("=" * 80)

# Obtener ruta base
ruta_base = os.path.dirname(os.path.abspath(__file__))

# 1. Verificar que los archivos modificados existen
print("\n1. Verificando archivos modificados...")
archivos_requeridos = {
    'Notificacion Service': os.path.join(ruta_base, 'app', 'services', 'liquidado_notificacion_service.py'),
    'Scheduler': os.path.join(ruta_base, 'app', 'services', 'liquidado_scheduler.py'),
    'Main': os.path.join(ruta_base, 'app', 'main.py'),
}

todos_existen = True
for nombre, ruta in archivos_requeridos.items():
    if os.path.exists(ruta):
        print(f"   OK: {nombre} ({ruta})")
    else:
        print(f"   FALTA: {nombre} ({ruta})")
        todos_existen = False

if not todos_existen:
    print("\n   ERROR: No se encontraron todos los archivos requeridos")
    sys.exit(1)

# 2. Verificar importaciones en notificacion_service.py
print("\n2. Verificando importaciones en liquidado_notificacion_service.py...")
ruta_notif = archivos_requeridos['Notificacion Service']

with open(ruta_notif, 'r', encoding='utf-8') as f:
    contenido = f.read()
    
importaciones_requeridas = [
    'from app.services.estado_cuenta_pdf import generar_pdf_estado_cuenta',
    'from app.core.email import send_email',
    'from app.services.cuota_estado import estado_cuota_para_mostrar',
    '_generar_pdf_estado_cuenta',
    'attachments',
]

for importacion in importaciones_requeridas:
    if importacion in contenido:
        print(f"   OK: {importacion}")
    else:
        print(f"   FALTA: {importacion}")

# 3. Verificar que el scheduler importa notificacion_service
print("\n3. Verificando integracion en liquidado_scheduler.py...")
ruta_scheduler = archivos_requeridos['Scheduler']

with open(ruta_scheduler, 'r', encoding='utf-8') as f:
    contenido_scheduler = f.read()

integraciones_scheduler = [
    'from app.services.liquidado_notificacion_service import notificacion_service',
    'notificacion_service.crear_notificacion',
    'prestamos_a_liquidar',
]

for integracion in integraciones_scheduler:
    if integracion in contenido_scheduler:
        print(f"   OK: {integracion}")
    else:
        print(f"   FALTA: {integracion}")

# 4. Verificar que main.py tiene los imports necesarios
print("\n4. Verificando integracion en main.py...")
ruta_main = archivos_requeridos['Main']

with open(ruta_main, 'r', encoding='utf-8') as f:
    contenido_main = f.read()

integraciones_main = [
    'from app.services.liquidado_scheduler import liquidado_scheduler',
    'prestamos_liquidado_automatico',
]

for integracion in integraciones_main:
    if integracion in contenido_main:
        print(f"   OK: {integracion}")
    else:
        print(f"   FALTA: {integracion}")

print("\n" + "=" * 80)
print("VALIDACION COMPLETADA")
print("=" * 80)
print("\nProximos pasos:")
print("1. Reiniciar la aplicacion: uvicorn app.main:app --reload")
print("2. Monitorear logs en busca de: [LIQUIDADO_NOTIF]")
print("3. Esperar a las 9 PM (21:00) o cambiar hora del scheduler para testing")
print("4. Verificar correos recibidos con PDF adjunto")
print("5. Consultar BD: SELECT * FROM envio_notificacion WHERE tipo=liquidado")
