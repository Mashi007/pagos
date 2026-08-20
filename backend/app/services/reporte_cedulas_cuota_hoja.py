"""
Excel Cédula | Cuota | Ene–Ago 2026 para las cédulas de la hoja Drive.

Cuota: prestamos.cuota_periodo (APROBADO; si no hay, LIQUIDADO, DESISTIMIENTO u otro).
Cédula hoja E84491751 cruza con V84491751 o 84491751 en sistema.
APROBADO: N° cuota / Vencido / Pagos / Saldo solo con 4+ cuotas en MORA.
F. venc. va para todos (APROBADO, LIQUIDADO, DESISTIMIENTO): cuota impaga
que vence en ese mes calendario.
Cada mes: Vencido (hasta ese mes, desde el inicio del préstamo si sigue
impago). Tabla de amortización: el saldo pasa al mes siguiente; si hay
pagos se resta, si no se traslada la deuda más la nueva cuota vencida.
Si ya vencieron todas las
cuotas (p. ej. 12/12) y siguen impagas, ese número va en todos los meses
(solo LIQUIDADO / DESISTIMIENTO).
"""
from __future__ import annotations

import csv
import io
import logging
import urllib.error
import urllib.request
from calendar import monthrange
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.models.prestamo import Prestamo
from app.utils.cedula_almacenamiento import (
    expr_cedula_normalizada_para_comparar,
    texto_cedula_comparable_bd,
)

logger = logging.getLogger(__name__)

_SHEET_EXPORT = (
    "https://docs.google.com/spreadsheets/d/{sid}/export?format=csv"
)
_ESTADOS_PRESTAMO = ("APROBADO", "LIQUIDADO", "DESISTIMIENTO")
_ESTADOS_EXCLUIDOS = ("DRAFT", "RECHAZADO")
_ANIO_VENCIDOS = 2026
_MES_DESDE = 1
_MES_HASTA = 8
MESES_VENCIDOS: Tuple[Tuple[int, int, str], ...] = tuple(
    (_ANIO_VENCIDOS, m, nombre)
    for m, nombre in enumerate(
        (
            "Enero 2026",
            "Febrero 2026",
            "Marzo 2026",
            "Abril 2026",
            "Mayo 2026",
            "Junio 2026",
            "Julio 2026",
            "Agosto 2026",
        ),
        start=1,
    )
)
_CLAVES_MES = tuple(f"{anio}-{mes:02d}" for anio, mes, _ in MESES_VENCIDOS)
MIN_CUOTAS_MORA_APROBADO = 4


def _sheet_id() -> str:
    from app.core.config import settings

    return (
        getattr(settings, "REPORTE_CUOTAS_JUN_AGO_SHEET_ID", None)
        or "1_Qean5MoSc1vWy6hMAAqOcMJeZzn9iUspJTqsOqZEqs"
    ).strip()


def _a_decimal(val: Any) -> Optional[Decimal]:
    if val is None or val == "":
        return None
    try:
        d = Decimal(str(val))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return d


def cuota_unica_de_prestamos(
    prestamos: Sequence[Tuple[str, Any]],
) -> Optional[Decimal]:
    """
    Un solo monto si todos los préstamos elegibles coinciden.

    Prioriza APROBADO. Si no hay, LIQUIDADO/DESISTIMIENTO u otro estado con un solo monto.
    Distintos montos → None (no se elige ni se promedia).
    """
    if not prestamos:
        return None
    aprobados = [
        _a_decimal(m)
        for est, m in prestamos
        if str(est or "").strip().upper() == "APROBADO"
    ]
    pool = [x for x in aprobados if x is not None]
    if not pool:
        preferidos = [
            _a_decimal(m)
            for est, m in prestamos
            if str(est or "").strip().upper() in ("LIQUIDADO", "DESISTIMIENTO")
        ]
        pool = [x for x in preferidos if x is not None]
    if not pool:
        pool = [x for x in (_a_decimal(m) for _e, m in prestamos) if x is not None]
    if not pool:
        return None
    montos = {x.quantize(Decimal("0.01")) for x in pool}
    if len(montos) != 1:
        return None
    return montos.pop()


def estado_actual_de_prestamos(
    prestamos: Sequence[Tuple[str, Any]],
) -> Optional[str]:
    """
    Estado actual del préstamo. Si hay APROBADO, ese.
    Si no, un único estado; si hay varios reales, se listan separados por ' / '.
    """
    estados: List[str] = []
    for est, _m in prestamos:
        e = str(est or "").strip().upper()
        if e and e not in estados:
            estados.append(e)
    if not estados:
        return None
    if "APROBADO" in estados:
        return "APROBADO"
    if len(estados) == 1:
        return estados[0]
    orden = ("LIQUIDADO", "DESISTIMIENTO")
    ordenados = [e for e in orden if e in estados]
    ordenados.extend(e for e in estados if e not in orden)
    return " / ".join(ordenados)


