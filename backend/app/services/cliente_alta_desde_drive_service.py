"""
Propuestas de alta de cliente desde snapshot `drive` (columnas D–G = nombres, cédula, teléfono, email).

Comparación de cédulas: misma normalización que POST /clientes/check-cedulas (`_normalizar_cedula_carga_masiva`).
Validación de formato de cédula: `validate_cedula` (mismas reglas que Validadores).
Nombre columna D: no seleccionable si el texto (tras strip, misma regla que POST /clientes) ya existe en `clientes.nombres`.
Correo columna G: no seleccionable si el mismo texto (tras strip) ya está en `clientes.email` o `clientes.email_secundario` (incluye placeholder si ya está ocupado).
Teléfono columna F: rechaza correos en F; normalización + `validate_phone` (04xx / 02xx, 11 dígitos).
"""
from __future__ import annotations

import json
import logging
from io import BytesIO
import re
import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import delete, desc, func, select
from sqlalchemy.orm import Session

from app.models.auditoria_cliente_alta_desde_drive import AuditoriaClienteAltaDesdeDrive
from app.models.cliente import Cliente
from app.models.conciliacion_sheet import ConciliacionSheetMeta
from app.models.drive import DriveRow
from app.models.clientes_drive_export_excel_auditoria import ClientesDriveExportExcelAuditoria
from app.models.drive_clientes_candidatos_cache import DriveClientesCandidatosCache
from app.schemas.cliente import ClienteCreate, ClienteDriveImportarFilaBody

logger = logging.getLogger(__name__)

_DEFAULT_FECHA_NAC = date(1990, 1, 1)
_DEFAULT_DIRECCION = "Pendiente (importación hoja CONCILIACIÓN)"
_DEFAULT_OCUPACION = "Por completar"
_PLACEHOLDER_EMAIL = "revisar@email.com"

# Subir cuando cambien reglas de candidatos (cédula, teléfono, etc.) para no servir JSON obsoleto
# desde `drive_clientes_candidatos_cache` aunque `synced_at` de la hoja no haya cambiado.
CANDIDATOS_DRIVE_CACHE_RULES_VERSION = 7


