"""
Endpoints para configuracion de 3 cuentas de email.
GET/PUT /configuracion/email/cuentas devuelven/aceptan { version: 2, cuentas: [c1,c2,c3], asignacion }.
Cuenta 1 = pagos@, 2 = tucuenta@, 3 = notificaciones@.
"""
import json
import logging
from typing import Any, List, Optional

from fastapi import APIRouter, Body, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.email_config_holder import (
    CLAVE_EMAIL_CONFIG,
    SENSITIVE_FIELDS,
    invalidate_email_config_cache,
    prepare_for_db_storage,
    update_from_api,
)
from app.core.email_cuentas import (
    NUM_CUENTAS,
    ASIGNACION_DEFAULT,
    SERVICIO_FINIQUITO,
    cuenta_vacia,
    migrar_config_v1_a_v2,
    normalizar_asignacion,
    normalizar_indice_cuenta,
)
from app.models.configuracion import Configuracion
from app.api.v1.endpoints.email_config_validacion import validar_config_email_para_guardar

logger = logging.getLogger(__name__)
router = APIRouter()

# Valores por defecto al crear email_config v2 por primera vez (sin fila previa).
_DEFAULTS_EMAIL_V2_GLOBALS: dict[str, Any] = {
    "modo_pruebas": "false",
    "email_pruebas": "",
    "email_activo": "true",
    "email_activo_notificaciones": "true",
    "email_activo_informe_pagos": "true",
    "email_activo_estado_cuenta": "true",
    "email_activo_finiquito": "true",
    "email_activo_cobros": "true",
    "email_activo_campanas": "true",
    "email_activo_tickets": "true",
    "email_activo_recibos": "true",
    "modo_pruebas_notificaciones": "false",
    "modo_pruebas_informe_pagos": "false",
    "modo_pruebas_estado_cuenta": "false",
    "modo_pruebas_finiquito": "false",
    "modo_pruebas_cobros": "false",
    "modo_pruebas_campanas": "false",
    "modo_pruebas_tickets": "false",
    "modo_pruebas_recibos": "false",
    "tickets_notify_emails": "",
    "recibos_bcc_emails": [],
}


def _email_v2_globals_for_api(data: dict) -> dict[str, Any]:
    """Expone en GET /cuentas las mismas claves globales que usa el holder (round-trip al guardar)."""
    out: dict[str, Any] = {}
    for k, default in _DEFAULTS_EMAIL_V2_GLOBALS.items():
        out[k] = data.get(k, default)
    if data.get("emails_pruebas") is not None:
        out["emails_pruebas"] = data.get("emails_pruebas")
    rbe = data.get("recibos_bcc_emails")
    if isinstance(rbe, list):
        out["recibos_bcc_emails"] = rbe
    else:
        out["recibos_bcc_emails"] = []
    return out


def _is_password_masked(v: Any) -> bool:
    if v is None or not isinstance(v, str):
        return True
    s = (v or "").strip()
    return s in ("", "***")


def _secret_field_stored(c: dict, field: str) -> bool:
    """True si hay contraseña persistida (encriptada en BD o legacy en claro)."""
    enc_key = f"{field}_encriptado"
    enc = c.get(enc_key)
    if enc is not None and str(enc).strip():
        return True
    val = c.get(field)
    if val is None:
        return False
    s = str(val).strip()
    return bool(s) and not _is_password_masked(s)


def _mask_cuenta(c: dict) -> dict:
    """Copia la cuenta enmascarando contrasenas y sin exponer campos _encriptado."""
    smtp_guardada = _secret_field_stored(c, "smtp_password")
    imap_guardada = _secret_field_stored(c, "imap_password")
    out = {k: v for k, v in c.items() if not k.endswith("_encriptado")}
    for f in SENSITIVE_FIELDS:
        if out.get(f):
            out[f] = "***"
    out["smtp_password_guardada"] = smtp_guardada
    out["imap_password_guardada"] = imap_guardada
    return out


def _load_raw_from_db(db) -> Optional[dict]:
    row = db.get(Configuracion, CLAVE_EMAIL_CONFIG)
    if not row or not row.valor:
        return None
    try:
        return json.loads(row.valor)
    except Exception:
        return None


def _asignacion_tiene_indice_legacy(raw: dict) -> bool:
    asig = raw.get("asignacion") or {}
    for key in ("cobros", "estado_cuenta", "recibos"):
        try:
            if int(asig.get(key, 0)) > NUM_CUENTAS:
                return True
        except (TypeError, ValueError):
            pass
    for val in (asig.get("notificaciones_tab") or {}).values():
        try:
            if int(val) > NUM_CUENTAS:
                return True
        except (TypeError, ValueError):
            pass
    return False