def _digitos_cedula(ced: str) -> str:
    return "".join(ch for ch in (ced or "") if ch.isdigit())


def _claves_equivalentes_cedula(ced: str) -> List[str]:
    """E84491751, V84491751 y 84491751 se tratan como la misma persona."""
    full = texto_cedula_comparable_bd(ced)
    digits = _digitos_cedula(full)
    keys: List[str] = []
    for k in (full, digits, *(f"{p}{digits}" for p in "VEJG" if digits)):
        if k and k not in keys:
            keys.append(k)
    return keys


def _expandir_claves_sql(cedulas: Iterable[str]) -> List[str]:
    out: List[str] = []
    seen: set[str] = set()
    for c in cedulas:
        for k in _claves_equivalentes_cedula(c):
            if k not in seen:
                seen.add(k)
                out.append(k)
    return out


def _prestamos_para_cedula_hoja(
    ced_hoja: str,
    prestamos_por_norm: Dict[str, List[Tuple[str, Any]]],
) -> List[Tuple[str, Any]]:
    k = texto_cedula_comparable_bd(ced_hoja)
    if k in prestamos_por_norm:
        return prestamos_por_norm[k]
    digits = _digitos_cedula(k)
    if not digits:
        return []
    merged: List[Tuple[str, Any]] = []
    seen: set[Tuple[str, str]] = set()
    for mk, prests in prestamos_por_norm.items():
        if _digitos_cedula(mk) != digits:
            continue
        for est, monto in prests:
            ident = (str(est), str(monto))
            if ident in seen:
                continue
            seen.add(ident)
            merged.append((est, monto))
    return merged


def _vencidos_para_cedula_hoja(
    ced_hoja: str,
    vencidos_por_norm: Dict[str, Dict[str, Decimal]],
) -> Dict[str, Decimal]:
    k = texto_cedula_comparable_bd(ced_hoja)
    if k in vencidos_por_norm:
        return vencidos_por_norm[k]
    digits = _digitos_cedula(k)
    if not digits:
        return {}
    acc: Dict[str, Decimal] = {}
    for mk, meses in vencidos_por_norm.items():
        if _digitos_cedula(mk) != digits:
            continue
        for clave, val in meses.items():
            acc[clave] = (acc.get(clave, Decimal("0")) + val).quantize(Decimal("0.01"))
    return acc


def _nros_para_cedula_hoja(
    ced_hoja: str,
    nros_por_norm: Dict[str, Dict[str, int]],
) -> Dict[str, int]:
    k = texto_cedula_comparable_bd(ced_hoja)
    if k in nros_por_norm:
        return nros_por_norm[k]
    digits = _digitos_cedula(k)
    if not digits:
        return {}
    acc: Dict[str, int] = {}
    for mk, meses in nros_por_norm.items():
        if _digitos_cedula(mk) != digits:
            continue
        for clave, n in meses.items():
            prev = acc.get(clave)
            if prev is None or int(n) > prev:
                acc[clave] = int(n)
    return acc


def _fechas_para_cedula_hoja(
    ced_hoja: str,
    fechas_por_norm: Dict[str, Dict[str, date]],
) -> Dict[str, date]:
    k = texto_cedula_comparable_bd(ced_hoja)
    if k in fechas_por_norm:
        return fechas_por_norm[k]
    digits = _digitos_cedula(k)
    if not digits:
        return {}
    acc: Dict[str, date] = {}
    for mk, meses in fechas_por_norm.items():
        if _digitos_cedula(mk) != digits:
            continue
        for clave, fv in meses.items():
            prev = acc.get(clave)
            if prev is None or fv > prev:
                acc[clave] = fv
    return acc


def _clave_pagos(clave_mes: str) -> str:
    return f"pagos_{clave_mes}"


def _clave_saldo(clave_mes: str) -> str:
    return f"saldo_{clave_mes}"


def _clave_nro(clave_mes: str) -> str:
    return f"nro_{clave_mes}"


def _clave_fv(clave_mes: str) -> str:
    return f"fv_{clave_mes}"


def _ultimo_dia(anio: int, mes: int) -> date:
    return date(anio, mes, monthrange(anio, mes)[1])


def _as_date(v: Any) -> Optional[date]:
    if v is None:
        return None
    return v.date() if hasattr(v, "date") else v


