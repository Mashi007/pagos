"""
Propuestas de alta de cliente desde snapshot `drive` (columnas D–G = nombres, cédula, teléfono, email).

Comparación de cédulas: misma normalización que POST /clientes/check-cedulas (`_normalizar_cedula_carga_masiva`).
Validación de formato de cédula: `validate_cedula` (mismas reglas que Validadores).
Teléfono columna F: dígitos solos, sin guión; quita 58 inicial si viene internacional y un 0 inicial en números de 11 dígitos.
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
    """Texto mostrado para columna E: formato V-… cuando aplica (igual que validadores con V implícita)."""
    s = _cell(raw)
    if vced.get("valido"):
        return str(vced.get("valor_formateado") or s).strip()
    digits = re.sub(r"\D", "", s)
    if digits and re.match(r"^\d{6,11}$", digits):
        return f"V-{digits}"
    return s


def _telefono_normalizado_drive_col_f(raw: str) -> str:
    """
    Columna F: quita guiones/espacios y deja solo dígitos; quita prefijo 58 si aplica;
    si quedan 11 dígitos y el primero es 0 (ej. 0412…), quita ese 0 inicial → 10 dígitos nacionales.
    Ej.: 0412-9941999 → 4129941999
    """
    s = _cell(raw)
    if not s:
        return ""
    digits = re.sub(r"\D", "", s)
    if not digits:
        return ""
    if len(digits) >= 12 and digits.startswith("58"):
        digits = digits[2:]
    if len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    return digits


def _dt_trunc_seconds(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    return dt.replace(microsecond=0)


def listar_candidatos_desde_drive(db: Session) -> Dict[str, Any]:
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

    candidatos: List[Dict[str, Any]] = []
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
        col_e_mostrar = _cedula_texto_columna_drive(raw_e, vced)
        tel_norm = _telefono_normalizado_drive_col_f(raw_f)

        candidatos.append(
            {
                "sheet_row_number": r.sheet_row_number,
                "col_d_nombres": raw_d or None,
                "col_e_cedula": col_e_mostrar or None,
                "col_f_telefono": tel_norm or None,
                "col_g_email": raw_g or None,
                "cedula_cmp": cmp_e,
                "cedula_valida": cedula_valida,
                "cedula_error": cedula_error,
                "cedula_para_crear": cedula_sugerida_bd if cedula_valida else None,
                "duplicada_en_hoja": dup_sheet,
                "seleccionable": cedula_valida and not dup_sheet,
                "defaults": {
                    "nombres": nombres_propuesto,
                    "telefono": tel_norm,
                    "email": email_propuesto,
                    "direccion": _DEFAULT_DIRECCION,
                    "fecha_nacimiento": _DEFAULT_FECHA_NAC.isoformat(),
                    "ocupacion": _DEFAULT_OCUPACION,
                    "estado": "ACTIVO",
                },
            }
        )

    return {
        "drive_synced_at": synced_at,
        "total_candidatos": len(candidatos),
        "candidatos": candidatos,
    }


def refrescar_cache_candidatos_drive(db: Session) -> Dict[str, Any]:
    """
    Recalcula candidatos desde tablas drive/clientes y persiste en drive_clientes_candidatos_cache (id=1).
    Usado por el job dom/mié 03:00 y tras importaciones para alinear la lista sin depender del usuario.
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

    if (
        not forzar_calculo
        and cache is not None
        and isinstance(cache.payload, dict)
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
    if not sheet_rows:
        raise HTTPException(status_code=400, detail="Debe enviar al menos una fila (sheet_row_number).")

    from app.api.v1.endpoints.clientes import create_cliente_from_payload

    snap = listar_candidatos_desde_drive(db)
    by_row = {int(c["sheet_row_number"]): c for c in (snap.get("candidatos") or [])}

    batch_id = str(uuid.uuid4())
    resultados: List[Dict[str, Any]] = []
    ok = 0
    err = 0

    seen_cmp: set[str] = set()

    for sheet_row in sheet_rows:
        info = by_row.get(int(sheet_row))
        if info is None:
            err += 1
            msg = "Fila no disponible para importación (no está en candidatos: ya existe en clientes o sin cédula en E)."
            db.add(
                AuditoriaClienteAltaDesdeDrive(
                    batch_id=batch_id,
                    sheet_row_number=int(sheet_row),
                    cedula="",
                    nombres=None,
                    telefono=None,
                    email=None,
                    comentario=comentario,
                    usuario_email=usuario_email,
                    estado="ERROR",
                    detalle_error=msg,
                )
            )
            db.commit()
            resultados.append({"sheet_row_number": sheet_row, "ok": False, "error": msg})
            continue

        if not info.get("seleccionable"):
            err += 1
            msg = (
                "No se permite guardar: la fila no cumple el 100% de validadores (cédula inválida en el snapshot)."
                if not info.get("cedula_valida")
                else "No se permite guardar: la fila no cumple el 100% de validadores (cédula duplicada en el snapshot de Drive)."
            )
            db.add(
                AuditoriaClienteAltaDesdeDrive(
                    batch_id=batch_id,
                    sheet_row_number=int(sheet_row),
                    cedula=str(info.get("col_e_cedula") or ""),
                    nombres=str(info.get("col_d_nombres") or ""),
                    telefono=str(info.get("col_f_telefono") or ""),
                    email=str(info.get("col_g_email") or ""),
                    comentario=comentario,
                    usuario_email=usuario_email,
                    estado="ERROR",
                    detalle_error=msg,
                )
            )
            db.commit()
            resultados.append({"sheet_row_number": sheet_row, "ok": False, "error": msg})
            continue

        cmp_k = str(info.get("cedula_cmp") or "")
        if cmp_k in seen_cmp:
            err += 1
            msg = "Cédula duplicada en la selección enviada."
            db.add(
                AuditoriaClienteAltaDesdeDrive(
                    batch_id=batch_id,
                    sheet_row_number=int(sheet_row),
                    cedula=str(info.get("cedula_para_crear") or info.get("col_e_cedula") or ""),
                    nombres=str(info.get("defaults", {}).get("nombres") or ""),
                    telefono=str(info.get("defaults", {}).get("telefono") or ""),
                    email=str(info.get("defaults", {}).get("email") or ""),
                    comentario=comentario,
                    usuario_email=usuario_email,
                    estado="ERROR",
                    detalle_error=msg,
                )
            )
            db.commit()
            resultados.append({"sheet_row_number": sheet_row, "ok": False, "error": msg})
            continue
        seen_cmp.add(cmp_k)

        ced = str(info.get("cedula_para_crear") or "").strip()
        defs = info.get("defaults") or {}
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
            err += 1
            msg = str(ve)
            db.add(
                AuditoriaClienteAltaDesdeDrive(
                    batch_id=batch_id,
                    sheet_row_number=int(sheet_row),
                    cedula=ced,
                    nombres=str(defs.get("nombres") or ""),
                    telefono=str(defs.get("telefono") or ""),
                    email=str(defs.get("email") or ""),
                    comentario=comentario,
                    usuario_email=usuario_email,
                    estado="ERROR",
                    detalle_error=f"Validación: {msg}"[:4000],
                )
            )
            db.commit()
            resultados.append({"sheet_row_number": sheet_row, "ok": False, "error": msg})
            continue

        try:
            row = create_cliente_from_payload(db, payload)
            ok += 1
            db.add(
                AuditoriaClienteAltaDesdeDrive(
                    batch_id=batch_id,
                    sheet_row_number=int(sheet_row),
                    cedula=str(row.cedula),
                    nombres=str(row.nombres),
                    telefono=str(row.telefono),
                    email=str(row.email),
                    comentario=comentario,
                    usuario_email=usuario_email,
                    estado="APROBADO_INSERTADO",
                    detalle_error=None,
                )
            )
            db.commit()
            resultados.append({"sheet_row_number": sheet_row, "ok": True, "cliente_id": row.id})
        except HTTPException as he:
            err += 1
            detail = he.detail
            if not isinstance(detail, str):
                detail = str(detail)
            try:
                db.rollback()
            except Exception:
                pass
            db.add(
                AuditoriaClienteAltaDesdeDrive(
                    batch_id=batch_id,
                    sheet_row_number=int(sheet_row),
                    cedula=ced,
                    nombres=str(defs.get("nombres") or ""),
                    telefono=str(defs.get("telefono") or ""),
                    email=str(defs.get("email") or ""),
                    comentario=comentario,
                    usuario_email=usuario_email,
                    estado="APROBADO_ERROR",
                    detalle_error=detail[:4000],
                )
            )
            db.commit()
            resultados.append({"sheet_row_number": sheet_row, "ok": False, "error": detail})
        except Exception as ex:  # pragma: no cover
            err += 1
            logger.exception("importar_seleccion_desde_drive fila=%s: %s", sheet_row, ex)
            try:
                db.rollback()
            except Exception:
                pass
            db.add(
                AuditoriaClienteAltaDesdeDrive(
                    batch_id=batch_id,
                    sheet_row_number=int(sheet_row),
                    cedula=ced,
                    nombres=str(defs.get("nombres") or ""),
                    telefono=str(defs.get("telefono") or ""),
                    email=str(defs.get("email") or ""),
                    comentario=comentario,
                    usuario_email=usuario_email,
                    estado="APROBADO_ERROR",
                    detalle_error=str(ex)[:4000],
                )
            )
            db.commit()
            resultados.append({"sheet_row_number": sheet_row, "ok": False, "error": str(ex)})

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
        "insertados_ok": ok,
        "errores": err,
        "resultados": resultados,
    }


