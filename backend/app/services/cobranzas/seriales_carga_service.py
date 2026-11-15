"""
Cobranzas → Seriales (solo itmaster@): carga de pagos Mercantil desde Excel de depósitos
a préstamos con cuotas atrasadas de una lista de cédulas.

Reglas de negocio:
- Un préstamo por cédula: el APROBADO cuya cuota atrasada pendiente es la más antigua.
- Cuotas atrasadas (vencidas con saldo) de la más antigua a la más nueva.
- Se llena la primera cuota atrasada con saldo tomando el primer depósito de la cola
  (orden Excel, no usado) con fecha en [vencimiento - 10 días, vencimiento + 60 días]
  de esa cuota y serial no registrado en BD. El monto no tiene que coincidir:
  menor → cuota parcial y se sigue buscando para la misma cuota; mayor → la cascada
  pasa el sobrante a las cuotas siguientes (cuentan como cubiertas).
- Una cuota puede llenarse con varios depósitos. Un depósito usado no se vuelve a usar.
- Se cargan depósitos solo hasta cubrir las cuotas atrasadas al inicio; el último
  depósito se carga completo aunque exceda (cascada normal).
- Si la cuota en curso no encuentra depósito en su ventana, queda parcial y se detiene
  ese préstamo.
- Pago: banco Mercantil, USD, comprobante imagen en blanco; luego cascada normal.
"""
from __future__ import annotations

import logging
import re
from datetime import date, datetime, time as dt_time, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Optional
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.constants.prestamo_estados import (
    ESTADOS_PRESTAMO_EXCLUIDOS_COBRANZA_NOTIF,
    prestamo_estado_es_desistimiento,
)
from app.core.documento import compose_numero_documento_almacenado, normalize_documento
from app.models.cliente import Cliente
from app.models.cuota import Cuota
from app.models.pago import Pago
from app.models.prestamo import Prestamo
from app.services.cuota_estado import TZ_NEGOCIO, hoy_negocio
from app.services.cobranzas.universo_analisis_service import (
    invalidate_universo_analisis_cache,
)
from app.services.pago_autoconciliacion import marcar_pago_autoconciliado
from app.services.pago_numero_documento import numero_documento_ya_registrado
from app.utils.cedula_almacenamiento import resolver_cedula_almacenada_en_clientes

logger = logging.getLogger(__name__)

BANCO = "Mercantil"
USUARIO_REGISTRO = "cobranzas-seriales@sistema.rapicredit.com"
MAX_PRESTAMOS_LOTE = 20
MAX_DEPOSITOS = 20000
DIAS_ANTES_VENCIMIENTO = 10
DIAS_DESPUES_VENCIMIENTO = 60
MAX_PAGOS_POR_PRESTAMO = 200
_CENT = Decimal("0.01")


def _monto_dec(val: Any) -> Optional[Decimal]:
    from app.services.importacion_extracto_service import _parse_monto

    m = _parse_monto(val)
    if m is None:
        return None
    return Decimal(str(m)).quantize(_CENT, rounding=ROUND_HALF_UP)


def _fecha(val: Any) -> Optional[date]:
    from app.services.importacion_extracto_service import _parse_fecha

    if isinstance(val, str) and re.fullmatch(r"\d{5}(\.\d+)?", val.strip()):
        return _parse_fecha(float(val.strip()))
    return _parse_fecha(val)


def _cedula_canon(val: Any) -> str:
    from app.services.importacion_extracto_service import _cedula_canon_match

    return _cedula_canon_match(str(val or ""))


def _serial_norm(val: Any) -> str:
    if val is None:
        return ""
    if isinstance(val, float) and val == int(val):
        val = int(val)
    s = str(val).strip()
    if s.endswith(".0") and s[:-2].isdigit():
        s = s[:-2]
    return normalize_documento(s, institucion=BANCO) or ""