def _pendiente_item_al(
    fv: Any,
    monto: Any,
    pagado: Any,
    fp: Any,
    as_of: date,
) -> Optional[Decimal]:
    fv_d = _as_date(fv)
    if fv_d is None or fv_d > as_of:
        return None
    fp_d = _as_date(fp)
    if fp_d is not None and fp_d > as_of:
        pag_eff, fp_eff = Decimal("0"), None
    else:
        pag_eff, fp_eff = pagado, fp_d
    return pendiente_vencido(monto, pag_eff, fv_d, fp_eff, as_of)


def _estado_item_al(
    fv: Any,
    monto: Any,
    pagado: Any,
    fp: Any,
    as_of: date,
) -> Optional[str]:
    from app.services.cuota_estado import clasificar_estado_cuota

    fv_d = _as_date(fv)
    if fv_d is None:
        return None
    m = _a_decimal(monto)
    if m is None:
        return None
    fp_d = _as_date(fp)
    if fp_d is not None and fp_d > as_of:
        pag_eff = Decimal("0")
    else:
        pag_eff = _a_decimal(pagado) or Decimal("0")
        if fp_d is not None and pag_eff < Decimal("0.01"):
            pag_eff = m
    return clasificar_estado_cuota(float(pag_eff), float(m), fv_d, as_of)


def conteo_cuotas_en_mora(
    items: Sequence[Tuple[Any, Any, Any, Any, Any, Any]],
    as_of: date,
) -> int:
    """Cantidad de cuotas con estado MORA a la fecha. No incluye VENCIDO."""
    n = 0
    for _nro, fv, monto, pagado, fp, _tot in items:
        if _estado_item_al(fv, monto, pagado, fp, as_of) == "MORA":
            n += 1
    return n


def nros_cuotas_en_mora(
    items: Sequence[Tuple[Any, Any, Any, Any, Any, Any]],
    fecha_ref: date,
) -> Dict[str, int]:
    """
    APROBADO: N° cuota = cantidad de cuotas en MORA.
    Solo meses con 4 o más; el número puede subir el mes siguiente.
    """
    out: Dict[str, int] = {}
    for clave in _CLAVES_MES:
        y, m = int(clave[:4]), int(clave[5:7])
        as_of = min(fecha_ref, _ultimo_dia(y, m))
        n = conteo_cuotas_en_mora(items, as_of)
        if n >= MIN_CUOTAS_MORA_APROBADO:
            out[clave] = n
    return out


def fechas_cuota_impaga_en_mes(
    items: Sequence[Tuple[Any, Any, Any, Any, Any, Any]],
    fecha_ref: date,
) -> Dict[str, date]:
    """
    F. venc. por mes: fecha de la cuota impaga (VENCIDO/MORA) que vence
    en ese mes calendario. Enero incluye arrastre (vencimiento <= fin enero).
    Misma ventana que cargos_por_mes_amortizacion.
    """
    primer = _CLAVES_MES[0]
    out: Dict[str, date] = {}
    for clave in _CLAVES_MES:
        y, m = int(clave[:4]), int(clave[5:7])
        ini = date(y, m, 1)
        fin = _ultimo_dia(y, m)
        as_of = min(fecha_ref, fin)
        mx_nro: Optional[int] = None
        mx_fv: Optional[date] = None
        for nro, fv, monto, pagado, fp, _tot in items:
            fv_d = _as_date(fv)
            if fv_d is None:
                continue
            if clave == primer:
                if fv_d > fin:
                    continue
            elif fv_d < ini or fv_d > fin:
                continue
            if _pendiente_item_al(fv, monto, pagado, fp, as_of) is None:
                continue
            n = int(nro or 0)
            if n and (mx_nro is None or n > mx_nro):
                mx_nro = n
                mx_fv = fv_d
        if mx_fv is not None:
            out[clave] = mx_fv
    return out


def nros_ultima_cuota_vencida(
    items: Sequence[Tuple[Any, Any, Any, Any, Any, Any]],
    fecha_ref: date,
) -> Dict[str, int]:
    """
    Última cuota vencida impaga (máximo numero_cuota) hasta cada mes.

    Si la totalidad del plan ya está vencida e impaga antes de diciembre
    (p. ej. 12 de 12), se pone ese número en todos los meses.
    items: (numero_cuota, fv, monto, pagado, fecha_pago, total_cuotas)
    """
    def max_nro_al(as_of: date) -> Optional[int]:
        mx: Optional[int] = None
        for nro, fv, monto, pagado, fp, _tot in items:
            if _pendiente_item_al(fv, monto, pagado, fp, as_of) is None:
                continue
            n = int(nro or 0)
            if n and (mx is None or n > mx):
                mx = n
        return mx

    tot = 0
    ultima_fv: Optional[date] = None
    for nro, fv, _m, _p, _fp, t in items:
        if t:
            tot = max(tot, int(t))
        fv_d = _as_date(fv)
        if tot and int(nro or 0) == tot and fv_d is not None:
            ultima_fv = fv_d
    max_hoy = max_nro_al(fecha_ref)
    if (
        max_hoy
        and tot
        and max_hoy >= tot
        and (ultima_fv is None or ultima_fv < date(_ANIO_VENCIDOS, 12, 1))
    ):
        return {clave: max_hoy for clave in _CLAVES_MES}

    out: Dict[str, int] = {}
    for clave in _CLAVES_MES:
        y, m = int(clave[:4]), int(clave[5:7])
        as_of = min(fecha_ref, _ultimo_dia(y, m))
        n = max_nro_al(as_of)
        if n is not None:
            out[clave] = n
    return out


