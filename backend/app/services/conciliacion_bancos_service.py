"""Conciliacion Bancos: carga Excel, match vs numero_documento, decision y aplicacion segura."""
from __future__ import annotations

import io
import json
import logging
import re
from datetime import date, datetime
from decimal import Decimal
from difflib import SequenceMatcher
from typing import Any, Optional

from fastapi import HTTPException, UploadFile
from openpyxl import Workbook, load_workbook
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.core.documento import normalize_documento, split_numero_documento_almacenado
from app.models.conciliacion_banco_ocr import (
    ConciliacionBancoOcrBanco,
    ConciliacionBancoOcrLote,
    ConciliacionBancoOcrResultado,
)
from app.models.pago import Pago
from app.services.cuota_pago_integridad import pago_tiene_aplicaciones_cuotas
from app.services.pago_numero_documento import numero_documento_ya_registrado
from app.services.tasa_cambio_service import (
    obtener_tasa_por_fecha,
    tasa_y_equivalente_usd_excel,
)

logger = logging.getLogger(__name__)

SIMILITUD_MINIMA = 70.0
MONTO_TOL = 0.02


BANCOS_CATEGORIAS = ("Mercantil", "BNC", "Binance", "BNV", "Recibos", "Otros")


def categoria_institucion(inst: Optional[str]) -> str:
    """Misma clasificacion que dashboard pagos por institucion."""
    s = (inst or "").strip().lower()
    if "mercantil" in s:
        return "Mercantil"
    if "bnc" in s or s == "banco nacional de credito":
        return "BNC"
    if "binance" in s:
        return "Binance"
    if "bnv" in s or "bdv" in s or "banco de venezuela" in s:
        return "BNV"
    if "recibo" in s:
        return "Recibos"
    return "Otros"


def normalizar_bancos_filtro(bancos: Optional[list[str]]) -> list[str]:
    allowed = set(BANCOS_CATEGORIAS)
    out: list[str] = []
    for b in bancos or []:
        name = (b or "").strip()
        if name in allowed and name not in out:
            out.append(name)
    return out


def _guardar_bancos_en_lote(lote: ConciliacionBancoOcrLote, bancos: list[str]) -> None:
    payload = {"bancos_filtro": bancos}
    lote.notas = json.dumps(payload, ensure_ascii=True)


def _leer_bancos_de_lote(lote: ConciliacionBancoOcrLote) -> list[str]:
    raw = (lote.notas or "").strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return normalizar_bancos_filtro(data.get("bancos_filtro") or [])
    except Exception:
        pass
    return []



# Prefijos/etiquetas frecuentes que operadores agregan al serial
_REF_RUIDO_PREFIX = re.compile(
    r"^(?:"
    r"(?:bs\.?\s*)?(?:bnc|binance|mercantil|bnv|bdv|ve|zelle|paypal|banco)\s*"
    r"(?:/\s*|[-–—]\s*|\s+)"
    r"(?:ref\.?\s*)?"
    r"|ref\.?\s*|nro\.?\s*|n[uú]m(?:ero)?\.?\s*|doc\.?\s*|comp(?:robante)?\.?\s*"
    r")+",
    re.IGNORECASE,
)


def _ref_solo_digitos(val: Optional[str]) -> str:
    """
    Clave de match/similitud: solo digitos del comprobante.

    - Ignora letras y signos agregados por digitacion (REF-, BNC/, puntos, guiones, etc.).
    - Quita sufijo interno §CD: (codigo desambiguador) para no contaminar la clave.
    - Maneja notacion cientifica via normalize_documento.
    """
    if val is None or val == "":
        return ""
    base, _codigo = split_numero_documento_almacenado(val)
    s = normalize_documento(base) or (base or str(val)).strip()
    if not s:
        return ""
    # Quitar etiquetas al inicio en bucle (BNC/ REF. ...)
    prev = None
    while prev != s:
        prev = s
        s2 = _REF_RUIDO_PREFIX.sub("", s).strip()
        s = s2 if s2 else s
        break  # una pasada basta; el bucle evita bucles raros si regex vacia
    # Solo digitos: letras/signos no participan en similitud
    return re.sub(r"\D+", "", s)