def _variantes_cedula(canon: str) -> list[str]:
    if not canon:
        return []
    out = {canon}
    if len(canon) >= 2 and canon[0] in "VEJG":
        dig = canon[1:]
        out |= {f"{canon[0]}-{dig}", dig, f"{canon[0]}{dig.zfill(8)}", f"{canon[0]}-{dig.zfill(8)}"}
    return sorted(out)


def _cuotas_atrasadas(db: Session, prestamo_id: int, hoy: date) -> list[Cuota]:
    return list(
        db.execute(
            select(Cuota)
            .where(
                Cuota.prestamo_id == int(prestamo_id),
                Cuota.fecha_vencimiento < hoy,
                or_(Cuota.total_pagado.is_(None), Cuota.total_pagado < Cuota.monto - 0.01),
            )
            .order_by(Cuota.fecha_vencimiento.asc(), Cuota.numero_cuota.asc())
        )
        .scalars()
        .all()
    )


def _prestamo_mas_atrasado(
    db: Session, cedula: str, hoy: date
) -> tuple[Optional[Prestamo], list[Cuota]]:
    """APROBADO de la cédula cuya cuota atrasada pendiente es la más antigua."""
    variantes = _variantes_cedula(cedula)
    if not variantes:
        return None, []
    ids: set[int] = set()
    for (pid,) in db.execute(select(Prestamo.id).where(Prestamo.cedula.in_(variantes))).all():
        ids.add(int(pid))
    cli_ids = [
        int(c)
        for (c,) in db.execute(select(Cliente.id).where(Cliente.cedula.in_(variantes))).all()
    ]
    if cli_ids:
        for (pid,) in db.execute(
            select(Prestamo.id).where(Prestamo.cliente_id.in_(cli_ids))
        ).all():
            ids.add(int(pid))

    mejor: Optional[Prestamo] = None
    mejor_cuotas: list[Cuota] = []
    mejor_fecha: Optional[date] = None
    for pid in sorted(ids):
        p = db.get(Prestamo, pid)
        if p is None:
            continue
        est = str(p.estado or "").upper()
        if (
            est != "APROBADO"
            or est in ESTADOS_PRESTAMO_EXCLUIDOS_COBRANZA_NOTIF
            or prestamo_estado_es_desistimiento(est)
        ):
            continue
        cuotas = _cuotas_atrasadas(db, pid, hoy)
        if not cuotas:
            continue
        f0 = cuotas[0].fecha_vencimiento
        if hasattr(f0, "date") and not isinstance(f0, date):
            f0 = f0.date()
        if mejor_fecha is None or f0 < mejor_fecha:
            mejor, mejor_cuotas, mejor_fecha = p, cuotas, f0
    return mejor, mejor_cuotas


def _saldo_cuota(db: Session, cuota: Cuota) -> Decimal:
    """Saldo vigente (tras commits/cascada se recarga desde BD)."""
    refresh = getattr(db, "refresh", None)
    if callable(refresh):
        try:
            refresh(cuota)
        except Exception:
            logger.debug("[cobranzas-seriales] refresh cuota_id=%s", getattr(cuota, "id", None))
    monto = Decimal(str(cuota.monto or 0))
    pagado = Decimal(str(cuota.total_pagado or 0))
    return max(Decimal("0"), monto - pagado).quantize(_CENT, rounding=ROUND_HALF_UP)


def _deposito_valido(dep: dict[str, Any]) -> bool:
    return bool(dep.get("serial_norm")) and dep.get("monto") is not None and dep.get("fecha") is not None