def _email_config_needs_migration_persist(raw: dict) -> bool:
    if not raw or not isinstance(raw, dict):
        return False
    if raw.get("version") != 2:
        return True
    if len(raw.get("cuentas") or []) > NUM_CUENTAS:
        return True
    if _asignacion_tiene_indice_legacy(raw):
        return True
    migrated = migrar_config_v1_a_v2(raw)
    return normalizar_asignacion(migrated.get("asignacion")) != normalizar_asignacion(
        raw.get("asignacion")
    )


def _persist_migrated_email_config(db: Session, raw: dict) -> dict:
    """Normaliza v1/4 cuentas a v2/3 en BD sin perder claves encriptadas."""
    migrated = migrar_config_v1_a_v2(raw)
    payload_data: dict[str, Any] = dict(raw)
    payload_data["version"] = 2
    payload_data["asignacion"] = normalizar_asignacion(migrated.get("asignacion"))

    raw_cuentas = list(raw.get("cuentas") or [])
    mig_cuentas = migrated.get("cuentas") or []
    cuentas_bd: List[dict] = []
    for i in range(NUM_CUENTAS):
        if raw.get("version") == 2 and i < len(raw_cuentas) and isinstance(raw_cuentas[i], dict):
            cuentas_bd.append(dict(raw_cuentas[i]))
        else:
            base = dict(mig_cuentas[i] if i < len(mig_cuentas) else cuenta_vacia())
            cuentas_bd.append(prepare_for_db_storage(base))
    payload_data["cuentas"] = cuentas_bd

    try:
        row = db.get(Configuracion, CLAVE_EMAIL_CONFIG)
        payload_str = json.dumps(payload_data, ensure_ascii=False)
        if row:
            row.valor = payload_str
        else:
            db.add(Configuracion(clave=CLAVE_EMAIL_CONFIG, valor=payload_str))
        db.commit()
        invalidate_email_config_cache()
        logger.info(
            "email_config migrado y persistido en BD (version=2, cuentas=%d)",
            len(cuentas_bd),
        )
    except Exception as e:
        logger.warning("No se pudo auto-persistir migracion email_config: %s", e)
        db.rollback()
    return migrated


@router.get("/cuentas")
def get_email_cuentas(db: Session = Depends(get_db)):
    """Devuelve la configuracion de 3 cuentas y asignacion. contrasenas enmascaradas."""
    data = _load_raw_from_db(db)
    if not data:
        out = {
            "version": 2,
            "cuentas": [cuenta_vacia() for _ in range(NUM_CUENTAS)],
            "asignacion": dict(ASIGNACION_DEFAULT),
            **_email_v2_globals_for_api({}),
        }
        for c in out["cuentas"]:
            _mask_cuenta(c)
        return out
    if _email_config_needs_migration_persist(data):
        migrated = _persist_migrated_email_config(db, data)
    else:
        migrated = migrar_config_v1_a_v2(data)
    cuentas = list(migrated["cuentas"])
    for i, c in enumerate(cuentas):
        if isinstance(c, dict):
            cuentas[i] = _mask_cuenta(dict(c))
    return {
        "version": 2,
        "cuentas": cuentas,
        "asignacion": migrated.get("asignacion") or ASIGNACION_DEFAULT,
        **_email_v2_globals_for_api(migrated if isinstance(migrated, dict) else {}),
    }


class CuentaEmail(BaseModel):
    smtp_host: Optional[str] = None
    smtp_port: Optional[str] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    from_email: Optional[str] = None
    from_name: Optional[str] = None
    smtp_use_tls: Optional[str] = None
    imap_host: Optional[str] = None
    imap_port: Optional[str] = None
    imap_user: Optional[str] = None
    imap_password: Optional[str] = None
    imap_use_ssl: Optional[str] = None


