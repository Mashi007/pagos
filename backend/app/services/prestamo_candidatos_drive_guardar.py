"""
Guardado masivo desde snapshot `prestamo_candidatos_drive`: solo filas que cumplen validación previa.

Solo se crean préstamos (y se borran del snapshot) las filas que pasan todas las comprobaciones.
Las que no cumplen o fallan al crear el préstamo **permanecen en el snapshot** para revisarlas en pantalla,
corregir la hoja Drive y volver a recalcular o guardar cuando estén listas.
"""
from __future__ import annotations

import logging
import re
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.prestamo_candidato_drive import PrestamoCandidatoDrive
from app.schemas.auth import UserResponse
from app.services.prestamo_candidatos_drive_validadores import (
    cedula_cmp_es_tipo_j,
    cedula_cmp_es_tipo_v_o_e,
    cedula_cmp_es_tipo_venezolano_v,
    conteo_prestamos_aprobados_por_cedula_norm,
    conteo_prestamos_desistimiento_por_cedula_norm,
    conteo_prestamos_no_liquidado_terminado_por_cedula_norm,
)
from app.services.prestamo_candidatos_drive_normalizacion import (
    normalizar_modalidad_drive,
    parse_decimal_monto_drive,
    parse_fecha_q_iso_y_ambigua,
    parse_numero_cuotas_drive,
)
from app.schemas.prestamo import PrestamoCreate

logger = logging.getLogger(__name__)

# Antigüedad máxima permitida para `fecha_aprobacion` (columna Q de Drive)
# al crear un préstamo desde este flujo. La regla operativa es: la fecha no
# puede estar más atrás de 1 año (365 días) respecto a hoy. Para casos más
# antiguos, el alta debe hacerse por el módulo de préstamos manual.
MAX_DIAS_APROBACION_DRIVE = 365

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
    return parse_decimal_monto_drive(s)


def _parse_numero_cuotas(s: str) -> Optional[int]:
    return parse_numero_cuotas_drive(s)


def _parse_fecha_a_date(s: str) -> Optional[date]:
    """Acepta DD/MM/YYYY, YYYY-MM-DD y serial de Google Sheets."""
    from app.api.v1.endpoints.validadores import validate_fecha

    raw = (s or "").strip()
    if not raw:
        return None
    parsed_q, _amb = parse_fecha_q_iso_y_ambigua(raw)
    if parsed_q is not None:
        return parsed_q
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


def _fecha_texto_es_ambigua_dd_mm(s: str) -> bool:
    """
    Detecta fechas con slash potencialmente ambiguas para humanos (d/m y m/d válidos),
    por ejemplo 04/07/2026. Para evitar inversión de día/mes, estas se bloquean y se
    exige ISO (YYYY-MM-DD) o día > 12.
    """
    raw = (s or "").strip()
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{4})$", raw)
    if not m:
        return False
    d, mo = int(m.group(1)), int(m.group(2))
    return 1 <= d <= 12 and 1 <= mo <= 12


def _q_contiene_fecha_ambigua_dd_mm(q_val: str) -> bool:
    raw = (q_val or "").strip()
    if not raw:
        return False
    for sep in ("|", ";", "  ", "\n"):
        if sep in raw:
            parts = [p.strip() for p in raw.split(sep, 1) if p.strip()]
            return any(_fecha_texto_es_ambigua_dd_mm(p) for p in parts)
    return _fecha_texto_es_ambigua_dd_mm(raw)


