#!/usr/bin/env python3
"""
Script para activar variables CUOTAS_VENCIDAS y FECHAS_CUOTAS_PENDIENTES en plantillas de cobranza.
Ejecutar desde la raíz del repo: python backend/patch_cobranza_vars.py
"""
import os

BASE = os.path.dirname(os.path.abspath(__file__))

# 1) plantilla_cobranza.py
path1 = os.path.join(BASE, "app", "services", "plantilla_cobranza.py")
with open(path1, "r", encoding="utf-8") as f:
    content1 = f.read()

old_return = """            total_adeudado += m

    return {
        "CLIENTES.TRATAMIENTO": tratamiento,
        "CLIENTES.NOMBRE_COMPLETO": cliente_nombres or "",
        "CLIENTES.CEDULA": cedula or "",
        "PRESTAMOS.ID": prestamo_id,
        "IDPRESTAMO": prestamo_id,
        "NUMEROCORRELATIVO": numero_correlativo,
        "TOTAL_ADEUDADO": _format_monto(total_adeudado),
        "FECHA_CARTA": f,
        "CUOTAS.VENCIMIENTOS": lista,
        "cuotas_vencidas": lista,
        "LOGO_URL": url_logo,
    }"""

new_return = """            total_adeudado += m

    cuotas_vencidas_count = len(lista)
    fechas_cuotas_pendientes_str = ", ".join(
        _format_fecha(c.get("fecha_vencimiento")) for c in lista
    )

    return {
        "CLIENTES.TRATAMIENTO": tratamiento,
        "CLIENTES.NOMBRE_COMPLETO": cliente_nombres or "",
        "CLIENTES.CEDULA": cedula or "",
        "PRESTAMOS.ID": prestamo_id,
        "IDPRESTAMO": prestamo_id,
        "NUMEROCORRELATIVO": numero_correlativo,
        "TOTAL_ADEUDADO": _format_monto(total_adeudado),
        "FECHA_CARTA": f,
        "CUOTAS.VENCIMIENTOS": lista,
        "cuotas_vencidas": lista,
        "CUOTAS_VENCIDAS": cuotas_vencidas_count,
        "FECHAS_CUOTAS_PENDIENTES": fechas_cuotas_pendientes_str,
        "LOGO_URL": url_logo,
    }"""

if old_return in content1:
    content1 = content1.replace(old_return, new_return)
    with open(path1, "w", encoding="utf-8") as f:
        f.write(content1)
    print("OK plantilla_cobranza.py: CUOTAS_VENCIDAS y FECHAS_CUOTAS_PENDIENTES añadidas al contexto.")
else:
    print("AVISO plantilla_cobranza.py: bloque no encontrado (quizá ya aplicado).")

# 2) notificaciones.py
path2 = os.path.join(BASE, "app", "api", "v1", "endpoints", "notificaciones.py")
with open(path2, "r", encoding="utf-8") as f:
    content2 = f.read()

vars_old = """_VARS_COBRANZA = (
    "{{FECHA_CARTA}}",
    "{{PRESTAMOS.ID}}",
    "{{IDPRESTAMO}}",
    "{{NUMEROCORRELATIVO}}",
    "{{CLIENTES.NOMBRE_COMPLETO}}",
    "{{CLIENTES.CEDULA}}",
    "{{TABLA_CUOTAS_PENDIENTES}}",
    "{{#CUOTAS.VENCIMIENTOS}}",
)"""
vars_new = """_VARS_COBRANZA = (
    "{{FECHA_CARTA}}",
    "{{PRESTAMOS.ID}}",
    "{{IDPRESTAMO}}",
    "{{NUMEROCORRELATIVO}}",
    "{{CLIENTES.NOMBRE_COMPLETO}}",
    "{{CLIENTES.CEDULA}}",
    "{{TABLA_CUOTAS_PENDIENTES}}",
    "{{#CUOTAS.VENCIMIENTOS}}",
    "{{CUOTAS_VENCIDAS}}",
    "{{FECHAS_CUOTAS_PENDIENTES}}",
)"""
if vars_old in content2:
    content2 = content2.replace(vars_old, vars_new)
    print("OK notificaciones.py: _VARS_COBRANZA actualizado.")
else:
    print("AVISO notificaciones.py: _VARS_COBRANZA no encontrado o ya actualizado.")

placeholder_old = """        "cuotas_vencidas": [
            {"numero": "{{CUOTA.NUMERO}}", "fecha_vencimiento": "{{CUOTA.FECHA_VENCIMIENTO}}", "monto": "{{CUOTA.MONTO}}"}
        ],
    }"""
placeholder_new = """        "cuotas_vencidas": [
            {"numero": "{{CUOTA.NUMERO}}", "fecha_vencimiento": "{{CUOTA.FECHA_VENCIMIENTO}}", "monto": "{{CUOTA.MONTO}}"}
        ],
        "CUOTAS_VENCIDAS": "{{CUOTAS_VENCIDAS}}",
        "FECHAS_CUOTAS_PENDIENTES": "{{FECHAS_CUOTAS_PENDIENTES}}",
    }"""
if placeholder_old in content2:
    content2 = content2.replace(placeholder_old, placeholder_new)
    print("OK notificaciones.py: _contexto_cobranza_placeholder actualizado.")
else:
    print("AVISO notificaciones.py: placeholder no encontrado o ya aplicado.")

with open(path2, "w", encoding="utf-8") as f:
    f.write(content2)

print("Listo.")
