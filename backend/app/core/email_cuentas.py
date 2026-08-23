"""
Modelo de 4 cuentas de email para RapiCredit.
- Cuenta 1: Cobros / Recibos / recordatorios (pagos@)
- Cuenta 2: Estado de cuenta (tucuenta@)
- Cuenta 3: Notificaciones mora (notificaciones@)
- Cuenta 4: 1 Cuota (recuerda@)
- Dia siguiente al vencimiento: cuenta 1 (pagos@)

La clave en BD es email_config. Formato versionado:
- version 1 (legacy): un solo objeto plano (smtp_host, smtp_user, ...).
- version 2: { "version": 2, "cuentas": [ c1..c4 ], "asignacion": { ... } }
"""
from typing import Any, Dict, List, Optional

NUM_CUENTAS = 4
INDICE_CUENTA_PAGOS = 1
INDICE_CUENTA_RECUERDA = 4

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
        "dias_1_retraso": 1,
        "dias_10_retraso": 4,
        "prejudicial": 3,
        "cobranzas": 3,
        "cuotas_4_mas": 3,
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
    """Indices validos 1-4 (cuenta 4 = recuerda@)."""
    try:
        n = int(idx)
    except (TypeError, ValueError):
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
    # Producto: 1 Cuota desde recuerda@; dia siguiente desde pagos@; 2+ desde notificaciones@.
    tab_out["dias_10_retraso"] = INDICE_CUENTA_RECUERDA
    tab_out["dias_1_retraso"] = INDICE_CUENTA_PAGOS
    tab_out["cobranzas"] = 3
    tab_out["cuotas_4_mas"] = 3
    tab_out["prejudicial"] = 3
    base["notificaciones_tab"] = tab_out
    return base


def normalizar_config_v2(data: Dict[str, Any]) -> Dict[str, Any]:
    """Asegura exactamente NUM_CUENTAS (4) y normaliza asignacion."""
    if not data or data.get("version") != 2:
        return data
    out = dict(data)
    cuentas = [dict(c) if isinstance(c, dict) else cuenta_vacia() for c in (out.get("cuentas") or [])]
    cuentas = cuentas[:NUM_CUENTAS]
    while len(cuentas) < NUM_CUENTAS:
        cuentas.append(cuenta_vacia())
    out["cuentas"] = [
        asegurar_identidad_cuenta(c, i + 1) for i, c in enumerate(cuentas)
    ]
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


# Identidad canónica por índice (1-based) — no incluye contraseñas.
CUENTA_IDENTIDAD_DEFAULT: Dict[int, Dict[str, str]] = {
    1: {
        "smtp_user": "pagos@rapicreditca.com",
        "from_email": "pagos@rapicreditca.com",
        "imap_user": "pagos@rapicreditca.com",
        "from_name": "RapiCredit",
    },
    2: {
        "smtp_user": "tucuenta@rapicreditca.com",
        "from_email": "tucuenta@rapicreditca.com",
        "imap_user": "tucuenta@rapicreditca.com",
        "from_name": "RapiCredit",
    },
    3: {
        "smtp_user": "notificaciones@rapicreditca.com",
        "from_email": "notificaciones@rapicreditca.com",
        "imap_user": "notificaciones@rapicreditca.com",
        "from_name": "RapiCredit",
    },
    4: {
        "smtp_user": "recuerda@rapicreditca.com",
        "from_email": "recuerda@rapicreditca.com",
        "imap_user": "recuerda@rapicreditca.com",
        "from_name": "RapiCredit",
    },
}


def asegurar_identidad_cuenta(cuenta: Dict[str, Any], indice_1based: int) -> Dict[str, Any]:
    """Rellena smtp_user/from_email/imap_user si faltan, segun buzon canonico."""
    out = dict(cuenta or {})
    ident = CUENTA_IDENTIDAD_DEFAULT.get(int(indice_1based)) or {}
    for k, v in ident.items():
        cur = str(out.get(k) or "").strip()
        if not cur:
            out[k] = v
    if not str(out.get("smtp_host") or "").strip():
        out["smtp_host"] = "smtp.gmail.com"
    if not str(out.get("smtp_port") or "").strip():
        out["smtp_port"] = "587"
    if not str(out.get("imap_host") or "").strip():
        out["imap_host"] = "imap.gmail.com"
    if not str(out.get("imap_port") or "").strip():
        out["imap_port"] = "993"
    return out


def migrar_config_v1_a_v2(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convierte config legacy (un solo bloque) a version 2 con 4 cuentas."""
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
    """Devuelve el indice de cuenta (1-4) para el servicio y opcionalmente tipo_tab."""
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


# tipo_caso (config envios) -> tipo_tab SMTP (notificaciones_tab)
TIPO_CASO_A_TAB_SMTP = {
    "PREJUDICIAL": "prejudicial",
    "COBRANZAS_EXCEL": "cobranzas",
    "CUOTAS_4_MAS": "cuotas_4_mas",
    "PAGO_1_DIA_ATRASADO": "dias_1_retraso",
    "PAGO_10_DIAS_ATRASADO": "dias_10_retraso",
    "PAGO_2_DIAS_ANTES_PENDIENTE": "d_2_antes_vencimiento",
    "PAGO_5_DIAS_ANTES": "dias_5",
    "PAGO_3_DIAS_ANTES": "d_2_antes_vencimiento",
    "PAGO_1_DIA_ANTES": "dias_1",
}


def indice_cuenta_para_tipo_caso_notificacion(
    tipo_caso: str, asignacion: Optional[Dict[str, Any]] = None
) -> int:
    """Indice SMTP (1-4) del caso de notificacion. Distintos indices = distintos buzones Gmail."""
    tipo = str(tipo_caso or "").strip()
    if tipo == "ESTADO_CUENTA":
        return obtener_indice_cuenta(
            SERVICIO_ESTADO_CUENTA, None, asignacion or {}
        )
    tab = TIPO_CASO_A_TAB_SMTP.get(tipo, "")
    if tipo == "PAGO_2_DIAS_ANTES_PENDIENTE":
        tab = "d_2_antes_vencimiento"
    return obtener_indice_cuenta(SERVICIO_NOTIFICACIONES, tab or None, asignacion or {})
