"""
Guardado masivo desde snapshot `prestamo_candidatos_drive`: solo filas que cumplen validación previa.

Solo se crean préstamos (y se borran del snapshot) las filas que pasan todas las comprobaciones.
Las que no cumplen o fallan al crear el préstamo **permanecen en el snapshot** para revisarlas en pantalla,
corregir la hoja Drive y volver a recalcular o guardar cuando estén listas.
"""
from __future__ import annotations

import logging
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.prestamo_candidato_drive import PrestamoCandidatoDrive
from app.schemas.auth import UserResponse
from app.services.prestamo_candidatos_drive_validadores import (
    cedula_cmp_es_tipo_v_o_e,
    conteo_prestamos_por_cedula_norm,
)
from app.schemas.prestamo import PrestamoCreate

logger = logging.getLogger(__name__)

_MODALIDADES = frozenset({"MENSUAL", "QUINCENAL", "SEMANAL"})

# Valor antiguo mal escrito en snapshots previos al refresh.
_LEGACY_PRODUCTO_DRIVE_TYPOS = frozenset({"FINCAMIRETO"})


def _producto_desde_payload(payload: Dict[str, Any]) -> str:
    raw = _cell_str(payload.get("producto")) or "FINANCIAMIENTO"
    if raw.upper() in _LEGACY_PRODUCTO_DRIVE_TYPOS:
        return "FINANCIAMIENTO"
    return raw


def _cell_str(v: Any) -> str:
    if v is None:
        return ""
    return str(v).strip()


def _parse_decimal_monto(s: str) -> Optional[Decimal]:
    """
    Monto desde celda tipo hoja VE/EU: miles con punto y decimal con coma (ej. 1.575,00).
    El reemplazo ingenuo coma→punto deja '1.575.00' y Decimal falla; por eso se normaliza antes.
    """
    t = (s or "").strip().replace(" ", "")
    for sym in ("$", "€", "Bs.", "Bs", "USD", "VES"):
        t = re.sub(re.escape(sym), "", t, flags=re.I).strip()
    if not t:
        return None
    last_comma = t.rfind(",")
    last_dot = t.rfind(".")
    if "," in t and "." in t:
        if last_comma > last_dot:
            t = t.replace(".", "").replace(",", ".")
        else:
            t = t.replace(",", "")
    elif "," in t:
        t = t.replace(",", ".")
    try:
        d = Decimal(t)
        if d <= 0:
            return None
        return d
    except (InvalidOperation, ValueError):
        return None


def _parse_numero_cuotas(s: str) -> Optional[int]:
    t = re.sub(r"\D", "", s or "")
    if not t:
        return None
    try:
        n = int(t)
        if 1 <= n <= 50:
            return n
    except ValueError:
        pass
    return None


def _parse_fecha_a_date(s: str) -> Optional[date]:
    """Acepta DD/MM/YYYY (validadores) o YYYY-MM-DD."""
    from app.api.v1.endpoints.validadores import validate_fecha

    raw = (s or "").strip()
    if not raw:
        return None
    if re.match(r"^\d{4}-\d{2}-\d{2}", raw):
        try:
            return date.fromisoformat(raw[:10])
        except ValueError:
            return None
    vf = validate_fecha(raw)
    if not vf.get("valido"):
        return None
    fmt = str(vf.get("valor_formateado") or raw).strip()
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", fmt)
    if not m:
        return None
    d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        return date(y, mo, d)
    except ValueError:
        return None


def _fechas_desde_col_q(q_val: str) -> Optional[Tuple[date, date]]:
    """
    Una celda Q: misma fecha para requerimiento y aprobación.
    Dos fechas separadas por '|', ';' o espacio doble: primera = requerimiento, segunda = aprobación.
    """
    raw = (q_val or "").strip()
    if not raw:
        return None
    for sep in ("|", ";", "  ", "\n"):
        if sep in raw:
            parts = [p.strip() for p in raw.split(sep, 1) if p.strip()]
            if len(parts) >= 2:
                d1 = _parse_fecha_a_date(parts[0])
                d2 = _parse_fecha_a_date(parts[1])
                if d1 and d2:
                    return (d1, d2)
            break
    d = _parse_fecha_a_date(raw)
    if d:
        return (d, d)
    return None