def _fechas_desde_col_q(q_val: str) -> Optional[Tuple[date, date]]:
    """
    Parser histórico de Q (mantiene compatibilidad de formatos).
    Regla vigente de negocio se aplica después: requerimiento = aprobación - 1 día.
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


def _fecha_requerimiento_desde_aprobacion(ap_d: date) -> date:
    """
    Regla operativa para candidatos Drive:
    fecha_requerimiento se calcula automáticamente como 1 día antes de aprobación.
    """
    return ap_d - timedelta(days=1)


def _normalizar_modalidad(s: str) -> Optional[str]:
    return normalizar_modalidad_drive(s)


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
    prestamo_counts_aprob: Dict[str, int],
    prestamo_counts_desist: Optional[Dict[str, int]] = None,
    prestamo_counts_no_liq_term: Optional[Dict[str, int]] = None,
) -> Tuple[bool, List[str], Optional[PrestamoCreate]]:
    """Devuelve (ok, lista_motivos_si_no_ok, prestamo_create_si_ok)."""
    from app.api.v1.endpoints.validadores import validate_cedula
    from app.utils.cedula_almacenamiento import texto_cedula_comparable_bd
    from app.services.prestamo_candidatos_drive_validadores import (
        MSG_DRIVE_BLOQUEO_DESISTIMIENTO,
        MSG_DRIVE_BLOQUEO_V_NO_LIQUIDADO_TERMINADO,
        cedula_bloqueada_por_desistimiento_drive,
        cedula_v_bloqueada_por_no_liquidado_terminado,
        n_desistimiento_en_payload,
        n_no_liquidado_terminado_en_payload,
    )

    motivos: List[str] = []

    if payload.get("cedula_valida") is not True:
        motivos.append("cédula: formato no válido según validadores")
    ced_cmp_raw = _cell_str(payload.get("cedula_cmp"))
    # Misma clave que cupo/BD: 30771164 ≡ V30771164
    ced_cmp = texto_cedula_comparable_bd(ced_cmp_raw) or ced_cmp_raw
    if not ced_cmp:
        motivos.append("sin clave de cédula normalizada")

    n_aprob = 0
    if ced_cmp:
        n_aprob = int(prestamo_counts_aprob.get(ced_cmp, 0) or 0)
        # Compat: conteos viejos indexados solo por dígitos
        if n_aprob == 0 and ced_cmp.startswith("V") and ced_cmp[1:].isdigit():
            n_aprob = int(prestamo_counts_aprob.get(ced_cmp[1:], 0) or 0)
    if (
        cedula_cmp_es_tipo_v_o_e(ced_cmp)
        and not cedula_cmp_es_tipo_j(ced_cmp)
        and n_aprob >= 1
    ):
        motivos.append(
            "cédula tipo V o E: máximo un préstamo APROBADO (innegociable; LIQUIDADO no cuenta). "
            f"Hay {n_aprob} préstamo(s) APROBADO en cartera."
        )

    # Regla absoluta Drive: DESISTIMIENTO en cartera → no alta nueva (V/E/J).
    if ced_cmp:
        n_desist = 0
        if prestamo_counts_desist is not None:
            n_desist = int(prestamo_counts_desist.get(ced_cmp, 0) or 0)
            if n_desist == 0 and ced_cmp.startswith("V") and ced_cmp[1:].isdigit():
                n_desist = int(prestamo_counts_desist.get(ced_cmp[1:], 0) or 0)
        if n_desist == 0:
            n_desist = n_desistimiento_en_payload(payload)
        if cedula_bloqueada_por_desistimiento_drive(n_desist):
            motivos.append(MSG_DRIVE_BLOQUEO_DESISTIMIENTO)

    # V: solo alta nueva si cartera está Liquidado / Terminado (o sin préstamos).
    if ced_cmp and cedula_cmp_es_tipo_venezolano_v(ced_cmp):
        n_no_liq_term = 0
        if prestamo_counts_no_liq_term is not None:
            n_no_liq_term = int(prestamo_counts_no_liq_term.get(ced_cmp, 0) or 0)
            if n_no_liq_term == 0 and ced_cmp.startswith("V") and ced_cmp[1:].isdigit():
                n_no_liq_term = int(prestamo_counts_no_liq_term.get(ced_cmp[1:], 0) or 0)
        if n_no_liq_term == 0:
            n_no_liq_term = n_no_liquidado_terminado_en_payload(payload)
        if cedula_v_bloqueada_por_no_liquidado_terminado(
            es_v=True, n_no_liquidado_terminado=n_no_liq_term
        ):
            motivos.append(MSG_DRIVE_BLOQUEO_V_NO_LIQUIDADO_TERMINADO)

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
    # No usar payload.huella_no_comparable: puede quedar stale (p. ej. monto Bs.S
    # que ahora sí parsea). Los chequeos de N/R/S/Q más abajo bastan.
    if _q_contiene_fecha_ambigua_dd_mm(q_s):
        motivos.append(
            "fecha (Q) ambigua: use formato ISO YYYY-MM-DD para evitar confusión día/mes "
            "(ejemplo ambiguo: 04/07/2026)."
        )
    fechas = _fechas_desde_col_q(q_s)
    if fechas is None:
        motivos.append("fecha (Q) inválida o vacía (DD/MM/YYYY o YYYY-MM-DD)")
    else:
        _req_entrada, ap_d = fechas
        req_d = _fecha_requerimiento_desde_aprobacion(ap_d)
        # Regla operativa (alineada a UI): aprobación (Q) no puede ser anterior a hoy
        # en más de `MAX_DIAS_APROBACION_DRIVE` días (1 año). Para casos más antiguos
        # corresponde el alta manual en el módulo de préstamos.
        if (date.today() - ap_d).days > MAX_DIAS_APROBACION_DRIVE:
            motivos.append(
                f"fecha de aprobación (Q) supera {MAX_DIAS_APROBACION_DRIVE} días "
                "(1 año) de antigüedad; no se permite guardar desde este flujo."
            )
        elif monto is not None and ncu is not None:
            from app.services.prestamos.prestamo_reimporte_liquidado import (
                motivo_si_reimporte_liquidado_desde_fechas,
            )

            ced_para_huella = ced_cmp or _cell_str(payload.get("col_e_cedula"))
            mod_pre = _normalizar_modalidad(_cell_str(payload.get("col_s_modalidad_pago")))
            if mod_pre:
                dup_liq = motivo_si_reimporte_liquidado_desde_fechas(
                    db,
                    cedula=ced_para_huella,
                    fecha_aprobacion=ap_d,
                    fecha_requerimiento=req_d,
                    total_financiamiento=monto,
                    numero_cuotas=ncu,
                    modalidad_pago=mod_pre,
                )
                if dup_liq:
                    motivos.append(dup_liq)

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
    _req_entrada, ap_d = fechas
    req_d = _fecha_requerimiento_desde_aprobacion(ap_d)

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

    En el mismo lote: a lo sumo un alta por cédula comparable (V/E), aunque la hoja traiga
    la misma cédula en varias filas (`duplicada_en_hoja` no bastaba porque no bloqueaba el guardado).
    """
    from app.api.v1.endpoints.prestamos import crear_prestamo_servicio_interno
    from app.utils.cedula_almacenamiento import texto_cedula_comparable_bd

    prestamo_counts_aprob = conteo_prestamos_aprobados_por_cedula_norm(db)
    prestamo_counts_desist = conteo_prestamos_desistimiento_por_cedula_norm(db)
    prestamo_counts_no_liq_term = conteo_prestamos_no_liquidado_terminado_por_cedula_norm(db)

    rows = list(
        db.execute(select(PrestamoCandidatoDrive).order_by(PrestamoCandidatoDrive.sheet_row_number.asc()))
        .scalars()
        .all()
        or []
    )

    insertados = 0
    omitidos: List[Dict[str, Any]] = []
    errores: List[Dict[str, Any]] = []
    # Evita 2 altas V/E la misma noche si Drive repite la cédula en N filas.
    cedulas_insertadas_lote: set[str] = set()

    for r in rows:
        payload = r.payload if isinstance(r.payload, dict) else {}
        cmp_fila = texto_cedula_comparable_bd(
            _cell_str(payload.get("cedula_cmp")) or (r.cedula_cmp or "")
        )
        if (
            cmp_fila
            and cedula_cmp_es_tipo_v_o_e(cmp_fila)
            and not cedula_cmp_es_tipo_j(cmp_fila)
            and cmp_fila in cedulas_insertadas_lote
        ):
            omitidos.append(
                {
                    "sheet_row_number": r.sheet_row_number,
                    "cedula_cmp": r.cedula_cmp,
                    "motivos": [
                        "cédula V/E ya insertada en este lote automático "
                        f"(otra fila de hoja con la misma clave {cmp_fila})."
                    ],
                }
            )
            continue
        ok, motivos, pc = _motivos_no_100(
            payload,
            db,
            prestamo_counts_aprob,
            prestamo_counts_desist,
            prestamo_counts_no_liq_term,
        )
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
            if cmp_fila:
                cedulas_insertadas_lote.add(cmp_fila)
                prestamo_counts_aprob[cmp_fila] = int(
                    prestamo_counts_aprob.get(cmp_fila, 0) or 0
                ) + 1
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
    from app.services.prestamo_candidatos_drive_validadores import (
        conteos_cupo_para_una_cedula,
    )

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
    cmp_fila = (_cell_str(payload.get("cedula_cmp")) or (r.cedula_cmp or "")).strip()
    # Solo esta cédula: el conteo global de APROBADO era lento y hacía timeout en UI.
    cupo = conteos_cupo_para_una_cedula(db, cmp_fila) if cmp_fila else {
        "aprob": 0,
        "desist": 0,
        "no_liq_term": 0,
    }
    prestamo_counts_aprob = {cmp_fila: int(cupo.get("aprob") or 0)} if cmp_fila else {}
    prestamo_counts_desist = {cmp_fila: int(cupo.get("desist") or 0)} if cmp_fila else {}
    prestamo_counts_no_liq_term = (
        {cmp_fila: int(cupo.get("no_liq_term") or 0)} if cmp_fila else {}
    )
    ok, motivos, pc = _motivos_no_100(
        payload,
        db,
        prestamo_counts_aprob,
        prestamo_counts_desist,
        prestamo_counts_no_liq_term,
    )
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