def _similitud(a: str, b: str) -> float:
    da, db = _ref_solo_digitos(a), _ref_solo_digitos(b)
    if not da or not db:
        return 0.0
    if da == db:
        return 100.0
    # Contencion: "90694665" vs "00090694665" / extras de digitacion
    shorter, longer = (da, db) if len(da) <= len(db) else (db, da)
    if len(shorter) >= 6 and shorter in longer:
        return round(100.0 * (len(shorter) / len(longer)), 2)
    return round(SequenceMatcher(None, da, db).ratio() * 100.0, 2)


def _parse_fecha(val: Any) -> Optional[date]:
    if val is None or val == "":
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    s = str(val).strip()
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%d-%m-%y", "%d/%m/%y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _parse_monto(val: Any) -> Optional[Decimal]:
    if val is None or val == "":
        return None
    if isinstance(val, (int, float, Decimal)):
        return Decimal(str(round(float(val), 2)))
    s = str(val).strip().replace(" ", "").replace(",", ".")
    s = re.sub(r"[^\d.\-]", "", s)
    if not s:
        return None
    try:
        return Decimal(str(round(float(s), 2)))
    except Exception:
        return None


def _pago_fecha(p: Pago) -> Optional[date]:
    fp = p.fecha_pago
    if fp is None:
        return None
    return fp.date() if hasattr(fp, "date") else fp


def _snapshot_pago(p: Pago) -> dict[str, Any]:
    return {
        "pago_id": p.id,
        "fecha_pago": _pago_fecha(p).isoformat() if _pago_fecha(p) else None,
        "monto_pagado": float(p.monto_pagado or 0),
        "numero_documento": p.numero_documento,
        "moneda_registro": p.moneda_registro,
        "monto_bs_original": float(p.monto_bs_original) if p.monto_bs_original is not None else None,
        "tasa_cambio_bs_usd": float(p.tasa_cambio_bs_usd) if p.tasa_cambio_bs_usd is not None else None,
        "fecha_tasa_referencia": p.fecha_tasa_referencia.isoformat() if p.fecha_tasa_referencia else None,
    }


def crear_lote_desde_excel(
    db: Session,
    *,
    file: UploadFile,
    content: bytes,
    moneda_carga: str,
    fecha_desde: date,
    fecha_hasta: date,
    usuario_id: Optional[int],
) -> ConciliacionBancoOcrLote:
    mon = (moneda_carga or "USD").strip().upper()
    if mon not in ("USD", "BS"):
        raise HTTPException(status_code=400, detail="moneda_carga debe ser USD o BS")
    if fecha_hasta < fecha_desde:
        raise HTTPException(status_code=400, detail="fecha_hasta debe ser >= fecha_desde")
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="Debe subir un Excel (.xlsx o .xls)")

    try:
        wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Excel invalido: {e}") from e
    ws = wb.active
    if not ws:
        raise HTTPException(status_code=400, detail="Excel sin hoja activa")

    lote = ConciliacionBancoOcrLote(
        usuario_id=usuario_id,
        archivo_nombre=(file.filename or "banco.xlsx")[:255],
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        estado="CARGADO",
        moneda_carga=mon,
    )
    db.add(lote)
    db.flush()

    n = 0
    for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if not row:
            continue
        fecha_b = _parse_fecha(row[0] if len(row) > 0 else None)
        ref_raw = str(row[1]).strip() if len(row) > 1 and row[1] is not None else ""
        monto_raw = _parse_monto(row[2] if len(row) > 2 else None)
        if not ref_raw and monto_raw is None and fecha_b is None:
            continue
        if not ref_raw:
            continue
        ref_norm = normalize_documento(ref_raw) or ref_raw.strip()
        db.add(
            ConciliacionBancoOcrBanco(
                lote_id=lote.id,
                fila_excel=i,
                fecha_banco=fecha_b,
                referencia_banco=ref_raw,
                ref_banco_norm=ref_norm,
                monto_banco=monto_raw if mon == "USD" else None,
                monto_banco_original=monto_raw,
                moneda_fila=mon,
            )
        )
        n += 1

    if n == 0:
        db.rollback()
        raise HTTPException(status_code=400, detail="No hay filas validas (Fecha, Referencia, Monto)")

    db.commit()
    db.refresh(lote)
    return lote


