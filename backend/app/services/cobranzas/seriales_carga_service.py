"""
Cobranzas → Seriales (solo itmaster@): carga de pagos Mercantil desde Excel de depósitos
a préstamos con cuotas atrasadas de una lista de cédulas.

Reglas de negocio:
- Un préstamo por cédula: el APROBADO cuya cuota atrasada pendiente es la más antigua.
- Cuotas atrasadas (vencidas con saldo) de la más antigua a la más nueva.
- Un solo depósito por mes calendario y por préstamo.
- Cada cuota busca desde el mes de su vencimiento (o el mes siguiente al último usado):
  entre los depósitos de ese mes (no usados) dentro de ±tolerancia del MONTO de la cuota
  toma el más cercano a lo que le falta (exacto primero); empate → fecha más antigua.
  Si el mes no tiene ninguno, sigue con el mes siguiente.
- Opciones: simulación sin escribir en BD; tolerancia configurable (por defecto ±20%);
  máximo de meses posteriores al vencimiento en que se busca (por defecto 2; 0 = sin límite).
- Se omiten seriales ya en pagos/pagos_con_errores, pagos reportados pendientes o en
  revisión, y pagos confirmados ACTIVO de Cobranzas.
- Lo que falta o sobra lo ajusta la cascada normal (p. ej. cuota 110 con depósito 100:
  los 10 pendientes los cubre el siguiente depósito por cascada).
- Termina cuando se acaban las cuotas atrasadas; si una cuota no encuentra depósito
  hasta el mes límite (o el último mes del archivo), se detiene ese préstamo.
- Pago: banco Mercantil, USD, comprobante imagen en blanco; luego cascada normal.
"""
from __future__ import annotations

import logging
import re
from datetime import date, datetime, time as dt_time
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
from app.utils.cedula_almacenamiento import CedulaPagoFkError, asegurar_cedula_pago_para_fk

logger = logging.getLogger(__name__)

BANCO = "Mercantil"
USUARIO_REGISTRO = "cobranzas-seriales@sistema.rapicredit.com"
MAX_PRESTAMOS_LOTE = 20
MAX_DEPOSITOS = 20000
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


def _mes(d: date) -> tuple[int, int]:
    return (d.year, d.month)


def _mes_siguiente(m: tuple[int, int]) -> tuple[int, int]:
    return (m[0] + 1, 1) if m[1] == 12 else (m[0], m[1] + 1)


