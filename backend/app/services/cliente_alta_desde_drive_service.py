"""
Propuestas de alta de cliente desde snapshot `drive` (columnas D–G = nombres, cédula, teléfono, email).

Comparación de cédulas: misma normalización que POST /clientes/check-cedulas (`_normalizar_cedula_carga_masiva`).
Validación de formato de cédula: `validate_cedula` (mismas reglas que Validadores).
"""
from __future__ import annotations

import logging
import re
import uuid
from datetime import date
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.api.v1.endpoints.clientes import (
    _normalizar_cedula_carga_masiva,
    create_cliente_from_payload,
)
from app.api.v1.endpoints.validadores import validate_cedula
from app.models.auditoria_cliente_alta_desde_drive import AuditoriaClienteAltaDesdeDrive
from app.models.cliente import Cliente
from app.models.conciliacion_sheet import ConciliacionSheetMeta
from app.models.drive import DriveRow
from app.schemas.cliente import ClienteCreate

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


def listar_candidatos_desde_drive(db: Session) -> Dict[str, Any]:
    rows = db.execute(select(DriveRow).order_by(DriveRow.sheet_row_number.asc())).scalars().all()
    cedulas_bd = db.execute(select(Cliente.cedula)).scalars().all()
    en_bd: set[str] = set()
    for c in cedulas_bd or []:
        n = _normalizar_cedula_carga_masiva(c or "")
        if n:
            en_bd.add(n)

    conteos: Dict[str, int] = {}
    tmp: List[Tuple[DriveRow, str]] = []
    for r in rows or []:
        raw_e = _cell(getattr(r, "col_e", None))
        cmp_e = _normalizar_cedula_carga_masiva(raw_e)
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

        candidatos.append(
            {
                "sheet_row_number": r.sheet_row_number,
                "col_d_nombres": raw_d or None,
                "col_e_cedula": raw_e or None,
                "col_f_telefono": raw_f or None,
                "col_g_email": raw_g or None,
                "cedula_cmp": cmp_e,
                "cedula_valida": cedula_valida,
                "cedula_error": cedula_error,
                "cedula_para_crear": cedula_sugerida_bd if cedula_valida else None,
                "duplicada_en_hoja": dup_sheet,
                "seleccionable": cedula_valida and not dup_sheet,
                "defaults": {
                    "nombres": nombres_propuesto,
                    "telefono": raw_f or "",
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


def importar_seleccion_desde_drive(
    db: Session,
    *,
    usuario_email: str,
    comentario: Optional[str],
    sheet_rows: List[int],
) -> Dict[str, Any]:
    if not sheet_rows:
        raise HTTPException(status_code=400, detail="Debe enviar al menos una fila (sheet_row_number).")

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
                "Fila bloqueada: cédula inválida o duplicada en la hoja."
                if not info.get("cedula_valida")
                else "Fila bloqueada: cédula repetida en el snapshot de Drive."
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

    return {
        "batch_id": batch_id,
        "insertados_ok": ok,
        "errores": err,
        "resultados": resultados,
    }


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