def _pagos_informe_hasta(
    pagos_por_mes: Dict[str, Decimal], clave_hasta: str
) -> Decimal:
    """Suma solo pagos de ene–ago 2026 hasta el mes analizado. Sin pagos del mes = 0."""
    total = Decimal("0")
    for clave in _CLAVES_MES:
        if clave > clave_hasta:
            break
        v = pagos_por_mes.get(clave)
        if v is not None:
            total += v
    return total.quantize(Decimal("0.01"))


def _saldo_mes(
    vencido: Optional[float], pagos_informe: Decimal
) -> Optional[float]:
    """Saldo = vencido − pagos del informe hasta ese mes. Si no pagó, saldo = vencido."""
    if vencido is None:
        return None
    v = Decimal(str(vencido))
    p = pagos_informe or Decimal("0")
    return float((v - p).quantize(Decimal("0.01")))


def _clave_mes(fv: date) -> Optional[str]:
    if fv.year != _ANIO_VENCIDOS or not (_MES_DESDE <= fv.month <= _MES_HASTA):
        return None
    return f"{fv.year}-{fv.month:02d}"


def clave_mes_con_arrastre(fv: date) -> Optional[str]:
    """
    Vencidos anteriores a enero 2026 se cargan en enero (arrastre).
    Enero–agosto 2026 van a su mes. Posterior a agosto: no entra en este informe.
    """
    if fv < date(_ANIO_VENCIDOS, _MES_DESDE, 1):
        return f"{_ANIO_VENCIDOS}-{_MES_DESDE:02d}"
    return _clave_mes(fv)


def pendiente_vencido(
    monto: Any,
    total_pagado: Any,
    fecha_vencimiento: Optional[date],
    fecha_pago: Optional[date] = None,
    fecha_ref: Optional[date] = None,
) -> Optional[Decimal]:
    """Saldo pendiente solo si el estado real es VENCIDO o MORA. None si no aplica."""
    from app.services.cuota_estado import clasificar_estado_cuota, hoy_negocio

    m = _a_decimal(monto)
    if m is None or fecha_vencimiento is None:
        return None
    pagado = _a_decimal(total_pagado) or Decimal("0")
    if fecha_pago is not None and pagado < Decimal("0.01"):
        pagado = m
    ref = fecha_ref or hoy_negocio()
    est = clasificar_estado_cuota(float(pagado), float(m), fecha_vencimiento, ref)
    if est not in ("VENCIDO", "MORA"):
        return None
    saldo = (m - pagado).quantize(Decimal("0.01"))
    if saldo <= Decimal("0.00"):
        return None
    return saldo


def parsear_cedulas_csv(raw: bytes) -> List[str]:
    if (
        not raw
        or raw.lstrip()[:15].lower().startswith(b"<!doctype")
        or b"<html" in raw[:400].lower()
    ):
        raise RuntimeError(
            "La hoja Drive no devolvio CSV (inicie sesion o publique la hoja)."
        )
    text = raw.decode("utf-8-sig", errors="replace")
    rows = list(csv.reader(io.StringIO(text)))
    if not rows:
        return []
    out: List[str] = []
    for i, row in enumerate(rows):
        if not row:
            continue
        cell = str(row[0] or "").strip()
        if not cell:
            continue
        if i == 0 and not any(ch.isdigit() for ch in cell):
            continue
        out.append(cell)
    return out


def leer_cedulas_hoja(spreadsheet_id: Optional[str] = None) -> List[str]:
    sid = (spreadsheet_id or _sheet_id()).strip()
    if not sid:
        raise RuntimeError("REPORTE_CUOTAS_JUN_AGO_SHEET_ID no configurado.")
    url = _SHEET_EXPORT.format(sid=sid)
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "pagos-reportes-cedulas-cuota/1.0"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
    except urllib.error.URLError as e:
        raise RuntimeError(f"No se pudo leer la hoja Drive: {e}") from e
    return parsear_cedulas_csv(raw)