def _normalizar_modalidad(s: str) -> Optional[str]:
    t = _cell_str(s).upper()
    if not t:
        return None
    for m in _MODALIDADES:
        if m in t or t == m:
            return m
    if "QUINCENA" in t:
        return "QUINCENAL"
    if "SEMANA" in t:
        return "SEMANAL"
    if "MENS" in t or "MES" in t:
        return "MENSUAL"
    return None


def _cliente_id_por_cedula_normalizada(db: Session, cedula_cmp: str) -> Optional[int]:
    """
    Resuelve cliente por clave de cédula alineada a POST /clientes (sin cargar toda la tabla en memoria).
    """
    from app.api.v1.endpoints.clientes import (
        _cedula_clave_comparacion_clientes,
        _expr_cedula_normalizada_sql,
    )

    if not (cedula_cmp or "").strip():
        return None
    key = _cedula_clave_comparacion_clientes(cedula_cmp.strip())
    if not key:
        return None
    ced_sql = _expr_cedula_normalizada_sql(Cliente.cedula)
    row = db.execute(select(Cliente.id).where(ced_sql == key)).first()
    return int(row[0]) if row else None


def _motivos_no_100(
    payload: Dict[str, Any],
    db: Session,
    prestamo_counts: Dict[str, int],
) -> Tuple[bool, List[str], Optional[PrestamoCreate]]:
    """Devuelve (ok, lista_motivos_si_no_ok, prestamo_create_si_ok)."""
    from app.api.v1.endpoints.validadores import validate_cedula

    motivos: List[str] = []

    if payload.get("cedula_valida") is not True:
        motivos.append("cédula: formato no válido según validadores")
    if payload.get("duplicada_en_hoja") is True:
        motivos.append("cédula duplicada en la hoja (columna E repetida)")
    ced_cmp = _cell_str(payload.get("cedula_cmp"))
    if not ced_cmp:
        motivos.append("sin clave de cédula normalizada")

    n_live = int(prestamo_counts.get(ced_cmp, 0) or 0) if ced_cmp else 0
    if cedula_cmp_es_tipo_v_o_e(ced_cmp) and n_live >= 1:
        motivos.append(
            "cédula tipo V o E: máximo un préstamo en cartera (innegociable). "
            f"Hay {n_live} préstamo(s) en tabla con esta cédula normalizada."
        )
    cliente_id = _cliente_id_por_cedula_normalizada(db, ced_cmp) if ced_cmp else None
    if cliente_id is None:
        motivos.append("cliente no existe en BD para esta cédula")

    total_s = _cell_str(payload.get("col_n_total_financiamiento"))
    monto = _parse_decimal_monto(total_s)
    if monto is None:
        motivos.append("total financiamiento (N) inválido o no positivo")

    ncu_s = _cell_str(payload.get("col_r_numero_cuotas"))
    ncu = _parse_numero_cuotas(ncu_s)
    if ncu is None:
        motivos.append("número de cuotas (R) inválido (1-50)")

    q_s = _cell_str(payload.get("col_q_fecha"))
    fechas = _fechas_desde_col_q(q_s)
    if fechas is None:
        motivos.append("fecha (Q) inválida o vacía (DD/MM/YYYY o YYYY-MM-DD)")
    else:
        req_d, ap_d = fechas
        if ap_d < req_d:
            motivos.append("fecha aprobación anterior a fecha requerimiento")
        # Innegociable (alineado a UI): aprobación (Q) no puede ser anterior a hoy en más de 30 días.
        if (date.today() - ap_d).days > 30:
            motivos.append(
                "fecha de aprobación (Q) supera 30 días de antigüedad; no se permite guardar (innegociable)"
            )

    mod = _normalizar_modalidad(_cell_str(payload.get("col_s_modalidad_pago")))
    if mod is None:
        motivos.append("modalidad (S) debe ser MENSUAL, QUINCENAL o SEMANAL")

    analista = _cell_str(payload.get("col_j_analista"))
    if not analista:
        motivos.append("analista (J) obligatorio")

    raw_ced = _cell_str(payload.get("col_e_cedula"))
    vced = validate_cedula(raw_ced)
    if not vced.get("valido"):
        motivos.append(f"cédula en columna E: {vced.get('error') or 'inválida'}")

    if motivos:
        return False, motivos, None

    if fechas is None or monto is None or ncu is None or mod is None or cliente_id is None:
        return False, ["validación interna incompleta"], None
    req_d, ap_d = fechas

    try:
        pc = PrestamoCreate(
            cliente_id=cliente_id,
            total_financiamiento=monto,
            fecha_requerimiento=req_d,
            fecha_aprobacion=ap_d,
            modalidad_pago=mod,
            numero_cuotas=ncu,
            producto=_producto_desde_payload(payload),
            analista=analista,
            concesionario=_cell_str(payload.get("col_k_concesionario")) or None,
            modelo=_cell_str(payload.get("col_i_modelo_vehiculo")) or None,
            estado="APROBADO",
            omitir_validacion_huella_duplicada=False,
        )
    except ValidationError as ve:
        return False, [f"Pydantic: {ve}"], None

    return True, [], pc


