"""
Modelo de 3 cuentas de email para RapiCredit.
- Cuenta 1: Cobros / Recibos / recordatorios (pagos@)
- Cuenta 2: Estado de cuenta / Finiquito (tucuenta@)
- Cuenta 3: Notificaciones mora (notificaciones@)

La clave en BD es email_config. Formato versionado:
- version 1 (legacy): un solo objeto plano (smtp_host, smtp_user, ...).
- version 2: { "version": 2, "cuentas": [ c1, c2, c3 ], "asignacion": { ... } }
"""
from typing import Any, Dict, List, Optional

NUM_CUENTAS = 3
# Cuenta 4 (recuerda@) eliminada; indices legacy > 3 se mapean a pagos@ (1).
INDICE_CUENTA_LEGACY_RECUERDA = 4

SERVICIO_COBROS = "cobros"
SERVICIO_ESTADO_CUENTA = "estado_cuenta"
SERVICIO_NOTIFICACIONES = "notificaciones"
SERVICIO_RECIBOS = "recibos"
SERVICIO_FINIQUITO = "finiquito"

ASIGNACION_DEFAULT = {
    "cobros": 1,
    "estado_cuenta": 2,
    "notificaciones_tab": {
        "d_2_antes_vencimiento": 1,
        "dias_5": 1,
        "dias_1": 1,
        "hoy": 1,
        "dias_1_retraso": 2,
        "dias_10_retraso": 3,
        "prejudicial": 3,
        "dias_3_retraso": 3,
        "dias_5_retraso": 3,
        "mora_90": 3,
    },
    "recibos": 1,
}

CAMPOS_CUENTA = [
    "smtp_host", "smtp_port", "smtp_user", "smtp_password", "from_email", "from_name",
    "smtp_use_tls", "imap_host", "imap_port", "imap_user", "imap_password", "imap_use_ssl",
]


def normalizar_indice_cuenta(idx: Any) -> int:
    """Indices validos 1-3. Legacy cuenta 4 (recuerda@) -> 1 (pagos@)."""
    try:
        n = int(idx)
    except (TypeError, ValueError):
        return 1
    if n > NUM_CUENTAS:
        return 1
    return max(1, min(n, NUM_CUENTAS))


def normalizar_asignacion(asignacion: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    base = dict(ASIGNACION_DEFAULT)
    raw = dict(asignacion or {})
    for key in ("cobros", "estado_cuenta", "recibos"):
        if key in raw:
            base[key] = normalizar_indice_cuenta(raw[key])
    tab_in = dict(raw.get("notificaciones_tab") or {})
    tab_out = dict(base.get("notificaciones_tab") or {})
    for k, v in tab_in.items():
        tab_out[k] = normalizar_indice_cuenta(v)
    base["notificaciones_tab"] = tab_out
    return base


def normalizar_config_v2(data: Dict[str, Any]) -> Dict[str, Any]:
    """Recorta a 3 cuentas y remapea asignaciones legacy (recuerda@)."""
    if not data or data.get("version") != 2:
        return data
    out = dict(data)
    cuentas = [dict(c) if isinstance(c, dict) else cuenta_vacia() for c in (out.get("cuentas") or [])]
    cuentas = cuentas[:NUM_CUENTAS]
    while len(cuentas) < NUM_CUENTAS:
        cuentas.append(cuenta_vacia())
    out["cuentas"] = cuentas
    out["asignacion"] = normalizar_asignacion(out.get("asignacion"))
    return out


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
    """Convierte config legacy (un solo bloque) a version 2 con 3 cuentas."""
    if data.get("version") == 2 and "cuentas" in data:
        return normalizar_config_v2(data)
    cuentas: List[Dict[str, Any]] = []
    base = {k: v for k, v in data.items() if k in CAMPOS_CUENTA or k in ("smtp_host", "smtp_port", "smtp_user", "smtp_password", "from_email", "from_name", "smtp_use_tls", "imap_host", "imap_port", "imap_user", "imap_password", "imap_use_ssl")}
    cuenta1 = cuenta_vacia()
    for k, v in base.items():
        if k in cuenta1 and v is not None:
            cuenta1[k] = v
    cuentas.append(cuenta1)
    for _ in range(NUM_CUENTAS - 1):
        cuentas.append(cuenta_vacia())
    asignacion = normalizar_asignacion(data.get("asignacion"))
    return {
        "version": 2,
        "cuentas": cuentas,
        "asignacion": asignacion,
        "modo_pruebas": data.get("modo_pruebas", "false"),
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
    """Devuelve el indice de cuenta (1-3) para el servicio y opcionalmente tipo_tab."""
    asig = normalizar_asignacion(asignacion)
    if servicio == SERVICIO_COBROS:
        return asig["cobros"]
    if servicio in (SERVICIO_ESTADO_CUENTA, SERVICIO_FINIQUITO):
        return asig["estado_cuenta"]
    if servicio == SERVICIO_RECIBOS:
        return asig["recibos"]
    if servicio == SERVICIO_NOTIFICACIONES and tipo_tab:
        tab_map = asig.get("notificaciones_tab") or {}
        tab = (tipo_tab or "").strip()
        # PAGO_3_DIAS_ANTES (General/Fechas) usa la misma cuenta que sidebar 3 dias antes.
        if tab == "dias_3":
            tab = "d_2_antes_vencimiento"
        return int(tab_map.get(tab, 3))
    if servicio == SERVICIO_NOTIFICACIONES:
        return int(asig.get("notificaciones_tab", {}).get("dias_5", 3))
    return 1