def _cell(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip()


def _validate_email_basic(email: str) -> bool:
    if not email:
        return False
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def _cedula_para_bd_desde_validacion(valor_formateado: str) -> str:
    """V-12345678 -> V12345678 (alineado a carga Excel / tabla)."""
    s = (valor_formateado or "").strip().upper().replace("-", "").replace(" ", "")
    return s


def _cedula_cmp_unificada(raw: str) -> str:
    """
    Clave estable para comparar cédulas (hoja vs BD vs duplicados en snapshot).
    Alinea con validate_cedula: si en la celda solo hay dígitos (6-11), se asume prefijo V.
    Así «24861353» en Drive y «V24861353» en clientes comparten la misma clave.
    """
    from app.api.v1.endpoints.clientes import _normalizar_cedula_carga_masiva
    from app.api.v1.endpoints.validadores import validate_cedula

    s = _cell(raw)
    if not s:
        return ""
    vced = validate_cedula(s)
    if vced.get("valido"):
        vf = str(vced.get("valor_formateado") or "").strip()
        bd = _cedula_para_bd_desde_validacion(vf)
        return _normalizar_cedula_carga_masiva(bd)
    return _normalizar_cedula_carga_masiva(s)


def _cedula_texto_columna_drive(raw: str, vced: Dict[str, Any]) -> str:
    """Texto mostrado para columna E: V + dígitos sin guión (coherente con almacenamiento en clientes)."""
    s = _cell(raw)
    if vced.get("valido"):
        vf = str(vced.get("valor_formateado") or s).strip()
        return _cedula_para_bd_desde_validacion(vf) or vf
    digits = re.sub(r"\D", "", s)
    if digits and re.match(r"^\d{6,11}$", digits):
        return f"V{digits}"
    return s


def _telefono_candidato_para_validate_phone(tel_norm: str) -> Optional[str]:
    """Pasa de 10 dígitos nacionales (412…) a 0412… para validate_phone, o devuelve None si no aplica."""
    if not tel_norm:
        return None
    if len(tel_norm) == 11 and tel_norm.startswith("0") and tel_norm[1] in ("2", "4"):
        return tel_norm
    if len(tel_norm) == 10 and tel_norm[0] in ("2", "4"):
        return "0" + tel_norm
    return None


def _telefono_col_f_validacion_estricta(raw_f: str) -> Tuple[bool, str, Optional[str]]:
    """
    Columna F obligatoria para marcar fila importable (salvo vacía → placeholder en alta).
    Rechaza correos en F y exige teléfono venezolano validate_phone (04xxxxxxxx / 02xxxxxxxx).
    Devuelve (válido, dígitos normalizados 10 para defaults/UI, mensaje_error).
    """
    raw = _cell(raw_f)
    if not raw:
        return True, "", None
    if "@" in raw:
        return False, "", "Columna F contiene «@»; parece un correo, no un teléfono."
    if _validate_email_basic(raw):
        return False, "", "Columna F tiene formato de correo; debe ser teléfono venezolano (04xx / 02xx)."
    tel_norm = _telefono_normalizado_drive_col_f(raw_f)
    if not tel_norm:
        return False, "", "Columna F no contiene un teléfono reconocible (solo dígitos 04… / 02…)."
    cand = _telefono_candidato_para_validate_phone(tel_norm)
    if not cand:
        return False, tel_norm, "Teléfono inválido: se esperan 10 dígitos nacionales tras normalizar (móvil 4… o fijo 2…)."
    from app.api.v1.endpoints.validadores import validate_phone

    vp = validate_phone(cand)
    if not vp.get("valido"):
        return False, tel_norm, str(vp.get("error") or "Teléfono inválido.")
    return True, tel_norm, None


def _telefono_normalizado_drive_col_f(raw: str) -> str:
    """
    Columna F: quita guiones, espacios y demás no dígitos; quita prefijo 58 si aplica;
    quita ceros a la izquierda mientras quede más de un bloque «extra» (p. ej. 00412… → 412…).
    Resultado típico: 10 dígitos nacionales (412… / 212…).
    Ej.: «0412 - 5443460» → 4125443460 ; 0412-9941999 → 4129941999
    """
    s = _cell(raw)
    if not s:
        return ""
    digits = re.sub(r"\D", "", s)
    if not digits:
        return ""
    if len(digits) >= 12 and digits.startswith("58"):
        digits = digits[2:]
    while len(digits) > 10 and digits.startswith("0"):
        digits = digits[1:]
    return digits


def _dt_trunc_seconds(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    return dt.replace(microsecond=0)


def listar_candidatos_desde_drive(db: Session) -> Dict[str, Any]:
    from app.api.v1.endpoints.clientes import _normalize_for_duplicate
    from app.api.v1.endpoints.validadores import validate_cedula

    rows = db.execute(select(DriveRow).order_by(DriveRow.sheet_row_number.asc())).scalars().all()
    cedulas_bd = db.execute(select(Cliente.cedula)).scalars().all()
    en_bd: set[str] = set()
    for c in cedulas_bd or []:
        n = _cedula_cmp_unificada(c or "")
        if n:
            en_bd.add(n)

    conteos: Dict[str, int] = {}
    tmp: List[Tuple[DriveRow, str]] = []
    for r in rows or []:
        raw_e = _cell(getattr(r, "col_e", None))
        cmp_e = _cedula_cmp_unificada(raw_e)
        if not cmp_e:
            continue
        conteos[cmp_e] = conteos.get(cmp_e, 0) + 1
        tmp.append((r, cmp_e))

    meta = db.get(ConciliacionSheetMeta, 1)
    synced_at = meta.synced_at.isoformat() if meta and meta.synced_at else None

    pending: List[Dict[str, Any]] = []
    for r, cmp_e in tmp:
        if cmp_e in en_bd:
            continue
        raw_d = _cell(getattr(r, "col_d", None))
        raw_f = _cell(getattr(r, "col_f", None))
        raw_g = _cell(getattr(r, "col_g", None))
        raw_e = _cell(getattr(r, "col_e", None))
        dup_sheet = conteos.get(cmp_e, 0) > 1
        vced = validate_cedula(raw_e)
        cedula_valida = bool(vced.get("valido"))
        cedula_error = None if cedula_valida else (vced.get("error") or "Cédula inválida")
        valor_fmt = str(vced.get("valor_formateado") or raw_e).strip()
        cedula_sugerida_bd = _cedula_para_bd_desde_validacion(valor_fmt) if cedula_valida else ""

        email_propuesto = raw_g if _validate_email_basic(raw_g) else _PLACEHOLDER_EMAIL
        nombres_propuesto = raw_d if raw_d else "Revisar Nombres"
        # Si solo hay dígitos (6–11) sin letra, validate_cedula ya asume V; mostramos V-… normalizado.
        col_e_mostrar = _cedula_texto_columna_drive(raw_e, vced)
        tel_norm = _telefono_normalizado_drive_col_f(raw_f)
        tel_ok, tel_val, tel_err = _telefono_col_f_validacion_estricta(raw_f)
        tel_display = tel_val if tel_ok else (tel_norm or raw_f or None)
        nombres_norm = _normalize_for_duplicate(nombres_propuesto)
        email_key = _normalize_for_duplicate(str(email_propuesto))

        pending.append(
            {
                "sheet_row_number": r.sheet_row_number,
                "col_d_nombres": raw_d or None,
                "col_e_cedula": col_e_mostrar or None,
                "col_f_telefono": tel_display,
                "col_g_email": raw_g or None,
                "cedula_cmp": cmp_e,
                "cedula_valida": cedula_valida,
                "cedula_error": cedula_error,
                "cedula_para_crear": cedula_sugerida_bd if cedula_valida else None,
                "duplicada_en_hoja": dup_sheet,
                "telefono_valida": tel_ok,
                "telefono_error": tel_err,
                "_nombres_norm": nombres_norm,
                "_email_key": email_key,
                "defaults": {
                    "nombres": nombres_propuesto,
                    "telefono": tel_val if tel_ok else (tel_norm or ""),
                    "email": email_propuesto,
                    "direccion": _DEFAULT_DIRECCION,
                    "fecha_nacimiento": _DEFAULT_FECHA_NAC.isoformat(),
                    "ocupacion": _DEFAULT_OCUPACION,
                    "estado": "ACTIVO",
                },
            }
        )

    noms_buscar = {p["_nombres_norm"] for p in pending if p.get("_nombres_norm")}
    nom_hit: Dict[str, int] = {}
    if noms_buscar:
        rows_nm = db.execute(
            select(Cliente.id, Cliente.nombres).where(Cliente.nombres.in_(list(noms_buscar)))
        ).all()
        for rid, n in rows_nm or []:
            if n is None:
                continue
            ns = str(n)
            if ns and ns not in nom_hit:
                nom_hit[ns] = int(rid)

    em_keys_buscar = {str(p.get("_email_key") or "").strip() for p in pending if (p.get("_email_key") or "").strip()}
    email_hit_lista: Dict[str, int] = {}
    if em_keys_buscar:
        em_list = list(em_keys_buscar)
        rows_p = db.execute(select(Cliente.id, Cliente.email).where(Cliente.email.in_(em_list))).all()
        for rid, mail in rows_p or []:
            if mail is None:
                continue
            m = str(mail).strip()
            if m and m not in email_hit_lista:
                email_hit_lista[m] = int(rid)
        rows_s = db.execute(
            select(Cliente.id, Cliente.email_secundario).where(
                Cliente.email_secundario.isnot(None),
                Cliente.email_secundario.in_(em_list),
            )
        ).all()
        for rid, mail2 in rows_s or []:
            if mail2 is None:
                continue
            m = str(mail2).strip()
            if m and m not in email_hit_lista:
                email_hit_lista[m] = int(rid)

    candidatos: List[Dict[str, Any]] = []
    for p in pending:
        nn = str(p.pop("_nombres_norm", "") or "")
        ex_id = nom_hit.get(nn) if nn else None
        nombres_valido = not (nn and ex_id is not None)
        nombres_error = (
            None
            if nombres_valido
            else (
                f"Ya existe un cliente con el mismo nombre completo en tabla clientes (ID {ex_id}). "
                "Corrija la columna D en Drive o el registro existente antes de importar."
            )
        )
        ek = str(p.pop("_email_key", "") or "").strip()
        ex_mail = email_hit_lista.get(ek) if ek else None
        email_valido = not (ek and ex_mail is not None)
        email_error = (
            None
            if email_valido
            else (
                f"Ya existe un cliente con el mismo correo en tabla clientes (ID {ex_mail}). "
                "Corrija la columna G en Drive o use otro correo."
            )
        )
        seleccionable = (
            bool(p["cedula_valida"])
            and not p["duplicada_en_hoja"]
            and bool(p["telefono_valida"])
            and nombres_valido
            and email_valido
        )
        candidatos.append(
            {
                **p,
                "nombres_valido": nombres_valido,
                "nombres_error": nombres_error,
                "email_valido": email_valido,
                "email_error": email_error,
                "seleccionable": seleccionable,
            }
        )

    return {
        "drive_synced_at": synced_at,
        "total_candidatos": len(candidatos),
        "candidatos": candidatos,
        "candidatos_reglas_version": CANDIDATOS_DRIVE_CACHE_RULES_VERSION,
    }


def refrescar_cache_candidatos_drive(db: Session) -> Dict[str, Any]:
    """
    Recalcula candidatos desde tablas drive/clientes y persiste en drive_clientes_candidatos_cache (id=1).
    Usado por el job lun-sab 02:30 (scheduler) y tras importaciones para alinear la lista sin depender del usuario.
    """
    data = listar_candidatos_desde_drive(db)
    meta = db.get(ConciliacionSheetMeta, 1)
    drive_at = meta.synced_at if meta else None
    row = db.get(DriveClientesCandidatosCache, 1)
    if row is None:
        row = DriveClientesCandidatosCache(id=1)
        db.add(row)
    row.payload = data
    row.drive_synced_at = drive_at
    row.computed_at = datetime.now(timezone.utc)
    db.commit()
    logger.info(
        "[drive_clientes_candidatos_cache] refrescado total=%s drive_synced_at=%s",
        data.get("total_candidatos"),
        drive_at.isoformat() if drive_at else None,
    )
    return {
        "ok": True,
        "total_candidatos": data.get("total_candidatos"),
        "drive_synced_at": data.get("drive_synced_at"),
        "computed_at": row.computed_at.isoformat() if row.computed_at else None,
    }


def obtener_candidatos_drive_para_api(db: Session, *, forzar_calculo: bool = False) -> Dict[str, Any]:
    """
    Sirve GET /clientes/drive-import/candidatos: usa caché si está alineada con conciliacion_sheet_meta.synced_at;
    si no, recalcula, actualiza caché y devuelve (sin requerir acción manual del usuario).
    """
    meta = db.get(ConciliacionSheetMeta, 1)
    drive_at = meta.synced_at if meta else None
    cache = db.get(DriveClientesCandidatosCache, 1)

    cached_ver = (
        int(cache.payload.get("candidatos_reglas_version") or 0)
        if cache is not None and isinstance(cache.payload, dict)
        else -1
    )
    if (
        not forzar_calculo
        and cache is not None
        and isinstance(cache.payload, dict)
        and cached_ver == CANDIDATOS_DRIVE_CACHE_RULES_VERSION
        and _dt_trunc_seconds(cache.drive_synced_at) == _dt_trunc_seconds(drive_at)
        and drive_at is not None
    ):
        out = dict(cache.payload)
        out["from_cache"] = True
        out["cache_computed_at"] = cache.computed_at.isoformat() if cache.computed_at else None
        return out

    data = listar_candidatos_desde_drive(db)
    row = cache
    if row is None:
        row = DriveClientesCandidatosCache(id=1)
        db.add(row)
    row.payload = data
    row.drive_synced_at = drive_at
    row.computed_at = datetime.now(timezone.utc)
    db.commit()
    out = dict(data)
    out["from_cache"] = False
    out["cache_computed_at"] = row.computed_at.isoformat() if row.computed_at else None
    return out


def importar_seleccion_desde_drive(
    db: Session,
    *,
    usuario_email: str,
    comentario: Optional[str],
    sheet_rows: List[int],
) -> Dict[str, Any]:
    """
    Importa varias filas en modo **parcial**: cada fila que cumple preflight e inserta en BD se persiste
    con su auditoría; las que fallan (preflight o error al insertar) no bloquean al resto.
    Devuelve `resultados` en el orden de `sheet_row_numbers` con `ok` / `error` por fila.
    """
    if not sheet_rows:
        raise HTTPException(status_code=400, detail="Debe enviar al menos una fila (sheet_row_number).")

    from app.api.v1.endpoints.clientes import (
        _cedula_clave_comparacion_clientes,
        _expr_cedula_normalizada_sql,
        _normalize_for_duplicate,
        create_cliente_from_payload,
    )

    snap = listar_candidatos_desde_drive(db)
    by_row = {int(c["sheet_row_number"]): c for c in (snap.get("candidatos") or [])}

    batch_id = str(uuid.uuid4())
    comentario_final = (comentario or "").strip() or None

    early_errors: List[Dict[str, Any]] = []
    seen_cmp: set[str] = set()
    ced_sql_tabla = _expr_cedula_normalizada_sql(Cliente.cedula)

    # Fase 1: validación + ClienteCreate; sin consultas por fila a BD (duplicados se resuelven en fase 2).
    staged: List[Tuple[int, Dict[str, Any], ClienteCreate, str, str, str, str]] = []
    for sheet_row in sheet_rows:
        sr = int(sheet_row)
        info = by_row.get(sr)
        if info is None:
            early_errors.append(
                {
                    "sheet_row_number": sr,
                    "error": "Fila no disponible para importación (no está en candidatos: ya existe en clientes o sin cédula en E).",
                }
            )
            continue
        if not info.get("seleccionable"):
            if not info.get("cedula_valida"):
                msg = "No se permite guardar: la fila no cumple el 100% de validadores (cédula inválida en el snapshot)."
            elif info.get("duplicada_en_hoja"):
                msg = "No se permite guardar: la fila no cumple el 100% de validadores (cédula duplicada en el snapshot de Drive)."
            elif not info.get("nombres_valido", True):
                msg = str(
                    info.get("nombres_error")
                    or "No se permite guardar: el nombre completo (columna D) ya existe en tabla clientes."
                )
            elif not info.get("email_valido", True):
                msg = str(
                    info.get("email_error")
                    or "No se permite guardar: el correo (columna G) ya existe en tabla clientes."
                )
            elif not info.get("telefono_valida", True):
                msg = str(info.get("telefono_error") or "No se permite guardar: teléfono columna F inválido.")
            else:
                msg = "No se permite guardar: la fila no cumple el 100% de validadores de la hoja."
            early_errors.append({"sheet_row_number": sr, "error": msg})
            continue

        cmp_k = str(info.get("cedula_cmp") or "")
        if cmp_k in seen_cmp:
            early_errors.append({"sheet_row_number": sr, "error": "Cédula duplicada en la selección enviada."})
            continue
        seen_cmp.add(cmp_k)

        defs = info.get("defaults") or {}

        ced = str(info.get("cedula_para_crear") or "").strip()
        ck = _cedula_clave_comparacion_clientes(ced)
        notas = (
            f"Alta aprobada desde Notificaciones > Clientes (Drive CONCILIACIÓN). "
            f"Fila hoja {info.get('sheet_row_number')}. "
            f"Email columna G: {info.get('col_g_email')!r}."
        )
        try:
            payload = ClienteCreate(
                cedula=ced,
                nombres=str(defs.get("nombres") or "Revisar Nombres"),
                telefono=str(defs.get("telefono") or ""),
                email=str(defs.get("email") or _PLACEHOLDER_EMAIL),
                email_secundario=None,
                direccion=_DEFAULT_DIRECCION,
                fecha_nacimiento=_DEFAULT_FECHA_NAC,
                ocupacion=_DEFAULT_OCUPACION,
                estado="ACTIVO",
                usuario_registro=usuario_email,
                notas=notas,
            )
        except ValidationError as ve:
            early_errors.append({"sheet_row_number": sr, "error": str(ve)})
            continue

        nombres_post = _normalize_for_duplicate(payload.nombres or "")
        em_post = _normalize_for_duplicate(payload.email or "")
        em_cmp = em_post.strip().lower()
        staged.append((sr, info, payload, ck, nombres_post, em_cmp, em_post))

    ced_keys = {t[3] for t in staged if t[3] and t[3] != "Z999999999"}
    ced_hit: Dict[str, int] = {}
    if ced_keys:
        rows = db.execute(
            select(Cliente.id, ced_sql_tabla).where(ced_sql_tabla.in_(list(ced_keys)))
        ).all()
        for rid, k in rows or []:
            if k and k not in ced_hit:
                ced_hit[str(k)] = int(rid)

    nom_set = {t[4] for t in staged if t[4]}
    nom_hit: Dict[str, int] = {}
    if nom_set:
        rows = db.execute(select(Cliente.id, Cliente.nombres).where(Cliente.nombres.in_(list(nom_set)))).all()
        for rid, n in rows or []:
            if n and n not in nom_hit:
                nom_hit[str(n)] = int(rid)

    # Misma condición que create_cliente_from_payload: cualquier email no vacío (incl. placeholder) vs BD.
    em_set = {(t[6] or "").strip() for t in staged if (t[6] or "").strip()}
    email_hit: Dict[str, int] = {}
    if em_set:
        em_list = list(em_set)
        rows_p = db.execute(select(Cliente.id, Cliente.email).where(Cliente.email.in_(em_list))).all()
        for rid, mail in rows_p or []:
            if mail is None:
                continue
            m = (str(mail)).strip()
            if m and m not in email_hit:
                email_hit[m] = int(rid)
        rows_s = db.execute(
            select(Cliente.id, Cliente.email_secundario).where(
                Cliente.email_secundario.isnot(None),
                Cliente.email_secundario.in_(em_list),
            )
        ).all()
        for rid, mail2 in rows_s or []:
            if mail2 is None:
                continue
            m = (str(mail2)).strip()
            if m and m not in email_hit:
                email_hit[m] = int(rid)

    late_errors: List[Dict[str, Any]] = []
    seen_nombres: set[str] = set()
    seen_email_lower: set[str] = set()
    carga: List[Tuple[int, Dict[str, Any], ClienteCreate]] = []
    for sr, info, payload, ck, nombres_post, em_cmp, em_post in staged:
        if ck and ck != "Z999999999" and ck in ced_hit:
            late_errors.append(
                {
                    "sheet_row_number": sr,
                    "error": (
                        f"La cédula ya existe en tabla clientes (ID {ced_hit[ck]}). "
                        "No se permite guardar duplicados."
                    ),
                }
            )
            continue
        if nombres_post and nombres_post in seen_nombres:
            late_errors.append(
                {"sheet_row_number": sr, "error": "Nombre completo duplicado dentro del mismo lote enviado."}
            )
            continue
        if nombres_post and nombres_post in nom_hit:
            late_errors.append(
                {
                    "sheet_row_number": sr,
                    "error": (
                        f"Ya existe un cliente con el mismo nombre completo en tabla clientes (ID {nom_hit[nombres_post]}). "
                        "Corrija la columna D en Drive o el registro existente antes de importar."
                    ),
                }
            )
            continue
        em_key = (em_post or "").strip()
        em_low = em_key.lower()
        if em_key and em_low in seen_email_lower:
            late_errors.append(
                {"sheet_row_number": sr, "error": "Correo (columna G) duplicado dentro del mismo lote enviado."}
            )
            continue
        if em_key:
            ex_id = email_hit.get(em_key)
            if ex_id is not None:
                late_errors.append(
                    {
                        "sheet_row_number": sr,
                        "error": (
                            f"Ya existe un cliente con el mismo correo en tabla clientes (ID {ex_id}). "
                            "Corrija la columna G en Drive."
                        ),
                    }
                )
                continue

        if nombres_post:
            seen_nombres.add(nombres_post)
        if em_key:
            seen_email_lower.add(em_low)
        carga.append((sr, info, payload))

    pre_errors = early_errors + late_errors
    preflight_err: Dict[int, str] = {int(e["sheet_row_number"]): str(e["error"]) for e in pre_errors}

    insertados_por_fila: List[Dict[str, Any]] = []
    insertados_ok = 0
    for sr, _info, payload in carga:
        try:
            row = create_cliente_from_payload(db, payload, commit=False)
            db.add(
                AuditoriaClienteAltaDesdeDrive(
                    batch_id=batch_id,
                    sheet_row_number=sr,
                    cedula=str(row.cedula),
                    nombres=str(row.nombres),
                    telefono=str(row.telefono),
                    email=str(row.email),
                    comentario=comentario_final,
                    usuario_email=usuario_email,
                    estado="APROBADO_INSERTADO",
                    detalle_error=None,
                )
            )
            db.commit()
            insertados_ok += 1
            insertados_por_fila.append({"sheet_row_number": sr, "ok": True, "cliente_id": row.id})
        except HTTPException as he:
            try:
                db.rollback()
            except Exception:
                pass
            detail = he.detail if isinstance(he.detail, str) else str(he.detail)
            insertados_por_fila.append({"sheet_row_number": sr, "ok": False, "error": detail})
        except Exception as ex:  # pragma: no cover
            logger.exception("importar_seleccion_desde_drive fila=%s: %s", sr, ex)
            try:
                db.rollback()
            except Exception:
                pass
            insertados_por_fila.append({"sheet_row_number": sr, "ok": False, "error": str(ex)})

    insert_map = {int(r["sheet_row_number"]): r for r in insertados_por_fila}
    resultados: List[Dict[str, Any]] = []
    for sheet_row in sheet_rows:
        isr = int(sheet_row)
        if isr in preflight_err:
            resultados.append({"sheet_row_number": isr, "ok": False, "error": preflight_err[isr]})
        elif isr in insert_map:
            resultados.append(insert_map[isr])
        else:
            resultados.append(
                {
                    "sheet_row_number": isr,
                    "ok": False,
                    "error": "Fila no procesada (no estaba en candidatos válidos para este envío).",
                }
            )

    errores = sum(1 for r in resultados if not r.get("ok"))
    if insertados_ok > 0:
        try:
            refrescar_cache_candidatos_drive(db)
        except Exception:
            logger.warning(
                "[drive_clientes_candidatos_cache] no se pudo refrescar tras importar lote batch_id=%s",
                batch_id,
                exc_info=True,
            )

    return {
        "batch_id": batch_id,
        "insertados_ok": insertados_ok,
        "errores": errores,
        "resultados": resultados,
        "lote_abortado": insertados_ok == 0 and errores > 0,
    }


def importar_fila_desde_drive(
    db: Session,
    *,
    usuario_email: str,
    body: ClienteDriveImportarFilaBody,
) -> Dict[str, Any]:
    """
    Inserta un cliente con ClienteCreate + auditoría.
    La cédula enviada debe coincidir con `cedula_cmp` de la fila Drive (no se puede cambiar a otra identidad).
    No exige que la fila sea `seleccionable`: el formulario puede corregir nombre, correo y teléfono.
    """
    from app.api.v1.endpoints.clientes import (
        _cedula_clave_comparacion_clientes,
        _expr_cedula_normalizada_sql,
        create_cliente_from_payload,
    )

    snap = listar_candidatos_desde_drive(db)
    by_row = {int(c["sheet_row_number"]): c for c in (snap.get("candidatos") or [])}
    info = by_row.get(int(body.sheet_row_number))
    if info is None:
        raise HTTPException(
            status_code=404,
            detail="Fila no disponible para importación (no está en candidatos o la lista cambió).",
        )
    # Desde edición se pueden corregir nombre, correo y teléfono: no exigir `seleccionable` del snapshot.
    # Sí bloquear cédula repetida en la misma hoja (no desambiguable por este flujo).
    if info.get("duplicada_en_hoja"):
        raise HTTPException(
            status_code=400,
            detail=(
                "La cédula está repetida en más de una fila del snapshot Drive (columna E). "
                "Corrija la hoja antes de importar esta fila."
            ),
        )

    tel_body_ok, _, tel_body_err = _telefono_col_f_validacion_estricta(body.telefono or "")
    if not tel_body_ok:
        raise HTTPException(
            status_code=400,
            detail=tel_body_err or "Teléfono inválido (columna F / formulario).",
        )

    cmp_expected = str(info.get("cedula_cmp") or "")
    cmp_sent = _cedula_cmp_unificada(body.cedula or "")
    if cmp_sent != cmp_expected:
        raise HTTPException(
            status_code=400,
            detail="La cédula enviada no coincide con la columna E de esta fila (tras normalización).",
        )

    cedula_crear = str(info.get("cedula_para_crear") or body.cedula or "").strip()
    ced_key = _cedula_clave_comparacion_clientes(cedula_crear)
    if ced_key and ced_key != "Z999999999":
        dup = db.execute(
            select(Cliente.id).where(_expr_cedula_normalizada_sql(Cliente.cedula) == ced_key)
        ).first()
        if dup:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Ya existe un cliente con la misma cédula en tabla clientes (ID {dup[0]}). "
                    "No se permite guardar."
                ),
            )
    notas_final = (body.notas or "").strip()
    if not notas_final:
        notas_final = (
            f"Alta desde Notificaciones > Clientes (Drive CONCILIACIÓN). "
            f"Fila hoja {body.sheet_row_number}. "
            f"Email columna G: {info.get('col_g_email')!r}."
        )

    batch_id = str(uuid.uuid4())
    comentario_final = (body.comentario or "").strip() or None

    try:
        payload = ClienteCreate(
            cedula=cedula_crear,
            nombres=body.nombres,
            telefono=body.telefono,
            email=body.email,
            email_secundario=body.email_secundario,
            direccion=body.direccion,
            fecha_nacimiento=body.fecha_nacimiento,
            ocupacion=body.ocupacion,
            estado=(body.estado or "ACTIVO").strip().upper(),
            usuario_registro=usuario_email,
            notas=notas_final,
        )
    except ValidationError as ve:
        raise HTTPException(status_code=422, detail=ve.errors()) from ve

    try:
        row = create_cliente_from_payload(db, payload)
        db.add(
            AuditoriaClienteAltaDesdeDrive(
                batch_id=batch_id,
                sheet_row_number=int(body.sheet_row_number),
                cedula=str(row.cedula),
                nombres=str(row.nombres),
                telefono=str(row.telefono),
                email=str(row.email),
                comentario=comentario_final,
                usuario_email=usuario_email,
                estado="APROBADO_INSERTADO",
                detalle_error=None,
            )
        )
        db.commit()
    except HTTPException as he:
        err_detail = he.detail
        if not isinstance(err_detail, str):
            err_detail = str(err_detail)
        try:
            db.rollback()
        except Exception:
            pass
        db.add(
            AuditoriaClienteAltaDesdeDrive(
                batch_id=batch_id,
                sheet_row_number=int(body.sheet_row_number),
                cedula=cedula_crear,
                nombres=body.nombres,
                telefono=body.telefono,
                email=body.email,
                comentario=comentario_final,
                usuario_email=usuario_email,
                estado="APROBADO_ERROR",
                detalle_error=err_detail[:4000],
            )
        )
        db.commit()
        raise
    except Exception as ex:  # pragma: no cover
        logger.exception("importar_fila_desde_drive fila=%s: %s", body.sheet_row_number, ex)
        try:
            db.rollback()
        except Exception:
            pass
        db.add(
            AuditoriaClienteAltaDesdeDrive(
                batch_id=batch_id,
                sheet_row_number=int(body.sheet_row_number),
                cedula=cedula_crear,
                nombres=body.nombres,
                telefono=body.telefono,
                email=body.email,
                comentario=comentario_final,
                usuario_email=usuario_email,
                estado="APROBADO_ERROR",
                detalle_error=str(ex)[:4000],
            )
        )
        db.commit()
        raise HTTPException(status_code=500, detail=str(ex)) from ex

    try:
        refrescar_cache_candidatos_drive(db)
    except Exception:
        logger.warning(
            "[drive_clientes_candidatos_cache] no se pudo refrescar tras importar-fila batch_id=%s",
            batch_id,
            exc_info=True,
        )

    return {
        "ok": True,
        "batch_id": batch_id,
        "cliente_id": row.id,
        "cedula": row.cedula,
    }