class EmailCuentasUpdate(BaseModel):
    cuentas: List[CuentaEmail]
    asignacion: Optional[dict] = None
    modo_pruebas: Optional[str] = None
    email_pruebas: Optional[str] = None
    email_activo: Optional[str] = None
    email_activo_notificaciones: Optional[str] = None
    email_activo_informe_pagos: Optional[str] = None
    email_activo_estado_cuenta: Optional[str] = None
    email_activo_finiquito: Optional[str] = None
    email_activo_cobros: Optional[str] = None
    email_activo_campanas: Optional[str] = None
    email_activo_tickets: Optional[str] = None
    email_activo_recibos: Optional[str] = None
    tickets_notify_emails: Optional[str] = None
    modo_pruebas_notificaciones: Optional[str] = None
    modo_pruebas_informe_pagos: Optional[str] = None
    modo_pruebas_estado_cuenta: Optional[str] = None
    modo_pruebas_finiquito: Optional[str] = None
    modo_pruebas_cobros: Optional[str] = None
    modo_pruebas_campanas: Optional[str] = None
    modo_pruebas_tickets: Optional[str] = None
    modo_pruebas_recibos: Optional[str] = None
    emails_pruebas: Optional[List[str]] = None
    recibos_bcc_emails: Optional[List[str]] = None


def _normalizar_recibos_bcc_emails(raw: Any) -> List[str]:
    """Hasta 2 correos válidos en CCO (BCC) para envíos Recibos; sin duplicados (case-insensitive)."""
    parts: List[str] = []
    if isinstance(raw, list):
        for x in raw:
            s = (str(x) if x is not None else "").strip()
            if s:
                parts.append(s)
    elif isinstance(raw, str) and raw.strip():
        for chunk in raw.replace(";", ",").split(","):
            s = chunk.strip()
            if s:
                parts.append(s)
    out: List[str] = []
    seen_lower: set[str] = set()
    for p in parts:
        if "@" not in p or "." not in p.split("@", 1)[-1]:
            continue
        low = p.lower()
        if low in seen_lower:
            continue
        seen_lower.add(low)
        out.append(p)
        if len(out) >= 2:
            break
    return out


def _get_existing_decrypted_password(existing_data: Optional[dict], account_index: int, field: str) -> Optional[str]:
    """Obtiene la contrasena ya guardada (desencriptada) para no sobrescribirla cuando el usuario no la cambia (***)."""
    if not existing_data or account_index < 0:
        return None
    cuentas = existing_data.get("cuentas") or []
    if account_index >= len(cuentas):
        return None
    cuenta = cuentas[account_index]
    if not isinstance(cuenta, dict):
        return None
    enc_key = f"{field}_encriptado"
    enc_val = cuenta.get(enc_key)
    if not enc_val:
        return cuenta.get(field)
    try:
        from app.core.crypto import decrypt_value
        if isinstance(enc_val, str):
            enc_bytes = bytes.fromhex(enc_val)
        else:
            enc_bytes = enc_val
        dec = decrypt_value(enc_bytes)
        return dec if isinstance(dec, str) else (dec.decode("utf-8") if dec else None)
    except Exception:
        return None