def comparar_lote(
    db: Session,
    lote_id: int,
    *,
    bancos_filtro: Optional[list[str]] = None,
) -> dict[str, Any]:
    lote = db.get(ConciliacionBancoOcrLote, lote_id)
    if not lote:
        raise HTTPException(status_code=404, detail="Lote no encontrado")

    bancos_sel = normalizar_bancos_filtro(bancos_filtro)
    if not bancos_sel:
        raise HTTPException(
            status_code=400,
            detail="Seleccione al menos un banco (Mercantil, BNC, Binance, BNV, Recibos, Otros).",
        )
    _guardar_bancos_en_lote(lote, bancos_sel)

    # Conservar filas ya confirmadas (visto / corregir aplicado / omitir).
    # Solo se regeneran las PENDIENTE: asi el reporte Excel no pierde lo confirmado
    # y esas refs/pagos no vuelven a salir como trabajo pendiente.
    confirmados_lote = (
        db.execute(
            select(ConciliacionBancoOcrResultado).where(
                ConciliacionBancoOcrResultado.lote_id == lote_id,
                or_(
                    ConciliacionBancoOcrResultado.decision == "VISTO",
                    ConciliacionBancoOcrResultado.decision == "OMITIR",
                    (ConciliacionBancoOcrResultado.decision == "CORREGIR")
                    & (ConciliacionBancoOcrResultado.aplicado.is_(True)),
                ),
            )
        )
        .scalars()
        .all()
    )
    # Confirmados de cualquier lote (futuras conciliaciones)
    confirmados_global = (
        db.execute(
            select(ConciliacionBancoOcrResultado).where(
                or_(
                    ConciliacionBancoOcrResultado.decision == "VISTO",
                    ConciliacionBancoOcrResultado.decision == "OMITIR",
                    (ConciliacionBancoOcrResultado.decision == "CORREGIR")
                    & (ConciliacionBancoOcrResultado.aplicado.is_(True)),
                ),
            )
        )
        .scalars()
        .all()
    )

    excluir_pago_ids: set[int] = set()
    excluir_banco_ids: set[int] = set()
    excluir_digitos: set[str] = set()
    for c in list(confirmados_lote) + list(confirmados_global):
        if c.pago_id:
            excluir_pago_ids.add(int(c.pago_id))
        if c.banco_id:
            excluir_banco_ids.add(int(c.banco_id))
        d1 = _ref_solo_digitos(c.referencia_banco)
        d2 = _ref_solo_digitos(c.referencia_bd)
        if d1:
            excluir_digitos.add(d1)
        if d2:
            excluir_digitos.add(d2)

    db.execute(
        delete(ConciliacionBancoOcrResultado).where(
            ConciliacionBancoOcrResultado.lote_id == lote_id,
            ConciliacionBancoOcrResultado.decision == "PENDIENTE",
        )
    )

    bancos = (
        db.execute(
            select(ConciliacionBancoOcrBanco).where(
                ConciliacionBancoOcrBanco.lote_id == lote_id
            )
        )
        .scalars()
        .all()
    )
    bancos = [
        b
        for b in bancos
        if int(b.id) not in excluir_banco_ids
        and _ref_solo_digitos(b.ref_banco_norm or b.referencia_banco) not in excluir_digitos
    ]

    pagos_raw = (
        db.execute(
            select(Pago).where(
                func.date(Pago.fecha_pago) >= lote.fecha_desde,
                func.date(Pago.fecha_pago) <= lote.fecha_hasta,
                Pago.numero_documento.isnot(None),
                Pago.numero_documento != "",
            )
        )
        .scalars()
        .all()
    )
    # Solo pagos de las instituciones seleccionadas (evita ruido de otros bancos)
    pagos = [
        p
        for p in pagos_raw
        if categoria_institucion(p.institucion_bancaria) in bancos_sel
        and int(p.id) not in excluir_pago_ids
        and _ref_solo_digitos(p.numero_documento) not in excluir_digitos
    ]

    by_digits: dict[str, list[Pago]] = {}
    for p in pagos:
        key = _ref_solo_digitos(normalize_documento(p.numero_documento) or p.numero_documento or "")
        if not key:
            continue
        by_digits.setdefault(key, []).append(p)

    matched_pago_ids: set[int] = set(excluir_pago_ids)
    stats = {
        "MATCH_EXACTO": 0,
        "MATCH_PARCIAL": 0,
        "SIN_BD": 0,
        "SIN_BANCO": 0,
        "AMBIGUO": 0,
        "SIN_TASA": 0,
    }

    for b in bancos:
        ref_b = b.ref_banco_norm or b.referencia_banco
        dig_b = _ref_solo_digitos(ref_b)
        fecha_b = b.fecha_banco
        monto_orig = float(b.monto_banco_original) if b.monto_banco_original is not None else None
        monto_usd: Optional[float] = None
        tipo_extra = None

        if lote.moneda_carga == "USD":
            monto_usd = monto_orig
        elif monto_orig is not None and fecha_b is not None:
            tasa, usd = tasa_y_equivalente_usd_excel(db, fecha_b, monto_orig, "BS")
            if usd is None:
                tipo_extra = "SIN_TASA"
            else:
                monto_usd = usd
                b.monto_banco = Decimal(str(usd))
        elif monto_orig is not None:
            tipo_extra = "SIN_TASA"

        candidatos_exactos = by_digits.get(dig_b, []) if dig_b else []

        if tipo_extra == "SIN_TASA" and lote.moneda_carga == "BS":
            db.add(
                ConciliacionBancoOcrResultado(
                    lote_id=lote_id,
                    banco_id=b.id,
                    pago_id=None,
                    fecha_banco=fecha_b,
                    referencia_banco=b.referencia_banco,
                    monto_banco=None,
                    similitud_pct=None,
                    tipo_novedad="SIN_TASA",
                    decision="PENDIENTE",
                    detalle_aplicacion="Sin tasa Bs/USD para la fecha del banco; no se puede comparar monto.",
                )
            )
            stats["SIN_TASA"] += 1
            continue

        if len(candidatos_exactos) == 1:
            p = candidatos_exactos[0]
            matched_pago_ids.add(p.id)
            db.add(
                ConciliacionBancoOcrResultado(
                    lote_id=lote_id,
                    banco_id=b.id,
                    pago_id=p.id,
                    fecha_banco=fecha_b,
                    fecha_bd=_pago_fecha(p),
                    referencia_banco=b.referencia_banco,
                    referencia_bd=p.numero_documento,
                    monto_banco=Decimal(str(monto_usd)) if monto_usd is not None else None,
                    monto_bd=p.monto_pagado,
                    similitud_pct=Decimal("100"),
                    tipo_novedad="MATCH_EXACTO",
                    decision="PENDIENTE",
                )
            )
            stats["MATCH_EXACTO"] += 1
            continue

        if len(candidatos_exactos) > 1:
            db.add(
                ConciliacionBancoOcrResultado(
                    lote_id=lote_id,
                    banco_id=b.id,
                    pago_id=None,
                    fecha_banco=fecha_b,
                    referencia_banco=b.referencia_banco,
                    monto_banco=Decimal(str(monto_usd)) if monto_usd is not None else None,
                    similitud_pct=Decimal("100"),
                    tipo_novedad="AMBIGUO",
                    decision="PENDIENTE",
                    detalle_aplicacion=(
                        f"Varios pagos con el mismo numero_documento normalizado "
                        f"({len(candidatos_exactos)}). Discernimiento manual."
                    ),
                )
            )
            stats["AMBIGUO"] += 1
            continue

        # Match parcial: candidatos por monto cercano en el rango
        mejores: list[tuple[float, Pago]] = []
        for p in pagos:
            if p.id in matched_pago_ids:
                continue
            sim = _similitud(ref_b, p.numero_documento or "")
            if sim < SIMILITUD_MINIMA:
                continue
            if monto_usd is not None:
                md = float(p.monto_pagado or 0)
                if abs(md - monto_usd) > MONTO_TOL and sim < 95.0:
                    continue
            mejores.append((sim, p))
        mejores.sort(key=lambda x: x[0], reverse=True)

        if not mejores:
            db.add(
                ConciliacionBancoOcrResultado(
                    lote_id=lote_id,
                    banco_id=b.id,
                    pago_id=None,
                    fecha_banco=fecha_b,
                    referencia_banco=b.referencia_banco,
                    monto_banco=Decimal(str(monto_usd)) if monto_usd is not None else None,
                    similitud_pct=None,
                    tipo_novedad="SIN_BD",
                    decision="PENDIENTE",
                    detalle_aplicacion="Referencia banco sin match en BD (voucher no digitalizado / no reportado).",
                )
            )
            stats["SIN_BD"] += 1
            continue

        if len(mejores) > 1 and abs(mejores[0][0] - mejores[1][0]) < 0.5:
            db.add(
                ConciliacionBancoOcrResultado(
                    lote_id=lote_id,
                    banco_id=b.id,
                    pago_id=None,
                    fecha_banco=fecha_b,
                    referencia_banco=b.referencia_banco,
                    monto_banco=Decimal(str(monto_usd)) if monto_usd is not None else None,
                    similitud_pct=Decimal(str(mejores[0][0])),
                    tipo_novedad="AMBIGUO",
                    decision="PENDIENTE",
                    detalle_aplicacion="Varios candidatos con similitud similar. Discernimiento manual.",
                )
            )
            stats["AMBIGUO"] += 1
            continue

        sim, p = mejores[0]
        matched_pago_ids.add(p.id)
        db.add(
            ConciliacionBancoOcrResultado(
                lote_id=lote_id,
                banco_id=b.id,
                pago_id=p.id,
                fecha_banco=fecha_b,
                fecha_bd=_pago_fecha(p),
                referencia_banco=b.referencia_banco,
                referencia_bd=p.numero_documento,
                monto_banco=Decimal(str(monto_usd)) if monto_usd is not None else None,
                monto_bd=p.monto_pagado,
                similitud_pct=Decimal(str(sim)),
                tipo_novedad="MATCH_PARCIAL",
                decision="PENDIENTE",
            )
        )
        stats["MATCH_PARCIAL"] += 1

    for p in pagos:
        if p.id in matched_pago_ids:
            continue
        db.add(
            ConciliacionBancoOcrResultado(
                lote_id=lote_id,
                banco_id=None,
                pago_id=p.id,
                fecha_bd=_pago_fecha(p),
                referencia_bd=p.numero_documento,
                monto_bd=p.monto_pagado,
                similitud_pct=None,
                tipo_novedad="SIN_BANCO",
                decision="PENDIENTE",
                detalle_aplicacion="Pago en BD del rango sin fila correspondiente en Excel banco.",
            )
        )
        stats["SIN_BANCO"] += 1

    lote.estado = "COMPARADO"
    db.commit()
    return {
        "lote_id": lote_id,
        "estado": lote.estado,
        "stats": stats,
        "bancos_filtro": bancos_sel,
        "pagos_universo": len(pagos),
        "confirmados_conservados": len(confirmados_lote),
        "excluidos_por_confirmacion": len(excluir_pago_ids) + len(excluir_digitos),
    }