def normalizar_depositos(depositos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normaliza filas del Excel de depósitos (id = índice en la cola original)."""
    out: list[dict[str, Any]] = []
    for d in depositos:
        out.append(
            {
                "id": int(d.get("id")),
                "fecha": _fecha(d.get("fecha")),
                "serial_raw": str(d.get("serial") or "").strip(),
                "serial_norm": _serial_norm(d.get("serial")),
                "monto": _monto_dec(d.get("monto")),
            }
        )
    return out


def _crear_pago_mercantil(
    db: Session,
    *,
    prestamo: Prestamo,
    cedula: str,
    dep: dict[str, Any],
    numero_doc: str,
) -> tuple[Optional[Pago], str]:
    from app.services.importacion_extracto_service import (
        _aplicar_cascada_importacion_extracto,
        _guardar_placeholder_imagen,
    )
    from app.services.pagos_gmail.comprobante_bd import url_comprobante_imagen_absoluta

    img_id = _guardar_placeholder_imagen(db)
    link = url_comprobante_imagen_absoluta(img_id)
    ahora = datetime.now(ZoneInfo(TZ_NEGOCIO))
    cedula_pago = resolver_cedula_almacenada_en_clientes(db, cedula) or prestamo.cedula or cedula
    pago = Pago(
        prestamo_id=int(prestamo.id),
        cedula_cliente=cedula_pago,
        fecha_pago=datetime.combine(dep["fecha"], dt_time(12, 0, 0)),
        monto_pagado=dep["monto"],
        numero_documento=numero_doc[:100],
        referencia_pago=dep["serial_norm"][:100],
        institucion_bancaria=BANCO,
        estado="PAGADO",
        conciliado=True,
        verificado_concordancia="SI",
        fecha_conciliacion=ahora,
        usuario_registro=USUARIO_REGISTRO,
        notas=f"[COBRANZAS_SERIALES] placeholder imagen; banco={BANCO}; cedula={cedula}",
        documento_nombre="placeholder-seriales.png",
        documento_tipo="image/png",
        documento_ruta=link,
        link_comprobante=link,
        moneda_registro="USD",
    )
    db.add(pago)
    db.flush()
    marcar_pago_autoconciliado(pago, ahora)
    ok, det, _cc, _cp = _aplicar_cascada_importacion_extracto(db, pago, int(prestamo.id))
    if not ok:
        db.delete(pago)
        db.flush()
        return None, det
    return pago, det


def procesar_lote_seriales(
    db: Session,
    *,
    cedulas: list[str],
    depositos: list[dict[str, Any]],
    usados: Optional[list[int]] = None,
) -> dict[str, Any]:
    """
    Procesa hasta 20 cédulas contra la cola de depósitos.

    ``depositos``: lista completa {id, fecha, serial, monto} en orden del Excel.
    ``usados``: ids ya consumidos en lotes anteriores (no se vuelven a usar).
    """
    if len(cedulas) > MAX_PRESTAMOS_LOTE:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail=f"Máximo {MAX_PRESTAMOS_LOTE} cédulas por lote.")
    if len(depositos) > MAX_DEPOSITOS:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail=f"Máximo {MAX_DEPOSITOS} depósitos.")

    hoy = hoy_negocio()
    cola = normalizar_depositos(depositos)
    usados_set: set[int] = {int(x) for x in (usados or [])}
    seriales_usados_lote: set[str] = set()
    descartados_bd: set[int] = set()

    resultados: list[dict[str, Any]] = []
    nuevos_usados: list[int] = []

    for raw_ced in cedulas:
        cedula = _cedula_canon(raw_ced)
        fila: dict[str, Any] = {
            "cedula": str(raw_ced or "").strip(),
            "cedula_norm": cedula or None,
            "prestamo_id": None,
            "cuotas_atrasadas": 0,
            "cuotas_cubiertas": 0,
            "pagos": [],
            "estado": "",
            "detalle": "",
        }
        if not cedula:
            fila.update(estado="CEDULA_INVALIDA", detalle="Cédula vacía o inválida")
            resultados.append(fila)
            continue

        prestamo, cuotas = _prestamo_mas_atrasado(db, cedula, hoy)
        if prestamo is None:
            fila.update(estado="SIN_ATRASO", detalle="Sin préstamo APROBADO con cuotas atrasadas")
            resultados.append(fila)
            continue

        fila["prestamo_id"] = int(prestamo.id)
        fila["cuotas_atrasadas"] = len(cuotas)
        parada = ""

        while len(fila["pagos"]) < MAX_PAGOS_POR_PRESTAMO:
            cuota = next((c for c in cuotas if _saldo_cuota(db, c) > _CENT), None)
            if cuota is None:
                break
            venc = cuota.fecha_vencimiento
            if hasattr(venc, "date") and not isinstance(venc, date):
                venc = venc.date()
            saldo = _saldo_cuota(db, cuota)
            desde = venc - timedelta(days=DIAS_ANTES_VENCIMIENTO)
            hasta = venc + timedelta(days=DIAS_DESPUES_VENCIMIENTO)

            elegido: Optional[dict[str, Any]] = None
            numero_doc = ""
            for dep in cola:
                did = dep["id"]
                if did in usados_set or did in descartados_bd or not _deposito_valido(dep):
                    continue
                if dep["monto"] <= 0:
                    continue
                if not (desde <= dep["fecha"] <= hasta):
                    continue
                if dep["serial_norm"] in seriales_usados_lote:
                    continue
                nd = compose_numero_documento_almacenado(dep["serial_norm"], None, institucion=BANCO)
                if not nd:
                    continue
                if numero_documento_ya_registrado(db, nd):
                    descartados_bd.add(did)
                    continue
                elegido, numero_doc = dep, nd
                break

            if elegido is None:
                parada = (
                    f"Cuota #{cuota.numero_cuota} ({venc.isoformat()}) queda con saldo ${saldo}: "
                    "sin depósito en su ventana; se detiene este préstamo"
                )
                break

            try:
                pago, det = _crear_pago_mercantil(
                    db, prestamo=prestamo, cedula=cedula, dep=elegido, numero_doc=numero_doc
                )
            except Exception as exc:
                logger.exception("[cobranzas-seriales] pago prestamo_id=%s", prestamo.id)
                db.rollback()
                parada = f"Error al crear pago: {str(exc)[:200]}"
                break
            if pago is None:
                db.rollback()
                parada = f"Cascada falló ({det}); se detiene este préstamo"
                break

            if not bool(getattr(prestamo, "requiere_revision", False)):
                prestamo.requiere_revision = True
            db.commit()

            usados_set.add(elegido["id"])
            nuevos_usados.append(elegido["id"])
            seriales_usados_lote.add(elegido["serial_norm"])
            fila["pagos"].append(
                {
                    "pago_id": int(pago.id),
                    "deposito_id": elegido["id"],
                    "cuota_numero": int(cuota.numero_cuota),
                    "cuota_vencimiento": venc.isoformat(),
                    "saldo_cuota_antes": float(saldo),
                    "fecha_deposito": elegido["fecha"].isoformat(),
                    "serial": elegido["serial_norm"],
                    "monto": float(elegido["monto"]),
                    "cascada": det,
                }
            )

        pendientes = sum(1 for c in cuotas if _saldo_cuota(db, c) > _CENT)
        fila["cuotas_cubiertas"] = len(cuotas) - pendientes
        n = len(fila["pagos"])
        if n == 0:
            fila["estado"] = "SIN_COINCIDENCIA"
        elif pendientes > 0:
            fila["estado"] = "PARCIAL"
        else:
            fila["estado"] = "COMPLETO"
        fila["detalle"] = parada or (
            f"{n} pago(s) cargado(s); {fila['cuotas_cubiertas']}/{len(cuotas)} cuotas atrasadas cubiertas"
        )
        resultados.append(fila)

    try:
        if nuevos_usados:
            invalidate_universo_analisis_cache()
    except Exception:
        logger.debug("[cobranzas-seriales] no se pudo invalidar caché universo", exc_info=True)

    return {
        "procesadas": len(resultados),
        "pagos_creados": len(nuevos_usados),
        "depositos_usados": nuevos_usados,
        "depositos_serial_en_bd": sorted(descartados_bd),
        "resultados": resultados,
    }