def _cuotas_bd_por_cedula_norm(
    db: Session, cedulas_norm: Iterable[str]
) -> Dict[str, List[Tuple[str, Any]]]:
    claves = _expandir_claves_sql(cedulas_norm)
    if not claves:
        return {}
    ced_expr = expr_cedula_normalizada_para_comparar(Prestamo.cedula)
    estado_u = func.upper(func.trim(Prestamo.estado))
    rows = db.execute(
        select(ced_expr, Prestamo.estado, Prestamo.cuota_periodo).where(
            ced_expr.in_(claves),
            estado_u.notin_(_ESTADOS_EXCLUIDOS),
        )
    ).all()
    out: Dict[str, List[Tuple[str, Any]]] = {}
    for ced, est, cuota in rows:
        k = texto_cedula_comparable_bd(ced or "")
        if not k:
            continue
        out.setdefault(k, []).append((str(est or ""), cuota))
    return out


def _vencidos_por_cedula_mes(
    db: Session,
    cedulas_norm: Iterable[str],
    fecha_ref: Optional[date] = None,
) -> Tuple[
    Dict[str, Dict[str, Decimal]],
    Dict[str, Dict[str, int]],
    Dict[str, Dict[str, date]],
]:
    """Montos vencidos, N° cuota y F. venc. por mes."""
    from app.models.cuota import Cuota
    from app.services.cuota_estado import hoy_negocio

    claves = _expandir_claves_sql(cedulas_norm)
    if not claves:
        return {}, {}, {}
    ref = fecha_ref or hoy_negocio()
    fin = date(_ANIO_VENCIDOS, _MES_HASTA, 31)
    ced_expr = expr_cedula_normalizada_para_comparar(Prestamo.cedula)
    estado_u = func.upper(func.trim(Prestamo.estado))
    rows = db.execute(
        select(
            ced_expr,
            Cuota.fecha_vencimiento,
            Cuota.monto,
            Cuota.total_pagado,
            Cuota.fecha_pago,
            Cuota.numero_cuota,
            Prestamo.numero_cuotas,
            Prestamo.estado,
        )
        .select_from(Cuota)
        .join(Prestamo, Cuota.prestamo_id == Prestamo.id)
        .where(
            ced_expr.in_(claves),
            estado_u.notin_(_ESTADOS_EXCLUIDOS),
            Cuota.fecha_vencimiento <= fin,
        )
    ).all()
    items_nro: Dict[str, List[Tuple[Any, Any, Any, Any, Any, Any]]] = {}
    estados_por_k: Dict[str, set] = {}
    for ced, fv, monto, pagado, f_pago, nro, tot, est in rows:
        k = texto_cedula_comparable_bd(ced or "")
        if not k or fv is None:
            continue
        fv_d = fv.date() if hasattr(fv, "date") else fv
        items_nro.setdefault(k, []).append((nro, fv_d, monto, pagado, f_pago, tot))
        e = str(est or "").strip().upper()
        if e:
            estados_por_k.setdefault(k, set()).add(e)
    out = {
        k: cargos_por_mes_amortizacion(items, ref) for k, items in items_nro.items()
    }
    nros: Dict[str, Dict[str, int]] = {}
    fechas: Dict[str, Dict[str, date]] = {}
    for k, items in items_nro.items():
        if "APROBADO" in estados_por_k.get(k, set()):
            nros[k] = nros_cuotas_en_mora(items, ref)
        else:
            nros[k] = nros_ultima_cuota_vencida(items, ref)
        fechas[k] = fechas_cuota_impaga_en_mes(items, ref)
    return out, nros, fechas