def _paquetes_iguales(
    fecha_a: Optional[date],
    monto_a: Optional[float],
    serial_a: Optional[str],
    fecha_b: Optional[date],
    monto_b: Optional[float],
    serial_b: Optional[str],
) -> bool:
    sa = _ref_solo_digitos(normalize_documento(serial_a) or serial_a or "")
    sb = _ref_solo_digitos(normalize_documento(serial_b) or serial_b or "")
    if sa != sb:
        return False
    if fecha_a != fecha_b:
        return False
    ma = float(monto_a or 0)
    mb = float(monto_b or 0)
    return abs(ma - mb) < MONTO_TOL


def decidir_y_aplicar(
    db: Session,
    resultado_id: int,
    *,
    decision: str,
    fuente_elegida: Optional[str],
    usuario_id: Optional[int],
) -> dict[str, Any]:
    res = db.get(ConciliacionBancoOcrResultado, resultado_id)
    if not res:
        raise HTTPException(status_code=404, detail="Resultado no encontrado")
    if res.aplicado and res.decision in ("VISTO", "CORREGIR"):
        raise HTTPException(status_code=400, detail="Esta fila ya fue procesada")

    dec = (decision or "").strip().upper()
    if dec not in ("VISTO", "CORREGIR", "OMITIR"):
        raise HTTPException(status_code=400, detail="decision invalida")

    now = datetime.now()
    res.usuario_decision_id = usuario_id
    res.decidido_en = now

    if dec == "OMITIR":
        res.decision = "OMITIR"
        res.aplicado = False
        res.detalle_aplicacion = "Omitido por administrador"
        db.commit()
        return {"ok": True, "resultado_id": res.id, "decision": res.decision, "aplicado": False}

    if dec == "VISTO":
        res.decision = "VISTO"
        res.aplicado = False
        res.fuente_elegida = None
        res.detalle_aplicacion = "Visto: sin cambios en BD"
        db.commit()
        return {"ok": True, "resultado_id": res.id, "decision": res.decision, "aplicado": False}

    # CORREGIR
    fuente = (fuente_elegida or "").strip().upper()
    if fuente not in ("BD", "BANCO"):
        raise HTTPException(
            status_code=400,
            detail="Para CORREGIR indique fuente_elegida=BD o BANCO",
        )
    res.decision = "CORREGIR"
    res.fuente_elegida = fuente

    if res.tipo_novedad in ("SIN_BD", "SIN_TASA") or not res.pago_id:
        raise HTTPException(
            status_code=400,
            detail="No hay pago BD vinculado; no se puede corregir (no se crean pagos).",
        )

    pago = db.get(Pago, res.pago_id)
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")

    lote = db.get(ConciliacionBancoOcrLote, res.lote_id)
    if not lote:
        raise HTTPException(status_code=404, detail="Lote no encontrado")

    antes = _snapshot_pago(pago)
    res.valores_antes = json.dumps(antes, ensure_ascii=True)

    if fuente == "BD":
        # Mantener paquete BD: sin escritura operativa
        res.aplicado = True
        res.detalle_aplicacion = "Se eligio Referencia BD: sin cambios (paquete ya en BD)."
        res.valores_despues = json.dumps(antes, ensure_ascii=True)
        db.commit()
        return {
            "ok": True,
            "resultado_id": res.id,
            "decision": res.decision,
            "fuente_elegida": fuente,
            "aplicado": True,
            "cambio": False,
        }

    # fuente BANCO
    fecha_new = res.fecha_banco or _pago_fecha(pago)
    # Preferir serial limpio (solo digitos) si tras quitar ruido queda un nucleo numerico
    serial_raw = normalize_documento(res.referencia_banco) or (res.referencia_banco or "").strip()
    serial_dig = _ref_solo_digitos(res.referencia_banco)
    serial_new = serial_dig if serial_dig else serial_raw
    if not serial_new:
        raise HTTPException(status_code=400, detail="Referencia banco vacia")

    monto_new_usd: Optional[float]
    monto_bs_orig = None
    tasa_usada = None
    if lote.moneda_carga == "BS":
        banco = db.get(ConciliacionBancoOcrBanco, res.banco_id) if res.banco_id else None
        monto_orig = (
            float(banco.monto_banco_original)
            if banco and banco.monto_banco_original is not None
            else (float(res.monto_banco) if res.monto_banco is not None else None)
        )
        if fecha_new is None or monto_orig is None:
            raise HTTPException(status_code=400, detail="Falta fecha/monto banco para convertir Bs")
        tasa_usada, monto_new_usd = tasa_y_equivalente_usd_excel(db, fecha_new, monto_orig, "BS")
        if monto_new_usd is None:
            raise HTTPException(
                status_code=400,
                detail=f"No hay tasa Bs/USD para {fecha_new.isoformat()}",
            )
        monto_bs_orig = monto_orig
    else:
        monto_new_usd = float(res.monto_banco) if res.monto_banco is not None else float(pago.monto_pagado or 0)

    if _paquetes_iguales(
        _pago_fecha(pago),
        float(pago.monto_pagado or 0),
        pago.numero_documento,
        fecha_new,
        monto_new_usd,
        serial_new,
    ):
        res.aplicado = True
        res.detalle_aplicacion = "Paquete banco coincide con BD: sin cambios."
        res.valores_despues = json.dumps(antes, ensure_ascii=True)
        db.commit()
        return {
            "ok": True,
            "resultado_id": res.id,
            "decision": res.decision,
            "fuente_elegida": fuente,
            "aplicado": True,
            "cambio": False,
        }

    # Conflicto de serial en otro pago -> no forzar
    if numero_documento_ya_registrado(db, serial_new, exclude_pago_id=pago.id):
        # No forzar: dejar pendiente para discernimiento (Visto / otra fuente)
        res.decision = "PENDIENTE"
        res.fuente_elegida = None
        res.aplicado = False
        res.detalle_aplicacion = (
            "Serial banco ya existe en otro pago. Discernimiento manual (puede marcar Visto)."
        )
        db.commit()
        raise HTTPException(
            status_code=409,
            detail=res.detalle_aplicacion,
        )

    had_cp = pago_tiene_aplicaciones_cuotas(db, pago.id)
    old_fecha = _pago_fecha(pago)
    old_monto = float(pago.monto_pagado or 0)

    # Actualizar pago
    if fecha_new is not None:
        pago.fecha_pago = datetime.combine(fecha_new, datetime.min.time())
    pago.monto_pagado = Decimal(str(round(float(monto_new_usd), 2)))
    pago.numero_documento = serial_new[:100]
    if lote.moneda_carga == "BS":
        pago.moneda_registro = "BS"
        pago.monto_bs_original = Decimal(str(round(float(monto_bs_orig), 2))) if monto_bs_orig is not None else None
        pago.tasa_cambio_bs_usd = Decimal(str(tasa_usada)) if tasa_usada is not None else None
        pago.fecha_tasa_referencia = fecha_new
    else:
        if not pago.moneda_registro:
            pago.moneda_registro = "USD"

    db.flush()

    fecha_changed = had_cp and old_fecha != _pago_fecha(pago)
    monto_changed = had_cp and abs(old_monto - float(pago.monto_pagado or 0)) >= MONTO_TOL
    cascada_info = None

    if (fecha_changed or monto_changed) and pago.prestamo_id:
        # Misma ruta segura que actualizar_pago cuando articula cuotas
        from app.services.pagos_cuotas_reaplicacion import reset_y_reaplicar_cascada_prestamo
        from app.services.pago_huella_funcional import primer_par_huella_duplicada_prestamo

        par = primer_par_huella_duplicada_prestamo(db, int(pago.prestamo_id))
        if par is not None:
            db.rollback()
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Huella funcional duplicada en prestamo {pago.prestamo_id} "
                    f"(pagos {par[0]} / {par[1]}). No se aplico el cambio."
                ),
            )
        r = reset_y_reaplicar_cascada_prestamo(db, int(pago.prestamo_id))
        if not r.get("ok"):
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail=f"No se pudo reaplicar cascada: {r.get('error')}",
            )
        cascada_info = r
    elif (
        not had_cp
        and pago.prestamo_id
        and float(pago.monto_pagado or 0) > 0
    ):
        from app.services.pagos_cascada_aplicacion import _aplicar_pago_a_cuotas_interno

        cc, cp = _aplicar_pago_a_cuotas_interno(pago, db)
        cascada_info = {"cuotas_completadas": cc, "cuotas_parciales": cp}

    despues = _snapshot_pago(pago)
    res.valores_despues = json.dumps(despues, ensure_ascii=True)
    res.aplicado = True
    res.referencia_bd = pago.numero_documento
    res.fecha_bd = _pago_fecha(pago)
    res.monto_bd = pago.monto_pagado
    res.detalle_aplicacion = (
        "Actualizado con paquete banco (fecha/monto/serial) "
        + ("y cascada reaplicada." if cascada_info else "sin rearticulacion de cuotas.")
    )
    lote.estado = "APLICADO"
    db.commit()
    return {
        "ok": True,
        "resultado_id": res.id,
        "decision": res.decision,
        "fuente_elegida": fuente,
        "aplicado": True,
        "cambio": True,
        "cascada": cascada_info,
        "antes": antes,
        "despues": despues,
    }