def ejecutar_guardar_candidatos_drive_validados_100(
    db: Session,
    *,
    current_user: UserResponse,
) -> Dict[str, Any]:
    """
    Recorre `prestamo_candidatos_drive` y crea préstamos solo para filas que cumplen `_motivos_no_100`.
    Cada inserción correcta elimina esa fila del snapshot. El resto queda intacto para revisión y pulido.
    """
    from app.api.v1.endpoints.prestamos import crear_prestamo_servicio_interno

    prestamo_counts = conteo_prestamos_por_cedula_norm(db)

    rows = list(
        db.execute(select(PrestamoCandidatoDrive).order_by(PrestamoCandidatoDrive.sheet_row_number.asc()))
        .scalars()
        .all()
        or []
    )

    insertados = 0
    omitidos: List[Dict[str, Any]] = []
    errores: List[Dict[str, Any]] = []

    for r in rows:
        payload = r.payload if isinstance(r.payload, dict) else {}
        ok, motivos, pc = _motivos_no_100(payload, db, prestamo_counts)
        if not ok or pc is None:
            omitidos.append(
                {
                    "sheet_row_number": r.sheet_row_number,
                    "cedula_cmp": r.cedula_cmp,
                    "motivos": motivos,
                }
            )
            continue
        try:
            crear_prestamo_servicio_interno(db, pc, current_user)
            db.delete(r)
            db.commit()
            insertados += 1
            cmp_upd = (_cell_str(payload.get("cedula_cmp")) or (r.cedula_cmp or "")).strip()
            if cmp_upd:
                prestamo_counts[cmp_upd] = int(prestamo_counts.get(cmp_upd, 0) or 0) + 1
        except HTTPException as he:
            db.rollback()
            msg = str(he.detail) if he.detail else str(he)
            errores.append(
                {
                    "sheet_row_number": r.sheet_row_number,
                    "cedula_cmp": r.cedula_cmp,
                    "error": msg,
                }
            )
            logger.warning(
                "[prestamo_candidatos_drive_guardar] fila=%s cedula=%s HTTP %s",
                r.sheet_row_number,
                r.cedula_cmp,
                msg,
            )
        except Exception as e:
            db.rollback()
            errores.append(
                {
                    "sheet_row_number": r.sheet_row_number,
                    "cedula_cmp": r.cedula_cmp,
                    "error": str(e),
                }
            )
            logger.exception(
                "[prestamo_candidatos_drive_guardar] fila=%s: %s",
                r.sheet_row_number,
                e,
            )

    pendientes = len(omitidos) + len(errores)
    return {
        "insertados_ok": insertados,
        "omitidos_no_100": len(omitidos),
        "errores_al_guardar": len(errores),
        "pendientes_en_snapshot": pendientes,
        "omitidos": omitidos,
        "errores": errores,
        "mensaje": (
            f"Guardado: {insertados} préstamo(s) creado(s) y quitado(s) del snapshot; "
            f"{len(omitidos)} omitido(s) por no cumplir validación; {len(errores)} error(es) al crear. "
            + (
                f"Quedan {pendientes} candidato(s) en el snapshot para revisar, corregir en Drive y seguir puliendo."
                if pendientes
                else "No quedan pendientes de este lote en el snapshot."
            )
        ),
    }