def _pagos_bd_por_cedula_mes(
    db: Session,
    cedulas_norm: Iterable[str],
) -> Dict[str, Dict[str, Decimal]]:
    """ced_norm -> { '2026-01': Decimal } suma de pagos.monto_pagado en ese mes calendario."""
    from app.models.pago import Pago

    claves = _expandir_claves_sql(cedulas_norm)
    if not claves:
        return {}
    fin_excl = date(_ANIO_VENCIDOS, _MES_HASTA + 1, 1)
    ced_prestamo = expr_cedula_normalizada_para_comparar(Prestamo.cedula)
    ced_pago = expr_cedula_normalizada_para_comparar(Pago.cedula_cliente)
    estado_pago = func.upper(func.trim(func.coalesce(Pago.estado, "")))
    estado_prestamo = func.upper(func.trim(Prestamo.estado))
    pago_ok = and_(
        ~estado_pago.like("ANULADO%"),
        estado_pago.is_distinct_from("DUPLICADO"),
    )
    prestamo_ok = or_(
        Prestamo.id.is_(None),
        estado_prestamo.notin_(_ESTADOS_EXCLUIDOS),
    )
    rows = db.execute(
        select(
            Pago.id,
            ced_prestamo,
            ced_pago,
            Pago.fecha_pago,
            Pago.monto_pagado,
        )
        .select_from(Pago)
        .outerjoin(Prestamo, Pago.prestamo_id == Prestamo.id)
        .where(
            pago_ok,
            prestamo_ok,
            Pago.fecha_pago.isnot(None),
            Pago.fecha_pago < fin_excl,
            or_(ced_prestamo.in_(claves), ced_pago.in_(claves)),
        )
    ).all()
    vistos: set[int] = set()
    out: Dict[str, Dict[str, Decimal]] = {}
    for pid, ced_pr, ced_pg, fp, monto in rows:
        if pid in vistos:
            continue
        vistos.add(int(pid))
        k = texto_cedula_comparable_bd(ced_pr or "") or texto_cedula_comparable_bd(
            ced_pg or ""
        )
        if not k or fp is None:
            continue
        fp_d = fp.date() if hasattr(fp, "date") else fp
        clave = f"{fp_d.year}-{fp_d.month:02d}"
        if clave > _CLAVES_MES[-1]:
            continue
        val = _a_decimal(monto)
        if val is None or val <= Decimal("0.00"):
            continue
        bucket = out.setdefault(k, {})
        bucket[clave] = (bucket.get(clave, Decimal("0")) + val).quantize(
            Decimal("0.01")
        )
    return out


def cargos_por_mes_amortizacion(
    items: Sequence[Tuple[Any, Any, Any, Any, Any, Any]],
    fecha_ref: date,
) -> Dict[str, Decimal]:
    """
    Cargo del mes: enero = todo lo vencido impago hasta enero (inicio del préstamo);
    meses siguientes = solo cuotas que vencen ese mes y siguen impagas a fin de mes.
    """
    primer = _CLAVES_MES[0]
    out: Dict[str, Decimal] = {}
    for clave in _CLAVES_MES:
        y, m = int(clave[:4]), int(clave[5:7])
        ini = date(y, m, 1)
        fin = _ultimo_dia(y, m)
        as_of = min(fecha_ref, fin)
        total = Decimal("0")
        hubo = False
        for _nro, fv, monto, pagado, fp, _tot in items:
            fv_d = fv.date() if hasattr(fv, "date") else fv
            if fv_d is None:
                continue
            if clave == primer:
                if fv_d > fin:
                    continue
            elif fv_d < ini or fv_d > fin:
                continue
            fp_d = fp.date() if fp is not None and hasattr(fp, "date") else fp
            if fp_d is not None and fp_d > as_of:
                pag_eff, fp_eff = Decimal("0"), None
            else:
                pag_eff, fp_eff = pagado, fp_d
            sal = pendiente_vencido(monto, pag_eff, fv_d, fp_eff, as_of)
            if sal is None:
                continue
            total += sal
            hubo = True
        if hubo:
            out[clave] = total.quantize(Decimal("0.01"))
    return out


def _pagos_en_meses_reportados(
    pagos: Dict[str, Decimal],
    *,
    es_aprobado: bool,
    nros: Dict[str, int],
) -> Dict[str, Decimal]:
    """
    Pagos solo en meses que se reportan. APROBADO: abonos de meses sin 4+ MORA
    se suman al primer mes reportado (no se pierden). LIQUIDADO/DESISTIMIENTO: igual.
    """
    if not es_aprobado:
        return dict(pagos)
    primer = next(
        (
            c
            for c in _CLAVES_MES
            if nros.get(c) is not None
            and int(nros[c]) >= MIN_CUOTAS_MORA_APROBADO
        ),
        None,
    )
    if primer is None:
        return {}
    out: Dict[str, Decimal] = {}
    arrastre = Decimal("0")
    for clave in _CLAVES_MES:
        v = pagos.get(clave) or Decimal("0")
        reporta = (
            nros.get(clave) is not None
            and int(nros[clave]) >= MIN_CUOTAS_MORA_APROBADO
        )
        if not reporta:
            arrastre += v
            continue
        total = v
        if clave == primer:
            total += arrastre
            arrastre = Decimal("0")
        if total > Decimal("0.00"):
            out[clave] = total.quantize(Decimal("0.01"))
    return out