def listar_resultados(db: Session, lote_id: int) -> list[dict[str, Any]]:
    rows = (
        db.execute(
            select(ConciliacionBancoOcrResultado)
            .where(ConciliacionBancoOcrResultado.lote_id == lote_id)
            .order_by(ConciliacionBancoOcrResultado.id.asc())
        )
        .scalars()
        .all()
    )
    pago_ids = [int(r.pago_id) for r in rows if r.pago_id]
    pagos_map: dict[int, Pago] = {}
    if pago_ids:
        for p in db.execute(select(Pago).where(Pago.id.in_(pago_ids))).scalars().all():
            pagos_map[int(p.id)] = p
    out = []
    for r in rows:
        pago = pagos_map.get(int(r.pago_id)) if r.pago_id else None
        out.append(
            {
                "id": r.id,
                "lote_id": r.lote_id,
                "banco_id": r.banco_id,
                "pago_id": r.pago_id,
                "cedula": (pago.cedula_cliente if pago else None),
                "prestamo_id": (pago.prestamo_id if pago else None),
                "institucion_bancaria": (pago.institucion_bancaria if pago else None),
                "institucion_categoria": (
                    categoria_institucion(pago.institucion_bancaria) if pago else None
                ),
                "fecha_banco": r.fecha_banco.isoformat() if r.fecha_banco else None,
                "fecha_bd": r.fecha_bd.isoformat() if r.fecha_bd else None,
                "referencia_banco": r.referencia_banco,
                "referencia_bd": r.referencia_bd,
                "monto_banco": float(r.monto_banco) if r.monto_banco is not None else None,
                "monto_bd": float(r.monto_bd) if r.monto_bd is not None else None,
                "similitud_pct": float(r.similitud_pct) if r.similitud_pct is not None else None,
                "tipo_novedad": r.tipo_novedad,
                "decision": r.decision,
                "fuente_elegida": r.fuente_elegida,
                "aplicado": bool(r.aplicado),
                "detalle_aplicacion": r.detalle_aplicacion,
            }
        )
    return out