def ejecutar_guardar_candidatos_drive_una_fila(
    db: Session,
    *,
    current_user: UserResponse,
    sheet_row_number: int,
) -> Dict[str, Any]:
    """
    Crea un préstamo solo si la fila cumple la misma validación que el guardado masivo.
    Si no cumple o falla la creación, la candidatura **sigue en el snapshot** para revisión.
    """
    from app.api.v1.endpoints.prestamos import crear_prestamo_servicio_interno

    prestamo_counts = conteo_prestamos_por_cedula_norm(db)
    r = db.scalar(
        select(PrestamoCandidatoDrive)
        .where(PrestamoCandidatoDrive.sheet_row_number == int(sheet_row_number))
        .order_by(PrestamoCandidatoDrive.id.desc())
        .limit(1)
    )
    if r is None:
        return {
            "ok": False,
            "insertados_ok": 0,
            "sheet_row_number": int(sheet_row_number),
            "motivos": [f"No hay candidato en snapshot para la fila de hoja {sheet_row_number}."],
            "mensaje": "Fila no encontrada en el snapshot.",
        }

    payload = r.payload if isinstance(r.payload, dict) else {}
    ok, motivos, pc = _motivos_no_100(payload, db, prestamo_counts)
    if not ok or pc is None:
        return {
            "ok": False,
            "insertados_ok": 0,
            "sheet_row_number": int(sheet_row_number),
            "motivos": motivos,
            "mensaje": (
                "La fila no cumple los requisitos para crear el préstamo; no se guardó nada. "
                "Sigue en el snapshot para revisar motivos, corregir datos o la hoja Drive y volver a intentar."
            ),
        }

    try:
        crear_prestamo_servicio_interno(db, pc, current_user)
        db.delete(r)
        db.commit()
        cmp_upd = (_cell_str(payload.get("cedula_cmp")) or (r.cedula_cmp or "")).strip()
        if cmp_upd:
            prestamo_counts[cmp_upd] = int(prestamo_counts.get(cmp_upd, 0) or 0) + 1
    except HTTPException as he:
        db.rollback()
        msg = str(he.detail) if he.detail else str(he)
        logger.warning(
            "[prestamo_candidatos_drive_guardar] fila única sheet_row=%s HTTP %s",
            sheet_row_number,
            msg,
        )
        return {
            "ok": False,
            "insertados_ok": 0,
            "sheet_row_number": int(sheet_row_number),
            "motivos": [msg],
            "mensaje": (
                "Error al crear el préstamo; no se eliminó la fila del snapshot. "
                "Revise el motivo, corrija y vuelva a guardar."
            ),
        }
    except Exception as e:
        db.rollback()
        logger.exception(
            "[prestamo_candidatos_drive_guardar] fila única sheet_row=%s: %s",
            sheet_row_number,
            e,
        )
        return {
            "ok": False,
            "insertados_ok": 0,
            "sheet_row_number": int(sheet_row_number),
            "motivos": [str(e)],
            "mensaje": (
                "Error al crear el préstamo; la candidatura sigue en el snapshot para revisión y corrección."
            ),
        }

    return {
        "ok": True,
        "insertados_ok": 1,
        "sheet_row_number": int(sheet_row_number),
        "motivos": [],
        "mensaje": (
            f"Préstamo creado para la fila de hoja {sheet_row_number}. "
            "Esa fila se quitó del snapshot; las demás candidaturas permanecen para revisión."
        ),
    }