def amortizar_tabla(
    cargos: Dict[str, Decimal],
    pagos: Dict[str, Decimal],
) -> Tuple[Dict[str, Decimal], Dict[str, Decimal]]:
    """
    Vencido del mes = saldo anterior + cargo del mes.
    Saldo = vencido − pagos del mes. Sin pagos, saldo = vencido y se traslada.
    """
    saldo_prev = Decimal("0")
    activo = False
    vencidos: Dict[str, Decimal] = {}
    saldos: Dict[str, Decimal] = {}
    for clave in _CLAVES_MES:
        cargo = cargos.get(clave)
        pag = pagos.get(clave)
        if cargo is None and pag is None and not activo:
            continue
        activo = True
        cargo_n = cargo or Decimal("0")
        if cargo_n < Decimal("0.00"):
            cargo_n = Decimal("0.00")
        vencido = (saldo_prev + cargo_n).quantize(Decimal("0.01"))
        if vencido < Decimal("0.00"):
            vencido = Decimal("0.00")
        saldo = (vencido - (pag or Decimal("0"))).quantize(Decimal("0.01"))
        if saldo < Decimal("0.00"):
            saldo = Decimal("0.00")
        vencidos[clave] = vencido
        saldos[clave] = saldo
        saldo_prev = saldo
    return vencidos, saldos


def acumular_vencidos_hasta_mes(
    por_mes: Dict[str, Decimal],
) -> Dict[str, Decimal]:
    """
    Acumulado de cuotas vencidas pendientes: cada mes = suma de ese mes y los anteriores.
    Solo aparecen meses desde el primer vencido; no se rellena 0.
    """
    acc = Decimal("0")
    hubo = False
    out: Dict[str, Decimal] = {}
    for clave in _CLAVES_MES:
        extra = por_mes.get(clave)
        if extra is not None:
            acc = (acc + extra).quantize(Decimal("0.01"))
            hubo = True
        if hubo and acc > Decimal("0.00"):
            out[clave] = acc
    return out


def filas_cedula_cuota(
    cedulas_hoja: Sequence[str],
    prestamos_por_norm: Dict[str, List[Tuple[str, Any]]],
    vencidos_por_norm: Optional[Dict[str, Dict[str, Decimal]]] = None,
    pagos_por_norm: Optional[Dict[str, Dict[str, Decimal]]] = None,
    nros_por_norm: Optional[Dict[str, Dict[str, int]]] = None,
    fechas_por_norm: Optional[Dict[str, Dict[str, date]]] = None,
) -> List[Dict[str, Any]]:
    vencidos_por_norm = vencidos_por_norm or {}
    pagos_por_norm = pagos_por_norm or {}
    nros_por_norm = nros_por_norm or {}
    fechas_por_norm = fechas_por_norm or {}
    filas: List[Dict[str, Any]] = []
    for raw in cedulas_hoja:
        prests = _prestamos_para_cedula_hoja(raw, prestamos_por_norm)
        estado = estado_actual_de_prestamos(prests)
        es_aprobado = estado == "APROBADO"
        nros = _nros_para_cedula_hoja(raw, nros_por_norm)
        fechas = _fechas_para_cedula_hoja(raw, fechas_por_norm)
        cuota = cuota_unica_de_prestamos(prests)
        cargos = _vencidos_para_cedula_hoja(raw, vencidos_por_norm)
        pagos_raw = _vencidos_para_cedula_hoja(raw, pagos_por_norm)
        pagos = _pagos_en_meses_reportados(
            pagos_raw, es_aprobado=es_aprobado, nros=nros
        )
        vencidos_am, saldos_am = amortizar_tabla(cargos, pagos)
        fila: Dict[str, Any] = {
            "cedula": raw,
            "estado": estado,
            "cuota": float(cuota) if cuota is not None else None,
        }
        for clave in _CLAVES_MES:
            nro = nros.get(clave)
            fv = fechas.get(clave)
            mostrar_mora = (not es_aprobado) or (
                nro is not None and int(nro) >= MIN_CUOTAS_MORA_APROBADO
            )
            fila[_clave_fv(clave)] = fv
            if not mostrar_mora:
                fila[clave] = None
                fila[_clave_nro(clave)] = None
                fila[_clave_pagos(clave)] = None
                fila[_clave_saldo(clave)] = None
                continue
            ven = vencidos_am.get(clave)
            pag = pagos.get(clave)
            sal = saldos_am.get(clave)
            fila[clave] = float(ven) if ven is not None else None
            fila[_clave_nro(clave)] = int(nro) if nro is not None else None
            fila[_clave_pagos(clave)] = float(pag) if pag is not None else None
            fila[_clave_saldo(clave)] = float(sal) if sal is not None else None
        filas.append(fila)
    return filas


_COLS_POR_MES = 5