_EXPORT_HEADERS = [
    "referencia_banco",
    "referencia_bd",
    "similitud_pct",
    "cedula",
    "prestamo_id",
    "institucion_bancaria",
    "institucion_categoria",
    "fecha_banco",
    "fecha_bd",
    "monto_banco_usd",
    "monto_bd_usd",
    "tipo_novedad",
    "decision",
    "fuente_elegida",
    "aplicado",
    "pago_id",
    "detalle",
]

# Una pestana por caso (mismo orden que chips de la UI)
_EXPORT_HOJAS_NOVEDAD = (
    "MATCH_EXACTO",
    "MATCH_PARCIAL",
    "SIN_BD",
    "SIN_BANCO",
    "AMBIGUO",
    "SIN_TASA",
)


def _fila_export_resultado(r: dict[str, Any]) -> list[Any]:
    return [
        r.get("referencia_banco"),
        r.get("referencia_bd"),
        r.get("similitud_pct"),
        r.get("cedula"),
        r.get("prestamo_id"),
        r.get("institucion_bancaria"),
        r.get("institucion_categoria"),
        r.get("fecha_banco"),
        r.get("fecha_bd"),
        r.get("monto_banco"),
        r.get("monto_bd"),
        r.get("tipo_novedad"),
        r.get("decision"),
        r.get("fuente_elegida"),
        r.get("aplicado"),
        r.get("pago_id"),
        r.get("detalle_aplicacion"),
    ]


def exportar_excel_lote(db: Session, lote_id: int) -> bytes:
    """Excel con una hoja por tipo de novedad (MATCH_EXACTO, MATCH_PARCIAL, ...)."""
    rows = listar_resultados(db, lote_id)
    by_tipo: dict[str, list[dict[str, Any]]] = {k: [] for k in _EXPORT_HOJAS_NOVEDAD}
    for r in rows:
        tipo = (r.get("tipo_novedad") or "").strip() or "OTROS"
        if tipo not in by_tipo:
            by_tipo[tipo] = []
        by_tipo[tipo].append(r)

    wb = Workbook()
    first = True
    for tipo in list(_EXPORT_HOJAS_NOVEDAD) + [
        k for k in by_tipo.keys() if k not in _EXPORT_HOJAS_NOVEDAD
    ]:
        items = by_tipo.get(tipo, [])
        title = tipo[:31]
        if first:
            ws = wb.active
            ws.title = title
            first = False
        else:
            ws = wb.create_sheet(title=title)
        ws.append(list(_EXPORT_HEADERS))
        for r in items:
            ws.append(_fila_export_resultado(r))

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