def _mes_txt(m: tuple[int, int]) -> str:
    return f"{m[1]:02d}/{m[0]}"


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

    prestamo_id = int(prestamo.id)
    try:
        cedula_pago = asegurar_cedula_pago_para_fk(
            db,
            cedula_raw=(cedula or prestamo.cedula or "").strip() or None,
            prestamo_id=prestamo_id,
        )
    except CedulaPagoFkError as exc:
        return None, str(exc)
    if not cedula_pago:
        return None, f"Sin cédula válida en clientes para el préstamo {prestamo_id}"

    img_id = _guardar_placeholder_imagen(db)
    link = url_comprobante_imagen_absoluta(img_id)
    ahora = datetime.now(ZoneInfo(TZ_NEGOCIO))
    pago = Pago(
        prestamo_id=prestamo_id,
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


def _clave_digitos(val: Any) -> str:
    dig = re.sub(r"\D+", "", str(val or ""))
    return dig.lstrip("0") or dig


def _claves_en_otras_tablas(db: Session) -> set[str]:
    """
    Seriales que ya circulan por otra vía y no deben cargarse aquí:
    pagos reportados pendientes/en revisión y pagos confirmados ACTIVO (Cobranzas).
    """
    from app.models.importacion_extracto import ImportacionExtractoPagoConfirmado
    from app.models.pago_reportado import PagoReportado

    claves: set[str] = set()
    try:
        for (num,) in db.execute(
            select(PagoReportado.numero_operacion).where(
                PagoReportado.estado.in_(("pendiente", "en_revision"))
            )
        ).all():
            k = _clave_digitos(num)
            if k:
                claves.add(k)
        for (ser,) in db.execute(
            select(ImportacionExtractoPagoConfirmado.serial_norm).where(
                ImportacionExtractoPagoConfirmado.estado == "ACTIVO"
            )
        ).all():
            k = _clave_digitos(ser)
            if k:
                claves.add(k)
    except Exception:
        logger.warning("[cobranzas-seriales] no se pudieron leer otras tablas", exc_info=True)
    return claves


def procesar_lote_seriales(
    db: Session,
    *,
    cedulas: list[str],
    depositos: list[dict[str, Any]],
    usados: Optional[list[int]] = None,
    simular: bool = False,
    tolerancia_pct: Any = 20,
    max_meses_adelante: int = 2,
) -> dict[str, Any]:
    """
    Procesa hasta 20 cédulas contra la cola de depósitos.

    ``depositos``: lista completa {id, fecha, serial, monto} en orden del Excel.
    ``usados``: ids ya consumidos en lotes anteriores (no se vuelven a usar).
    ``simular``: no escribe en BD; la cascada se simula sobre las cuotas atrasadas.
    ``tolerancia_pct``: margen sobre el monto de la cuota (20 = ±20%).
    ``max_meses_adelante``: meses posteriores al vencimiento en que se busca (0 = sin límite).
    """
    from fastapi import HTTPException

    if len(cedulas) > MAX_PRESTAMOS_LOTE:
        raise HTTPException(status_code=400, detail=f"Máximo {MAX_PRESTAMOS_LOTE} cédulas por lote.")
    if len(depositos) > MAX_DEPOSITOS:
        raise HTTPException(status_code=400, detail=f"Máximo {MAX_DEPOSITOS} depósitos.")
    try:
        tol = Decimal(str(tolerancia_pct))
    except Exception:
        tol = Decimal("20")
    if tol < 0 or tol > 50:
        raise HTTPException(status_code=400, detail="La tolerancia debe estar entre 0% y 50%.")
    tol = tol / Decimal("100")
    max_meses = max(0, int(max_meses_adelante or 0))

    hoy = hoy_negocio()
    cola = normalizar_depositos(depositos)
    usados_set: set[int] = {int(x) for x in (usados or [])}
    seriales_usados_lote: set[str] = {
        d["serial_norm"] for d in cola if d["id"] in usados_set and d["serial_norm"]
    }
    descartados_bd: set[int] = set()
    descartados_otras: set[int] = set()
    claves_otras = _claves_en_otras_tablas(db)
    meses_validos = [_mes(d["fecha"]) for d in cola if _deposito_valido(d)]
    ultimo_mes: Optional[tuple[int, int]] = max(meses_validos) if meses_validos else None

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
        puntero_mes: Optional[tuple[int, int]] = None
        aplicado_sim: dict[int, Decimal] = {}

        def saldo_de(c: Cuota) -> Decimal:
            base = _saldo_cuota(db, c)
            return max(Decimal("0"), base - aplicado_sim.get(id(c), Decimal("0")))

        for cuota in cuotas:
            if len(fila["pagos"]) >= MAX_PAGOS_POR_PRESTAMO:
                break
            saldo = saldo_de(cuota)
            if saldo <= _CENT:
                continue
            venc = cuota.fecha_vencimiento
            if hasattr(venc, "date") and not isinstance(venc, date):
                venc = venc.date()
            mes = _mes(venc)
            limite = ultimo_mes
            if max_meses > 0:
                m_lim = mes
                for _ in range(max_meses):
                    m_lim = _mes_siguiente(m_lim)
                if limite is None or m_lim < limite:
                    limite = m_lim
            if puntero_mes is not None and puntero_mes > mes:
                mes = puntero_mes
            mes_inicio = mes
            monto_c = Decimal(str(cuota.monto)) if cuota.monto is not None else saldo
            tope = monto_c * tol

            elegido: Optional[dict[str, Any]] = None
            numero_doc = ""
            alternativas = 0
            while limite is not None and mes <= limite:
                candidatos = []
                for dep in cola:
                    did = dep["id"]
                    if (
                        did in usados_set
                        or did in descartados_bd
                        or did in descartados_otras
                        or not _deposito_valido(dep)
                        or dep["monto"] <= 0
                        or _mes(dep["fecha"]) != mes
                        or dep["serial_norm"] in seriales_usados_lote
                        or abs(dep["monto"] - monto_c) > tope
                    ):
                        continue
                    if _clave_digitos(dep["serial_norm"]) in claves_otras:
                        descartados_otras.add(did)
                        continue
                    candidatos.append(dep)
                candidatos.sort(key=lambda d: (abs(d["monto"] - saldo), d["fecha"], d["id"]))
                for i, dep in enumerate(candidatos):
                    nd = compose_numero_documento_almacenado(
                        dep["serial_norm"], None, institucion=BANCO
                    )
                    if not nd:
                        continue
                    if numero_documento_ya_registrado(db, nd):
                        descartados_bd.add(dep["id"])
                        continue
                    elegido, numero_doc = dep, nd
                    alternativas = len(candidatos) - i - 1
                    break
                if elegido is not None:
                    break
                mes = _mes_siguiente(mes)

            if elegido is None:
                if saldo < monto_c - tope:
                    # Residuo menor que cualquier depósito aceptable: lo cubre la cascada
                    # del depósito de la cuota siguiente (aplica desde la más antigua).
                    fila["residuos_omitidos"] = fila.get("residuos_omitidos", 0) + 1
                    continue
                hasta_txt = _mes_txt(limite) if limite else "—"
                pct_txt = f"{(tol * 100).normalize():f}"
                en_rango = [
                    d
                    for d in cola
                    if _deposito_valido(d)
                    and d["monto"] > 0
                    and mes_inicio <= _mes(d["fecha"]) <= (limite or mes_inicio)
                    and abs(d["monto"] - monto_c) <= tope
                ]
                n_bd = sum(1 for d in en_rango if d["id"] in descartados_bd)
                n_otras = sum(1 for d in en_rango if d["id"] in descartados_otras)
                n_usados = sum(
                    1
                    for d in en_rango
                    if d["id"] in usados_set or d["serial_norm"] in seriales_usados_lote
                )
                parada = (
                    f"Cuota #{cuota.numero_cuota} de ${monto_c} (vence {venc.isoformat()}, falta ${saldo}): "
                    f"sin depósito ±{pct_txt}% del monto entre {_mes_txt(mes_inicio)} y {hasta_txt} "
                    f"(en rango: {len(en_rango)}; ya en BD: {n_bd}; usados en esta carga: {n_usados}; "
                    f"reportados/confirmados: {n_otras}); se detiene este préstamo"
                )
                break

            pago_id: Optional[int] = None
            det = "simulado"
            if simular:
                resto = elegido["monto"]
                for c in cuotas:
                    if resto <= 0:
                        break
                    falta = saldo_de(c)
                    if falta <= 0:
                        continue
                    aplica = min(falta, resto)
                    aplicado_sim[id(c)] = aplicado_sim.get(id(c), Decimal("0")) + aplica
                    resto -= aplica
            else:
                prestamo_id_log = int(getattr(prestamo, "id", 0) or 0)
                try:
                    pago, det = _crear_pago_mercantil(
                        db, prestamo=prestamo, cedula=cedula, dep=elegido, numero_doc=numero_doc
                    )
                except Exception as exc:
                    try:
                        db.rollback()
                    except Exception:
                        logger.debug("[cobranzas-seriales] rollback falló", exc_info=True)
                    logger.exception(
                        "[cobranzas-seriales] pago prestamo_id=%s", prestamo_id_log
                    )
                    parada = f"Error al crear pago: {str(exc)[:200]}"
                    break
                if pago is None:
                    try:
                        db.rollback()
                    except Exception:
                        logger.debug("[cobranzas-seriales] rollback falló", exc_info=True)
                    parada = f"No se pudo cargar el pago ({det}); se detiene este préstamo"
                    break
                if not bool(getattr(prestamo, "requiere_revision", False)):
                    prestamo.requiere_revision = True
                db.commit()
                pago_id = int(pago.id)

            usados_set.add(elegido["id"])
            nuevos_usados.append(elegido["id"])
            seriales_usados_lote.add(elegido["serial_norm"])
            puntero_mes = _mes_siguiente(mes)
            fila["pagos"].append(
                {
                    "pago_id": pago_id,
                    "deposito_id": elegido["id"],
                    "cuota_numero": int(cuota.numero_cuota),
                    "cuota_vencimiento": venc.isoformat(),
                    "saldo_cuota_antes": float(saldo),
                    "mes": _mes_txt(mes),
                    "fecha_deposito": elegido["fecha"].isoformat(),
                    "serial": elegido["serial_norm"],
                    "monto": float(elegido["monto"]),
                    "alternativas": alternativas,
                    "cascada": det,
                }
            )

        pendientes = sum(1 for c in cuotas if saldo_de(c) > _CENT)
        fila["cuotas_cubiertas"] = len(cuotas) - pendientes
        n = len(fila["pagos"])
        if n == 0:
            fila["estado"] = "SIN_COINCIDENCIA"
        elif pendientes > 0:
            fila["estado"] = "PARCIAL"
        else:
            fila["estado"] = "COMPLETO"
        verbo = "a cargar (simulación)" if simular else "cargado(s)"
        fila["detalle"] = parada or (
            f"{n} pago(s) {verbo}; {fila['cuotas_cubiertas']}/{len(cuotas)} cuotas atrasadas cubiertas"
        )
        if fila.get("residuos_omitidos"):
            fila["detalle"] += (
                f" · {fila['residuos_omitidos']} cuota(s) con residuo menor al rango: "
                "no se busca depósito propio, lo cubre la cascada"
            )
        resultados.append(fila)

    if nuevos_usados and not simular:
        try:
            invalidate_universo_analisis_cache()
        except Exception:
            logger.debug("[cobranzas-seriales] no se pudo invalidar caché universo", exc_info=True)

    return {
        "simulado": bool(simular),
        "procesadas": len(resultados),
        "pagos_creados": 0 if simular else len(nuevos_usados),
        "depositos_usados": nuevos_usados,
        "depositos_serial_en_bd": sorted(descartados_bd),
        "depositos_en_otras_tablas": sorted(descartados_otras),
        "resultados": resultados,
    }


MAX_DESHACER = 500


def deshacer_pagos_seriales(db: Session, pago_ids: list[int], *, current_user=None) -> dict[str, Any]:
    """
    Elimina pagos creados por este módulo (usuario_registro de seriales) con el flujo
    estándar de eliminación (limpia dependencias y realinea cuotas). Más recientes primero.
    """
    from fastapi import HTTPException

    from app.services.pagos_eliminar_service import ejecutar_eliminar_pago

    ids = sorted({int(x) for x in pago_ids if x}, reverse=True)
    if len(ids) > MAX_DESHACER:
        raise HTTPException(status_code=400, detail=f"Máximo {MAX_DESHACER} pagos por solicitud.")

    eliminados: list[int] = []
    omitidos: list[dict[str, Any]] = []
    errores: list[dict[str, Any]] = []
    for pid in ids:
        row = db.get(Pago, pid)
        if row is None:
            omitidos.append({"pago_id": pid, "motivo": "no existe"})
            continue
        if (row.usuario_registro or "").strip().lower() != USUARIO_REGISTRO:
            omitidos.append({"pago_id": pid, "motivo": "no fue cargado por Cobranzas → Seriales"})
            continue
        try:
            ejecutar_eliminar_pago(db, pid, current_user=current_user)
            eliminados.append(pid)
        except HTTPException as exc:
            db.rollback()
            errores.append({"pago_id": pid, "error": str(exc.detail)[:300]})
        except Exception as exc:
            db.rollback()
            logger.exception("[cobranzas-seriales] deshacer pago_id=%s", pid)
            errores.append({"pago_id": pid, "error": str(exc)[:300]})

    if eliminados:
        try:
            invalidate_universo_analisis_cache()
        except Exception:
            logger.debug("[cobranzas-seriales] no se pudo invalidar caché universo", exc_info=True)
    return {"eliminados": eliminados, "omitidos": omitidos, "errores": errores}


# --- Revisión manual por cédula -------------------------------------------------------
# Para cada cuota atrasada se muestran, por cada uno de los N meses posteriores a su
# vencimiento, los depósitos dentro de ±tolerancia del MONTO de la cuota. El usuario marca
# a lo sumo un depósito por mes y por préstamo; al guardar se crean los pagos y la cascada
# los aplica desde la cuota pendiente más antigua.

TOLERANCIA_REVISION = 30
MESES_REVISION = 3
MAX_GUARDAR_CEDULA = 60


def _venc(c: Cuota) -> date:
    v = c.fecha_vencimiento
    if hasattr(v, "date") and not isinstance(v, date):
        v = v.date()
    return v


def _todas_cuotas(db: Session, prestamo_id: int) -> list[Cuota]:
    return list(
        db.execute(
            select(Cuota)
            .where(Cuota.prestamo_id == int(prestamo_id))
            .order_by(Cuota.numero_cuota.asc())
        )
        .scalars()
        .all()
    )


def _cuota_dict(c: Cuota, hoy: date) -> dict[str, Any]:
    monto = Decimal(str(c.monto or 0)).quantize(_CENT, rounding=ROUND_HALF_UP)
    pagado = Decimal(str(c.total_pagado or 0)).quantize(_CENT, rounding=ROUND_HALF_UP)
    falta = max(Decimal("0"), monto - pagado)
    venc = _venc(c)
    return {
        "id": int(c.id),
        "numero": int(c.numero_cuota),
        "vencimiento": venc.isoformat(),
        "monto": float(monto),
        "pagado": float(pagado),
        "falta": float(falta),
        "estado": str(c.estado or ""),
        "atrasada": bool(venc < hoy and falta > _CENT),
    }


def _meses_despues(venc: date, n: int) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    m = _mes(venc)
    for _ in range(n):
        m = _mes_siguiente(m)
        out.append(m)
    return out


def _parse_tolerancia(tolerancia_pct: Any) -> Decimal:
    from fastapi import HTTPException

    try:
        tol = Decimal(str(tolerancia_pct))
    except Exception:
        tol = Decimal(TOLERANCIA_REVISION)
    if tol < 0 or tol > 50:
        raise HTTPException(status_code=400, detail="La tolerancia debe estar entre 0% y 50%.")
    return tol / Decimal("100")


def _dep_out(dep: dict[str, Any]) -> dict[str, Any]:
    return {
        "deposito_id": dep["id"],
        "fecha": dep["fecha"].isoformat(),
        "serial": dep["serial_norm"],
        "monto": float(dep["monto"]),
    }


def revision_cedula(
    db: Session,
    *,
    cedula: str,
    depositos: list[dict[str, Any]],
    usados: Optional[list[int]] = None,
    tolerancia_pct: Any = TOLERANCIA_REVISION,
    meses_despues: int = MESES_REVISION,
    seriales_tomados: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    Cuotas del préstamo más atrasado y depósitos candidatos por mes (sin escribir en BD).
    Un serial se aplica a un solo préstamo: se excluyen los usados en la sesión
    (``usados`` / ``seriales_tomados``) y los ya registrados en BD u otras tablas.
    """
    from fastapi import HTTPException

    if len(depositos) > MAX_DEPOSITOS:
        raise HTTPException(status_code=400, detail=f"Máximo {MAX_DEPOSITOS} depósitos.")
    tol = _parse_tolerancia(tolerancia_pct)
    n_meses = int(meses_despues or 0)
    if n_meses < 1 or n_meses > 12:
        raise HTTPException(status_code=400, detail="Los meses deben estar entre 1 y 12.")

    hoy = hoy_negocio()
    canon = _cedula_canon(cedula)
    base: dict[str, Any] = {
        "cedula": str(cedula or "").strip(),
        "cedula_norm": canon or None,
        "prestamo_id": None,
        "cliente": "",
        "cuotas": [],
        "bloques": [],
        "sugeridos": [],
        "depositos_serial_en_bd": [],
        "depositos_en_otras_tablas": [],
        "estado": "",
        "detalle": "",
    }
    if not canon:
        base.update(estado="CEDULA_INVALIDA", detalle="Cédula vacía o inválida")
        return base
    prestamo, atrasadas = _prestamo_mas_atrasado(db, canon, hoy)
    if prestamo is None:
        base.update(estado="SIN_ATRASO", detalle="Sin préstamo APROBADO con cuotas atrasadas")
        return base

    todas = _todas_cuotas(db, int(prestamo.id))
    base["prestamo_id"] = int(prestamo.id)
    base["cliente"] = str(getattr(prestamo, "nombres", "") or "")
    base["cuotas"] = [_cuota_dict(c, hoy) for c in todas]

    usados_set = {int(x) for x in (usados or [])}
    normalizados = normalizar_depositos(depositos)
    seriales_usados = {d["serial_norm"] for d in normalizados if d["id"] in usados_set}
    seriales_usados |= {_serial_norm(x) for x in (seriales_tomados or []) if x}
    cola = [
        d
        for d in normalizados
        if d["id"] not in usados_set
        and _deposito_valido(d)
        and d["monto"] > 0
        and d["serial_norm"] not in seriales_usados
    ]
    por_mes: dict[tuple[int, int], list[dict[str, Any]]] = {}
    for d in cola:
        por_mes.setdefault(_mes(d["fecha"]), []).append(d)

    claves_otras = _claves_en_otras_tablas(db)
    en_bd: set[int] = set()
    en_otras: set[int] = set()
    estado_serial: dict[str, str] = {}

    def disponible(dep: dict[str, Any]) -> bool:
        sn = dep["serial_norm"]
        if sn not in estado_serial:
            if _clave_digitos(sn) in claves_otras:
                estado_serial[sn] = "otras"
            else:
                nd = compose_numero_documento_almacenado(sn, None, institucion=BANCO)
                estado_serial[sn] = "bd" if (not nd or numero_documento_ya_registrado(db, nd)) else "ok"
        st = estado_serial[sn]
        if st == "otras":
            en_otras.add(dep["id"])
        elif st == "bd":
            en_bd.add(dep["id"])
        return st == "ok"

    bloques: list[dict[str, Any]] = []
    for c in atrasadas:
        monto_c = Decimal(str(c.monto or 0)).quantize(_CENT, rounding=ROUND_HALF_UP)
        tope = monto_c * tol
        meses_out = []
        for m in _meses_despues(_venc(c), n_meses):
            cands = [
                d
                for d in por_mes.get(m, [])
                if abs(d["monto"] - monto_c) <= tope and disponible(d)
            ]
            cands.sort(key=lambda d: (abs(d["monto"] - monto_c), d["fecha"], d["id"]))
            meses_out.append(
                {
                    "mes": _mes_txt(m),
                    "clave": f"{m[0]:04d}-{m[1]:02d}",
                    "candidatos": [_dep_out(d) for d in cands],
                    "_deps": cands,
                }
            )
        bloques.append(
            {
                "cuota_id": int(c.id),
                "cuota_numero": int(c.numero_cuota),
                "vencimiento": _venc(c).isoformat(),
                "monto": float(monto_c),
                "meses": meses_out,
            }
        )

    # Sugerencia: por cuota atrasada (más antigua primero), en sus meses y sin repetir mes,
    # el depósito más cercano a lo que le falta tras la cascada simulada, hasta cubrirla.
    falta: dict[int, Decimal] = {}
    for c in todas:
        f = Decimal(str(c.monto or 0)) - Decimal(str(c.total_pagado or 0))
        falta[int(c.id)] = max(Decimal("0"), f).quantize(_CENT, rounding=ROUND_HALF_UP)
    meses_tomados: set[str] = set()
    sugeridos: list[int] = []
    seriales_sugeridos: set[str] = set()

    def cascada(monto: Decimal) -> None:
        resto = monto
        for c in todas:
            if resto <= 0:
                break
            f = falta[int(c.id)]
            if f <= 0:
                continue
            aplica = min(f, resto)
            falta[int(c.id)] = f - aplica
            resto -= aplica

    for b in bloques:
        for mb in b["meses"]:
            pendiente = falta.get(b["cuota_id"], Decimal("0"))
            if pendiente <= _CENT:
                break
            if mb["clave"] in meses_tomados:
                continue
            libres = [d for d in mb["_deps"] if d["serial_norm"] not in seriales_sugeridos]
            if not libres:
                continue
            elegido = min(libres, key=lambda d: (abs(d["monto"] - pendiente), d["fecha"], d["id"]))
            sugeridos.append(elegido["id"])
            seriales_sugeridos.add(elegido["serial_norm"])
            meses_tomados.add(mb["clave"])
            cascada(elegido["monto"])
    for b in bloques:
        for mb in b["meses"]:
            mb.pop("_deps", None)

    hay = any(mb["candidatos"] for b in bloques for mb in b["meses"])
    pct_txt = f"{(tol * 100).normalize():f}"
    base.update(
        bloques=bloques,
        sugeridos=sugeridos,
        depositos_serial_en_bd=sorted(en_bd),
        depositos_en_otras_tablas=sorted(en_otras),
        estado="CON_CANDIDATOS" if hay else "SIN_CANDIDATOS",
        detalle=(
            f"{len(atrasadas)} cuota(s) atrasada(s); {len(sugeridos)} depósito(s) sugerido(s)"
            if hay
            else f"Sin depósitos ±{pct_txt}% en los {n_meses} meses posteriores a cada vencimiento"
        ),
    )
    return base


def guardar_revision_cedula(
    db: Session,
    *,
    cedula: str,
    prestamo_id: int,
    depositos: list[dict[str, Any]],
) -> dict[str, Any]:
    """Crea los pagos de los depósitos aprobados (orden por fecha) y aplica cascada."""
    from fastapi import HTTPException

    if not depositos:
        raise HTTPException(status_code=400, detail="No hay depósitos seleccionados.")
    if len(depositos) > MAX_GUARDAR_CEDULA:
        raise HTTPException(status_code=400, detail=f"Máximo {MAX_GUARDAR_CEDULA} depósitos por cédula.")

    hoy = hoy_negocio()
    canon = _cedula_canon(cedula)
    if not canon:
        raise HTTPException(status_code=400, detail="Cédula vacía o inválida.")
    prestamo, _atr = _prestamo_mas_atrasado(db, canon, hoy)
    if prestamo is None or int(prestamo.id) != int(prestamo_id):
        raise HTTPException(
            status_code=409,
            detail="El préstamo más atrasado de esta cédula cambió; vuelve a cargar la cédula.",
        )

    deps = normalizar_depositos(depositos)
    invalidos = [d["id"] for d in deps if not _deposito_valido(d) or d["monto"] <= 0]
    if invalidos:
        raise HTTPException(status_code=400, detail=f"Depósitos inválidos: {invalidos[:10]}")
    meses = [_mes(d["fecha"]) for d in deps]
    repetidos_mes = sorted({_mes_txt(m) for m in meses if meses.count(m) > 1})
    if repetidos_mes:
        raise HTTPException(
            status_code=400,
            detail=f"Solo un depósito por mes; repetidos: {', '.join(repetidos_mes)}",
        )
    seriales = [d["serial_norm"] for d in deps]
    rep_serial = sorted({s for s in seriales if seriales.count(s) > 1})
    if rep_serial:
        raise HTTPException(status_code=400, detail=f"Serial repetido: {', '.join(rep_serial[:5])}")

    claves_otras = _claves_en_otras_tablas(db)
    bloqueados: list[str] = []
    docs: dict[int, str] = {}
    for d in deps:
        nd = compose_numero_documento_almacenado(d["serial_norm"], None, institucion=BANCO)
        if not nd or _clave_digitos(d["serial_norm"]) in claves_otras or numero_documento_ya_registrado(db, nd):
            bloqueados.append(d["serial_norm"])
        else:
            docs[d["id"]] = nd
    if bloqueados:
        raise HTTPException(
            status_code=409,
            detail=f"Serial ya registrado o en otra tabla: {', '.join(bloqueados[:5])}",
        )

    creados: list[dict[str, Any]] = []
    error: Optional[str] = None
    prestamo_id_log = int(getattr(prestamo, "id", 0) or 0)
    for d in sorted(deps, key=lambda x: (x["fecha"], x["id"])):
        try:
            pago, det = _crear_pago_mercantil(
                db, prestamo=prestamo, cedula=canon, dep=d, numero_doc=docs[d["id"]]
            )
        except Exception as exc:
            try:
                db.rollback()
            except Exception:
                logger.debug("[cobranzas-seriales] rollback falló", exc_info=True)
            logger.exception(
                "[cobranzas-seriales] revisión pago prestamo_id=%s", prestamo_id_log
            )
            error = f"Error al crear pago (serial {d['serial_norm']}): {str(exc)[:200]}"
            break
        if pago is None:
            try:
                db.rollback()
            except Exception:
                logger.debug("[cobranzas-seriales] rollback falló", exc_info=True)
            error = f"No se pudo cargar el pago (serial {d['serial_norm']}): {det}"
            break
        if not bool(getattr(prestamo, "requiere_revision", False)):
            prestamo.requiere_revision = True
        db.commit()
        creados.append({**_dep_out(d), "pago_id": int(pago.id), "cascada": det})

    if creados:
        try:
            invalidate_universo_analisis_cache()
        except Exception:
            logger.debug("[cobranzas-seriales] no se pudo invalidar caché universo", exc_info=True)

    cuotas: list[dict[str, Any]] = []
    for c in _todas_cuotas(db, int(prestamo.id)):
        refresh = getattr(db, "refresh", None)
        if callable(refresh):
            try:
                refresh(c)
            except Exception:
                pass
        cuotas.append(_cuota_dict(c, hoy))
    return {"prestamo_id": int(prestamo.id), "pagos": creados, "error": error, "cuotas": cuotas}