def generar_excel_cedulas_cuota(filas: Sequence[Dict[str, Any]]) -> bytes:
    import openpyxl
    from openpyxl.styles import Alignment, Font, numbers
    from openpyxl.utils import get_column_letter

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Cedula cuota"
    bold = Font(bold=True)
    centro = Alignment(horizontal="center")
    ws.cell(1, 1, "Cédula").font = bold
    ws.cell(1, 2, "Estado").font = bold
    ws.cell(1, 3, "Cuota").font = bold
    ws.merge_cells(start_row=1, start_column=1, end_row=2, end_column=1)
    ws.merge_cells(start_row=1, start_column=2, end_row=2, end_column=2)
    ws.merge_cells(start_row=1, start_column=3, end_row=2, end_column=3)
    for i, (_a, _m, nombre) in enumerate(MESES_VENCIDOS):
        c1 = 4 + i * _COLS_POR_MES
        ws.merge_cells(
            start_row=1, start_column=c1, end_row=1, end_column=c1 + _COLS_POR_MES - 1
        )
        cell_m = ws.cell(1, c1, nombre)
        cell_m.font = bold
        cell_m.alignment = centro
        ws.cell(2, c1, "N° cuota").font = bold
        ws.cell(2, c1 + 1, "Vencido").font = bold
        ws.cell(2, c1 + 2, "Pagos").font = bold
        ws.cell(2, c1 + 3, "Saldo").font = bold
        ws.cell(2, c1 + 4, "F. venc.").font = bold
    for f in filas:
        cuota = f.get("cuota")
        row: List[Any] = [
            f.get("cedula") or "",
            f.get("estado") or None,
            cuota if cuota is not None else None,
        ]
        for clave in _CLAVES_MES:
            row.append(
                f.get(_clave_nro(clave))
                if f.get(_clave_nro(clave)) is not None
                else None
            )
            row.append(f.get(clave) if f.get(clave) is not None else None)
            row.append(
                f.get(_clave_pagos(clave))
                if f.get(_clave_pagos(clave)) is not None
                else None
            )
            row.append(
                f.get(_clave_saldo(clave))
                if f.get(_clave_saldo(clave)) is not None
                else None
            )
            fv_val = f.get(_clave_fv(clave))
            row.append(fv_val if fv_val is not None else None)
        ws.append(row)
        r = ws.max_row
        nro_cols = {4 + i * _COLS_POR_MES for i in range(len(_CLAVES_MES))}
        fv_cols = {4 + i * _COLS_POR_MES + 4 for i in range(len(_CLAVES_MES))}
        for col in range(3, 3 + 1 + len(_CLAVES_MES) * _COLS_POR_MES):
            cell = ws.cell(r, col)
            if col in nro_cols:
                continue
            if col in fv_cols:
                if cell.value is not None:
                    cell.number_format = "YYYY-MM-DD"
                cell.alignment = Alignment(horizontal="center")
                continue
            if cell.value is not None:
                cell.number_format = numbers.FORMAT_NUMBER_COMMA_SEPARATED2
            cell.alignment = Alignment(horizontal="right")
    ws.column_dimensions["A"].width = 18
    ws.column_dimensions["B"].width = 18
    last_col = 3 + len(_CLAVES_MES) * _COLS_POR_MES
    for col in range(3, last_col + 1):
        ws.column_dimensions[get_column_letter(col)].width = 14
    ws.freeze_panes = "A3"
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def construir_excel_cedulas_cuota_hoja(
    db: Session,
    *,
    spreadsheet_id: Optional[str] = None,
    cedulas: Optional[Sequence[str]] = None,
) -> Tuple[bytes, int, int]:
    """
    Devuelve (xlsx, filas, filas_con_cuota).
    `cedulas` solo para tests; en runtime se leen de la hoja.
    """
    lista = list(cedulas) if cedulas is not None else leer_cedulas_hoja(spreadsheet_id)
    if not lista:
        raise RuntimeError("La hoja no tiene cédulas.")
    normas = [texto_cedula_comparable_bd(c) for c in lista]
    mapa = _cuotas_bd_por_cedula_norm(db, normas)
    vencidos, nros, fechas = _vencidos_por_cedula_mes(db, normas)
    pagos = _pagos_bd_por_cedula_mes(db, normas)
    filas = filas_cedula_cuota(lista, mapa, vencidos, pagos, nros, fechas)
    con_cuota = sum(1 for f in filas if f.get("cuota") is not None)
    logger.info(
        "[reporte_cedulas_cuota_hoja] filas=%s con_cuota=%s sin_cuota=%s",
        len(filas),
        con_cuota,
        len(filas) - con_cuota,
    )
    return generar_excel_cedulas_cuota(filas), len(filas), con_cuota
