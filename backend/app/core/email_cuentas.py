"""
Modelo de 4 cuentas de email para RapiCredit.
- Cuenta 1: Cobros (rapicredit-cobros)
- Cuenta 2: Estado de cuenta (rapicredit-estadocuenta)
- Cuentas 3 y 4: Notificaciones (cada pestaña puede elegir cuenta 3 o 4)

La clave en BD es email_config. Formato versionado:
- version 1 (legacy): un solo objeto plano (smtp_host, smtp_user, ...).
- version 2: { "version": 2, "cuentas": [ c1, c2, c3, c4 ], "asignacion": { "cobros": 1, "estado_cuenta": 2, "notificaciones_tab": { "dias_5": 3, ... } } }
"""
from typing import Any, Dict, List, Optional

NUM_CUENTAS = 4
SERVICIO_COBROS = "cobros"
SERVICIO_ESTADO_CUENTA = "estado_cuenta"
SERVICIO_NOTIFICACIONES = "notificaciones"
# Recibos: estado de cuenta por correo tras pagos conciliados (scheduler / POST manual).
SERVICIO_RECIBOS = "recibos"
# Portal Finiquito (OTP): misma cuenta SMTP que estado de cuenta salvo que se asigne otro indice en el futuro.
SERVICIO_FINIQUITO = "finiquito"

# Índices 1-based para la UI (Cuenta 1, 2, 3, 4)
ASIGNACION_DEFAULT = {
    "cobros": 1,
    "estado_cuenta": 2,
    "notificaciones_tab": {
        "d_2_antes_vencimiento": 3,
        "dias_1_retraso": 3,
        "dias_10_retraso": 3,
        "prejudicial": 3,
    },
    "recibos": 3,
}

CAMPOS_CUENTA = [
    "smtp_host", "smtp_port", "smtp_user", "smtp_password", "from_email", "from_name",
    "smtp_use_tls", "imap_host", "imap_port", "imap_user", "imap_password", "imap_use_ssl",
]


def cuenta_vacia() -> Dict[str, Any]:
    """Devuelve un diccionario de cuenta vacía (valores por defecto)."""
    return {
        "smtp_host": "smtp.gmail.com",
        "smtp_port": "587",
        "smtp_user": "",
        "smtp_password": "",
        "from_email": "",
        "from_name": "RapiCredit",
        "smtp_use_tls": "true",
        "imap_host": "",
        "imap_port": "993",
        "imap_user": "",
        "imap_password": "",
        "imap_use_ssl": "true",
    }


def migrar_config_v1_a_v2(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convierte config legacy (un solo bloque) a version 2 con 4 cuentas."""
    if data.get("version") == 2 and "cuentas" in data:
        return data
    cuentas: List[Dict[str, Any]] = []
    base = {k: v for k, v in data.items() if k in CAMPOS_CUENTA or k in ("smtp_host", "smtp_port", "smtp_user", "smtp_password", "from_email", "from_name", "smtp_use_tls", "imap_host", "imap_port", "imap_user", "imap_password", "imap_use_ssl")}
    cuenta1 = cuenta_vacia()
    for k, v in base.items():
        if k in cuenta1 and v is not None:
            cuenta1[k] = v
    cuentas.append(cuenta1)
    for _ in range(NUM_CUENTAS - 1):
        cuentas.append(cuenta_vacia())
    asignacion = data.get("asignacion") or ASIGNACION_DEFAULT
    if "notificaciones_tab" not in asignacion or "recibos" not in asignacion:
        asignacion = dict(asignacion)
        if "notificaciones_tab" not in asignacion:
            asignacion["notificaciones_tab"] = ASIGNACION_DEFAULT["notificaciones_tab"]
        if "recibos" not in asignacion:
            asignacion["recibos"] = ASIGNACION_DEFAULT["recibos"]
    return {
        "version": 2,
        "cuentas": cuentas,
        "asignacion": asignacion,
        "modo_pruebas": data.get("modo_pruebas", "true"),
        "email_pruebas": data.get("email_pruebas", ""),
        "emails_pruebas": data.get("emails_pruebas"),
        "email_activo": data.get("email_activo", "true"),
        "email_activo_notificaciones": data.get("email_activo_notificaciones", "true"),
        "email_activo_informe_pagos": data.get("email_activo_informe_pagos", "true"),
        "email_activo_estado_cuenta": data.get("email_activo_estado_cuenta", "true"),
        "email_activo_finiquito": data.get("email_activo_finiquito", "true"),
        "email_activo_cobros": data.get("email_activo_cobros", "true"),
        "email_activo_campanas": data.get("email_activo_campanas", "true"),
        "email_activo_tickets": data.get("email_activo_tickets", "true"),
        "email_activo_recibos": data.get("email_activo_recibos", "true"),
        "modo_pruebas_notificaciones": data.get("modo_pruebas_notificaciones", "false"),
        "modo_pruebas_informe_pagos": data.get("modo_pruebas_informe_pagos", "false"),
        "modo_pruebas_estado_cuenta": data.get("modo_pruebas_estado_cuenta", "false"),
        "modo_pruebas_finiquito": data.get("modo_pruebas_finiquito", "false"),
        "modo_pruebas_cobros": data.get("modo_pruebas_cobros", "false"),
        "modo_pruebas_campanas": data.get("modo_pruebas_campanas", "false"),
        "modo_pruebas_tickets": data.get("modo_pruebas_tickets", "false"),
        "modo_pruebas_recibos": data.get("modo_pruebas_recibos", "false"),
        "tickets_notify_emails": data.get("tickets_notify_emails", ""),
    }


def obtener_indice_cuenta(servicio: Optional[str], tipo_tab: Optional[str], asignacion: Dict[str, Any]) -> int:
    """
    Devuelve el índice de cuenta (1-4) para el servicio y opcionalmente tipo_tab.
    asignacion: { "cobros": 1, "estado_cuenta": 2, "notificaciones_tab": { "dias_5": 3, ... } }
    """
    if servicio == SERVICIO_COBROS:
        return int(asignacion.get("cobros", 1))
    if servicio in (SERVICIO_ESTADO_CUENTA, SERVICIO_FINIQUITO):
        return int(asignacion.get("estado_cuenta", 2))
    if servicio == SERVICIO_RECIBOS:
        return int(asignacion.get("recibos", 3))
    if servicio == SERVICIO_NOTIFICACIONES and tipo_tab:
        tab_map = asignacion.get("notificaciones_tab") or {}
        return int(tab_map.get(tipo_tab, 3))
    if servicio == SERVICIO_NOTIFICACIONES:
        return int(asignacion.get("notificaciones_tab", {}).get("dias_5", 3))
    return 1