def importar_fila_desde_drive(
    db: Session,
    *,
    usuario_email: str,
    body: ClienteDriveImportarFilaBody,
) -> Dict[str, Any]:
    """Inserta un cliente con ClienteCreate + auditoría; la cédula normalizada debe coincidir con `cedula_cmp` de la fila."""
    from app.api.v1.endpoints.clientes import create_cliente_from_payload

    snap = listar_candidatos_desde_drive(db)
    by_row = {int(c["sheet_row_number"]): c for c in (snap.get("candidatos") or [])}
    info = by_row.get(int(body.sheet_row_number))
    if info is None:
        raise HTTPException(
            status_code=404,
            detail="Fila no disponible para importación (no está en candidatos o la lista cambió).",
        )
    if not info.get("seleccionable"):
        raise HTTPException(
            status_code=400,
            detail="La fila no cumple el 100% de validadores de la hoja (cédula inválida o duplicada en el snapshot de Drive); no se permite guardar en clientes.",
        )

    cmp_expected = str(info.get("cedula_cmp") or "")
    cmp_sent = _cedula_cmp_unificada(body.cedula or "")
    if cmp_sent != cmp_expected:
        raise HTTPException(
            status_code=400,
            detail="La cédula enviada no coincide con la columna E de esta fila (tras normalización).",
        )

    cedula_crear = str(info.get("cedula_para_crear") or body.cedula or "").strip()
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