def exportar_candidatos_drive_excel_y_borrar_filas(
    db: Session,
    *,
    usuario_email: str,
    modo: str,
) -> Tuple[bytes, str]:
    """
    Genera Excel con candidatos Drive y elimina de `drive` las filas exportadas (sheet_row_number).
    modo=solo_no_seleccionable: filas que no cumplen validadores de pantalla (rojo/ámbar).
    modo=todos_candidatos: todos los candidatos listados (incluye listos para revisión).
    Tras borrar, recalcula caché de candidatos. Las filas vuelven a aparecer en el próximo sync Google → BD.
    """
    if modo not in ("solo_no_seleccionable", "todos_candidatos"):
        raise HTTPException(status_code=400, detail="modo debe ser solo_no_seleccionable o todos_candidatos.")

    data = listar_candidatos_desde_drive(db)
    candidatos: List[Dict[str, Any]] = list(data.get("candidatos") or [])
    if modo == "solo_no_seleccionable":
        to_export = [c for c in candidatos if not c.get("seleccionable")]
    else:
        to_export = list(candidatos)

    if not to_export:
        raise HTTPException(
            status_code=400,
            detail="No hay filas para exportar con ese criterio.",
        )

    try:
        from openpyxl import Workbook
    except ImportError as e:  # pragma: no cover
        raise HTTPException(
            status_code=503,
            detail="Dependencia openpyxl no disponible en el servidor.",
        ) from e

    wb = Workbook()
    ws = wb.active
    ws.title = "candidatos_drive"
    headers = [
        "sheet_row_number",
        "col_d_nombres",
        "col_e_cedula",
        "col_f_telefono",
        "col_g_email",
        "cedula_valida",
        "cedula_error",
        "duplicada_en_hoja",
        "seleccionable",
        "motivo_estado",
    ]
    ws.append(headers)
    for c in to_export:
        defs = c.get("defaults") or {}
        if not c.get("cedula_valida"):
            motivo = "cedula_invalida"
        elif c.get("duplicada_en_hoja"):
            motivo = "duplicada_en_hoja"
        elif not c.get("nombres_valido", True):
            motivo = "nombre_duplicado_en_clientes"
        elif not c.get("email_valido", True):
            motivo = "email_duplicado_en_clientes"
        elif not c.get("telefono_valida", True):
            motivo = "telefono_invalido"
        elif c.get("seleccionable"):
            motivo = "listo_revision"
        else:
            motivo = "otro"
        ws.append(
            [
                c.get("sheet_row_number"),
                c.get("col_d_nombres") or "",
                c.get("col_e_cedula") or "",
                defs.get("telefono") or "",
                defs.get("email") or "",
                bool(c.get("cedula_valida")),
                c.get("cedula_error") or "",
                bool(c.get("duplicada_en_hoja")),
                bool(c.get("seleccionable")),
                motivo,
            ]
        )

    buf = BytesIO()
    wb.save(buf)
    raw_bytes = buf.getvalue()

    nums = sorted({int(c["sheet_row_number"]) for c in to_export})
    db.execute(delete(DriveRow).where(DriveRow.sheet_row_number.in_(nums)))
    db.add(
        ClientesDriveExportExcelAuditoria(
            usuario_email=usuario_email,
            modo=modo,
            filas_count=len(nums),
            sheet_rows_json=json.dumps(nums),
        )
    )
    db.commit()

    try:
        refrescar_cache_candidatos_drive(db)
    except Exception:
        logger.warning(
            "[drive_clientes_candidatos_cache] no se pudo refrescar tras exportar-excel modo=%s",
            modo,
            exc_info=True,
        )

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    fname = f"drive_candidatos_{modo}_{stamp}.xlsx"
    return raw_bytes, fname


def listar_auditoria(db: Session, *, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
    page = max(page, 1)
    per_page = min(max(per_page, 1), 200)
    total = int(db.scalar(select(func.count()).select_from(AuditoriaClienteAltaDesdeDrive)) or 0)
    rows = (
        db.execute(
            select(AuditoriaClienteAltaDesdeDrive)
            .order_by(desc(AuditoriaClienteAltaDesdeDrive.id))
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        .scalars()
        .all()
    )
    items = [
        {
            "id": r.id,
            "batch_id": r.batch_id,
            "sheet_row_number": r.sheet_row_number,
            "cedula": r.cedula,
            "nombres": r.nombres,
            "telefono": r.telefono,
            "email": r.email,
            "comentario": r.comentario,
            "usuario_email": r.usuario_email,
            "estado": r.estado,
            "detalle_error": r.detalle_error,
            "creado_en": r.creado_en.isoformat() if r.creado_en else None,
        }
        for r in rows
    ]
    return {"total": total, "page": page, "per_page": per_page, "items": items}