@router.put("/cuentas")
def put_email_cuentas(payload: EmailCuentasUpdate = Body(...), db: Session = Depends(get_db)):
    """Guarda las 3 cuentas y la asignacion. Encripta contrasenas en BD."""
    existing_data = _load_raw_from_db(db)
    cuentas = payload.cuentas or []
    if len(cuentas) < NUM_CUENTAS:
        cuentas = list(cuentas) + [{} for _ in range(NUM_CUENTAS - len(cuentas))]
    cuentas = cuentas[:NUM_CUENTAS]
    raw_asig = dict(payload.asignacion or {})
    asignacion = normalizar_asignacion({**ASIGNACION_DEFAULT, **raw_asig})
    nt_default = dict(ASIGNACION_DEFAULT.get("notificaciones_tab") or {})
    existing_asig = (existing_data or {}).get("asignacion") if isinstance(existing_data, dict) else {}
    existing_nt = (
        (existing_asig.get("notificaciones_tab") or {})
        if isinstance(existing_asig, dict)
        else {}
    )
    nt_in = raw_asig.get("notificaciones_tab")
    if isinstance(nt_in, dict):
        merged_nt = {
            k: normalizar_indice_cuenta(v)
            for k, v in {**existing_nt, **nt_in}.items()
        }
        for k, v in nt_default.items():
            if k not in merged_nt:
                merged_nt[k] = v
        asignacion["notificaciones_tab"] = merged_nt
    else:
        asignacion["notificaciones_tab"] = {
            k: normalizar_indice_cuenta(v)
            for k, v in {**nt_default, **existing_nt}.items()
        }
    for svc_key in ("cobros", "estado_cuenta", "recibos"):
        if svc_key in raw_asig:
            asignacion[svc_key] = normalizar_indice_cuenta(raw_asig[svc_key])

    cuentas_dict: List[dict] = []
    password_changed_indices: List[int] = []
    for i, c in enumerate(cuentas):
        d = c.model_dump(exclude_none=True) if hasattr(c, "model_dump") else dict(c)
        pwd_in_payload = d.get("smtp_password")
        password_changed = bool(
            pwd_in_payload and not _is_password_masked(str(pwd_in_payload))
        )
        base = cuenta_vacia()
        for k, v in d.items():
            if k in base and v is not None:
                if k in ("smtp_password", "imap_password") and _is_password_masked(v):
                    continue
                base[k] = v
        for field in SENSITIVE_FIELDS:
            if (not base.get(field) or _is_password_masked(base.get(field) or "")) and existing_data:
                existing_val = _get_existing_decrypted_password(existing_data, i, field)
                if existing_val:
                    base[field] = existing_val

        if password_changed:
            password_changed_indices.append(i)
        elif (
            (base.get("smtp_user") or "").strip()
            and (base.get("smtp_password") or "").strip()
            and existing_data
            and not _secret_field_stored(
                (existing_data.get("cuentas") or [{}])[i]
                if i < len(existing_data.get("cuentas") or [])
                else {},
                "smtp_password",
            )
        ):
            password_changed_indices.append(i)

        cuentas_dict.append(base)

    from app.core.email import test_smtp_connection

    smtp_verificaciones: List[dict] = []
    for i in password_changed_indices:
        c = cuentas_dict[i]
        if not (c.get("smtp_user") or "").strip():
            continue
        ok, err = test_smtp_connection(c)
        smtp_verificaciones.append({"cuenta": i + 1, "ok": ok, "mensaje": err or "Conexion SMTP OK"})
        if not ok:
            logger.warning(
                "PUT email/cuentas: verificacion SMTP fallida cuenta %d user=%s: %s",
                i + 1,
                (c.get("smtp_user") or "").strip(),
                err,
            )
            raise HTTPException(
                status_code=400,
                detail="Cuenta %d: no se pudo conectar por SMTP. %s"
                % (i + 1, err or "Revise host, puerto, usuario y contraseña."),
            )

    for i, c in enumerate(cuentas_dict):
        if (c.get("smtp_user") or "").strip():
            valido, errores = validar_config_email_para_guardar({**c, "modo_pruebas": payload.modo_pruebas if payload.modo_pruebas is not None else "false", "email_pruebas": payload.email_pruebas or ""})
            if not valido:
                raise HTTPException(
                    status_code=400,
                    detail="Cuenta %d: %s" % (i + 1, "; ".join(errores)),
                )

    cuentas_para_bd = []
    for idx, c in enumerate(cuentas_dict):
        stored = prepare_for_db_storage(dict(c))
        if existing_data and idx < len(existing_data.get("cuentas") or []):
            existing_cuenta = existing_data["cuentas"][idx]
            if isinstance(existing_cuenta, dict):
                for field in SENSITIVE_FIELDS:
                    enc_key = f"{field}_encriptado"
                    if enc_key not in stored or not stored.get(enc_key):
                        if existing_cuenta.get(enc_key):
                            stored[enc_key] = existing_cuenta.get(enc_key)
        plain_pwd = (c.get("smtp_password") or "").strip()
        if plain_pwd and not _is_password_masked(plain_pwd):
            if not _secret_field_stored(stored, "smtp_password"):
                raise HTTPException(
                    status_code=500,
                    detail=(
                        "Cuenta %d: la contraseña SMTP no se pudo guardar en la base de datos. "
                        "Revise los logs del servidor."
                    )
                    % (idx + 1),
                )
        cuentas_para_bd.append(stored)

    # Persistencia: fusionar con JSON existente para no perder claves que el cliente no envía
    # (email_activo maestro, informe_pagos, campañas, modo_pruebas_* por servicio, etc.).
    body = payload.model_dump(exclude_unset=True)
    if (
        existing_data
        and isinstance(existing_data, dict)
        and existing_data.get("version") == 2
        and isinstance(existing_data.get("cuentas"), list)
    ):
        payload_data: dict[str, Any] = dict(existing_data)
    else:
        payload_data = {}
    for k, v in body.items():
        if k in ("cuentas", "asignacion"):
            continue
        payload_data[k] = v
    payload_data["version"] = 2
    payload_data["cuentas"] = cuentas_para_bd[:NUM_CUENTAS]
    while len(payload_data["cuentas"]) < NUM_CUENTAS:
        payload_data["cuentas"].append(prepare_for_db_storage(cuenta_vacia()))
    payload_data["asignacion"] = asignacion
    if "recibos_bcc_emails" in body:
        payload_data["recibos_bcc_emails"] = _normalizar_recibos_bcc_emails(body.get("recibos_bcc_emails"))
    for dk, dv in _DEFAULTS_EMAIL_V2_GLOBALS.items():
        if dk not in payload_data or payload_data[dk] is None:
            payload_data[dk] = dv

    holder_update: dict[str, Any] = {
        "version": 2,
        "cuentas": cuentas_dict,
        "asignacion": asignacion,
    }
    for k, v in payload_data.items():
        if k not in ("version", "cuentas", "asignacion"):
            holder_update[k] = v
    update_from_api(holder_update)
    try:
        row = db.get(Configuracion, CLAVE_EMAIL_CONFIG)
        payload_str = json.dumps(payload_data, ensure_ascii=False)
        if row:
            row.valor = payload_str
        else:
            db.add(Configuracion(clave=CLAVE_EMAIL_CONFIG, valor=payload_str))
        db.commit()
        invalidate_email_config_cache()
        logger.info(
            "email_config persistido en BD (clave=%s, cuentas=%d, utf8=True, recibos_bcc=%s)",
            CLAVE_EMAIL_CONFIG,
            len(cuentas_para_bd),
            payload_data.get("recibos_bcc_emails") or [],
        )
    except Exception as e:
        logger.exception("Error guardando cuentas email: %s", e)
        db.rollback()
        raise HTTPException(status_code=500, detail="Error al guardar en BD")
    return {"message": "configuracion de 3 cuentas guardada", "version": 2, "asignacion": asignacion, "smtp_verificaciones": smtp_verificaciones}