def ejecutar_eliminar_candidatos_drive_seleccionados(
    db: Session,
    *,
    ids: List[int],
    usuario_email: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Elimina del snapshot las filas seleccionadas y las registra en pasivo
    (`drive_candidatos_eliminados_pasivos`) para que el refresh no las reinsertee.
    """
    from app.services.drive_candidatos_eliminados_pasivos import (
        ORIGEN_PRESTAMO,
        registrar_eliminados_pasivos_bulk,
    )

    ids_clean = sorted({int(x) for x in (ids or []) if int(x) > 0})
    if not ids_clean:
        return {
            "eliminados": 0,
            "seleccionados": 0,
            "mensaje": "No se recibieron filas válidas para eliminar.",
        }

    rows = list(
        db.execute(
            select(PrestamoCandidatoDrive).where(PrestamoCandidatoDrive.id.in_(ids_clean))
        )
        .scalars()
        .all()
        or []
    )
    pasivo_items = [
        (str(r.cedula_cmp or "").strip(), int(r.sheet_row_number) if r.sheet_row_number else None)
        for r in rows
        if str(r.cedula_cmp or "").strip()
    ]

    try:
        if pasivo_items:
            registrar_eliminados_pasivos_bulk(
                db,
                origen=ORIGEN_PRESTAMO,
                items=pasivo_items,
                usuario_email=usuario_email,
            )
        stmt = delete(PrestamoCandidatoDrive).where(PrestamoCandidatoDrive.id.in_(ids_clean))
        result = db.execute(stmt)
        db.commit()
    except Exception:
        db.rollback()
        raise

    eliminados = int(getattr(result, "rowcount", 0) or 0)
    return {
        "eliminados": eliminados,
        "seleccionados": len(ids_clean),
        "pasivos_registrados": len(pasivo_items),
        "mensaje": (
            f"Se eliminaron {eliminados} fila(s) del snapshot y se guardaron en pasivo "
            f"para que no reaparezcan en el próximo recálculo "
            f"(seleccionadas: {len(ids_clean)})."
        ),
    }