class ProbarSmtpCuentaRequest(BaseModel):
    """Prueba login SMTP de una cuenta (1-3) sin enviar correo."""
    cuenta: int = 1
    smtp_host: Optional[str] = None
    smtp_port: Optional[str] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: Optional[str] = None


@router.post("/cuentas/probar-smtp")
def post_cuenta_probar_smtp(payload: ProbarSmtpCuentaRequest = Body(...), db: Session = Depends(get_db)):
    """Verifica conexion SMTP (login) para la cuenta indicada. Usa clave del body o la guardada en BD."""
    from app.core.email import test_smtp_connection

    idx = max(1, min(int(payload.cuenta or 1), NUM_CUENTAS)) - 1
    base = cuenta_vacia()
    if payload.smtp_host:
        base["smtp_host"] = payload.smtp_host
    if payload.smtp_port:
        base["smtp_port"] = payload.smtp_port
    if payload.smtp_user:
        base["smtp_user"] = payload.smtp_user
    if payload.smtp_use_tls:
        base["smtp_use_tls"] = payload.smtp_use_tls
    pwd = (payload.smtp_password or "").strip()
    if pwd and not _is_password_masked(pwd):
        base["smtp_password"] = pwd
    else:
        existing = _load_raw_from_db(db)
        if existing and existing.get("version") == 2:
            dec = _get_existing_decrypted_password(existing, idx, "smtp_password")
            if dec:
                base["smtp_password"] = dec
        if not base.get("smtp_password") and existing:
            migrated = migrar_config_v1_a_v2(existing) if "cuentas" not in existing else existing
            cu = (migrated.get("cuentas") or [{}])[idx]
            if isinstance(cu, dict):
                for k in ("smtp_host", "smtp_port", "smtp_user", "smtp_use_tls", "from_email"):
                    if not base.get(k) and cu.get(k):
                        base[k] = cu[k]
                if not base.get("smtp_user"):
                    base["smtp_user"] = cu.get("smtp_user") or ""
    ok, err = test_smtp_connection(base)
    return {
        "success": ok,
        "cuenta": idx + 1,
        "mensaje": "Conexion SMTP correcta (login aceptado)." if ok else (err or "Error SMTP"),
    }



def _parse_emails_pruebas(email_pruebas: str) -> List[str]:
    """Convierte el campo email_pruebas (coma, punto y coma o saltos de linea) en lista de emails validos."""
    if not (email_pruebas or "").strip():
        return []
    raw = (email_pruebas or "").replace(",", " ").replace(";", " ").replace("\n", " ")
    emails = [e.strip() for e in raw.split() if e.strip()]
    valid = []
    for e in emails:
        if "@" in e and "." in e.split("@")[-1] and len((e.split("@")[-1].split(".")[-1])) >= 2:
            valid.append(e)
    return valid


@router.post(
    "/enviar-prueba",
    summary="Envia un correo de prueba a todos los correos de pruebas registrados.",
)
def post_email_enviar_prueba(db: Session = Depends(get_db)):
    """
    Envia un email de prueba a cada direccion indicada en 'Correo de pruebas'
    (varios correos separados por coma, punto y coma o espacio).
    Usa la Cuenta 1 (Cobros) para el envio.
    """
    from app.core.email_config_holder import sync_from_db, get_smtp_config
    from app.core.email import send_email

    data = _load_raw_from_db(db)
    if not data:
        raise HTTPException(
            status_code=400,
            detail="No hay configuracion de email guardada. Guarde las cuentas primero.",
        )
    migrated = migrar_config_v1_a_v2(data) if data.get("version") != 2 or "cuentas" not in data else data
    email_pruebas_str = (migrated.get("email_pruebas") or "").strip()
    destinatarios = _parse_emails_pruebas(email_pruebas_str)
    if not destinatarios:
        raise HTTPException(
            status_code=400,
            detail="Configure al menos un correo de pruebas (puede ser varios separados por coma) y vuelva a intentar.",
        )

    sync_from_db()
    asignacion = normalizar_asignacion(migrated.get("asignacion"))
    tab_map = asignacion.get("notificaciones_tab") or {}
    tab_para_3 = next((t for t, c in tab_map.items() if c == 3), "dias_10_retraso")
    tab_para_1 = next((t for t, c in tab_map.items() if c == 1), "d_2_antes_vencimiento")
    pares_cuentas = [
        (1, "cobros", None),
        (1, "notificaciones", tab_para_1),
        (2, "estado_cuenta", None),
        (2, SERVICIO_FINIQUITO, None),
        (3, "notificaciones", tab_para_3),
    ]

    subject_base = "Prueba Cuenta {} - RapiCredit"
    body_base = "Prueba enviada con la Cuenta {}. Si recibes este correo, la cuenta esta operativa."
    enviados: List[dict] = []
    errores: List[dict] = []

    for num_cuenta, svc, tab in pares_cuentas:
        cfg = get_smtp_config(servicio=svc, tipo_tab=tab)
        if not (cfg.get("smtp_host") and (cfg.get("smtp_user") or "").strip()):
            continue
        pwd = (cfg.get("smtp_password") or "").strip()
        if not pwd or pwd == "***":
            errores.append({"cuenta": num_cuenta, "email": destinatarios[0] if destinatarios else "", "mensaje": "Falta contrasena en la cuenta"})
            continue
        for to in destinatarios:
            if svc == SERVICIO_FINIQUITO:
                subject = "Prueba Finiquito (codigo OTP) - RapiCredit"
                body_txt = (
                    "Prueba SMTP para el portal Finiquito (servicio finiquito). "
                    "Usa la misma cuenta que Estado de cuenta. Si recibe esto, el envio de codigos de acceso deberia funcionar."
                )
            else:
                subject = subject_base.format(num_cuenta)
                body_txt = body_base.format(num_cuenta)
            ok, err_msg = send_email(
                to_emails=[to],
                subject=subject,
                body_text=body_txt,
                respetar_destinos_manuales=True,
                servicio=svc,
                tipo_tab=tab,
            )
            if ok:
                enviados.append({"cuenta": num_cuenta, "email": to})
                logger.info("Email de prueba Cuenta %d enviado a %s", num_cuenta, to)
            else:
                errores.append({"cuenta": num_cuenta, "email": to, "mensaje": err_msg or "Error al enviar"})
                logger.warning("Email de prueba Cuenta %d fallo para %s: %s", num_cuenta, to, err_msg)

    total_ok = len(enviados)
    total_err = len(errores)
    logger.info(
        "enviar-prueba fin: aceptados_smtp=%d fallos=%d destinatarios_config=%s detalle_enviados=%s",
        total_ok,
        total_err,
        destinatarios,
        enviados,
    )
    return {
        "success": total_err == 0 and total_ok > 0,
        "enviados": enviados,
        "errores": errores,
        "mensaje": "Enviados: %d. Errores: %d (por cuenta/destino)." % (total_ok, total_err),
        "nota_smtp": (
            "Cada envio OK significa que el servidor SMTP acepto el mensaje (sin rechazo inmediato). "
            "La llegada a la bandeja la confirma el cliente de correo (revisar spam)."
        ),
    }
