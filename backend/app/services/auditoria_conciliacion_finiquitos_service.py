"""
Conciliación archivo finiquitos vs sistema: Excel de cédulas → estados reales en BD.

No inventa estados: lee ``prestamos.estado``, ``prestamos.estado_gestion_finiquito``
y ``finiquito_casos.estado`` tal cual están persistidos.
"""
from __future__ import annotations

import io
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.finiquito import FiniquitoCaso
from app.models.prestamo import Prestamo
from app.services.cobranzas.universo_analisis_service import parse_cedulas_desde_excel
from app.utils.cedula_almacenamiento import (
    expr_cedula_normalizada_para_comparar,
    texto_cedula_comparable_bd,
)


def _variantes_clave_cedula(raw: str) -> Set[str]:
    """Claves comparables para cruzar Excel (solo dígitos) con BD (V/E/J/G + dígitos)."""
    key = texto_cedula_comparable_bd(raw)
    if not key:
        return set()
    out: Set[str] = {key}
    if key[0] in ("V", "E", "G", "J") and key[1:].isdigit():
        out.add(key[1:])
    if key[0].isdigit():
        for prefijo in ("V", "E", "G", "J"):
            out.add(f"{prefijo}{key}")
    return out


def comparar_cedulas_archivo_vs_sistema(
    db: Session,
    content: bytes,
) -> Dict[str, Any]:
    cedulas_archivo = parse_cedulas_desde_excel(content)
    if not cedulas_archivo:
        raise HTTPException(
            status_code=400,
            detail="El Excel no tiene cédulas en la columna A (o solo encabezados).",
        )

    excel_variantes: Dict[str, Set[str]] = {}
    all_keys: Set[str] = set()
    for ced in cedulas_archivo:
        vars_ = _variantes_clave_cedula(ced)
        excel_variantes[ced] = vars_
        all_keys |= vars_

    if not all_keys:
        raise HTTPException(status_code=400, detail="No se pudo normalizar ninguna cédula.")

    expr_p = expr_cedula_normalizada_para_comparar(Prestamo.cedula)
    prestamos = (
        db.query(Prestamo)
        .filter(expr_p.in_(list(all_keys)))
        .order_by(Prestamo.id.asc())
        .all()
    )

    cliente_ids = {int(p.cliente_id) for p in prestamos if p.cliente_id is not None}
    clientes_by_id: Dict[int, Cliente] = {}
    if cliente_ids:
        for c in db.query(Cliente).filter(Cliente.id.in_(list(cliente_ids))).all():
            clientes_by_id[int(c.id)] = c

    prestamo_ids = [int(p.id) for p in prestamos]
    casos_by_prestamo: Dict[int, FiniquitoCaso] = {}
    if prestamo_ids:
        for caso in (
            db.query(FiniquitoCaso)
            .filter(FiniquitoCaso.prestamo_id.in_(prestamo_ids))
            .all()
        ):
            casos_by_prestamo[int(caso.prestamo_id)] = caso

    prestamos_by_key: Dict[str, List[Prestamo]] = defaultdict(list)
    for p in prestamos:
        k = texto_cedula_comparable_bd(str(p.cedula or ""))
        if k:
            prestamos_by_key[k].append(p)

    items: List[Dict[str, Any]] = []
    no_encontradas = 0
    for ced in cedulas_archivo:
        matched: List[Prestamo] = []
        seen_ids: Set[int] = set()
        for vk in excel_variantes.get(ced) or set():
            for p in prestamos_by_key.get(vk) or []:
                pid = int(p.id)
                if pid in seen_ids:
                    continue
                seen_ids.add(pid)
                matched.append(p)

        if not matched:
            no_encontradas += 1
            items.append(
                {
                    "cedula_archivo": ced,
                    "en_sistema": False,
                    "cliente_id": None,
                    "nombres": None,
                    "prestamo_id": None,
                    "estado_prestamo": None,
                    "estado_gestion_finiquito": None,
                    "caso_finiquito_id": None,
                    "estado_caso_finiquito": None,
                    "estado_sistema": "NO_ENCONTRADA",
                }
            )
            continue

        for p in matched:
            cli = clientes_by_id.get(int(p.cliente_id)) if p.cliente_id else None
            caso = casos_by_prestamo.get(int(p.id))
            estado_prestamo = (p.estado or "").strip() or None
            items.append(
                {
                    "cedula_archivo": ced,
                    "en_sistema": True,
                    "cliente_id": int(p.cliente_id) if p.cliente_id else None,
                    "nombres": (cli.nombres if cli else p.nombres) or None,
                    "prestamo_id": int(p.id),
                    "estado_prestamo": estado_prestamo,
                    "estado_gestion_finiquito": (
                        (p.estado_gestion_finiquito or "").strip() or None
                    ),
                    "caso_finiquito_id": int(caso.id) if caso else None,
                    "estado_caso_finiquito": (
                        (caso.estado or "").strip() or None if caso else None
                    ),
                    # Columna principal pedida: estado del préstamo en sistema (sin inventar).
                    "estado_sistema": estado_prestamo or "SIN_ESTADO",
                }
            )

    por_estado: Dict[str, int] = defaultdict(int)
    for it in items:
        por_estado[str(it.get("estado_sistema") or "SIN_ESTADO")] += 1

    return {
        "total_cedulas_archivo": len(cedulas_archivo),
        "total_filas_resultado": len(items),
        "encontradas": len(cedulas_archivo) - no_encontradas,
        "no_encontradas": no_encontradas,
        "por_estado_sistema": dict(sorted(por_estado.items(), key=lambda x: (-x[1], x[0]))),
        "items": items,
    }


def exportar_resultado_excel(payload: Dict[str, Any]) -> bytes:
    try:
        from openpyxl import Workbook
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail="Dependencia openpyxl no disponible en el servidor.",
        ) from e

    wb = Workbook()
    ws = wb.active
    ws.title = "Conciliacion_finiquitos"
    headers = [
        "cedula_archivo",
        "en_sistema",
        "estado_sistema",
        "estado_prestamo",
        "estado_gestion_finiquito",
        "estado_caso_finiquito",
        "prestamo_id",
        "caso_finiquito_id",
        "cliente_id",
        "nombres",
    ]
    ws.append(headers)
    for it in payload.get("items") or []:
        ws.append(
            [
                it.get("cedula_archivo"),
                "SI" if it.get("en_sistema") else "NO",
                it.get("estado_sistema"),
                it.get("estado_prestamo"),
                it.get("estado_gestion_finiquito"),
                it.get("estado_caso_finiquito"),
                it.get("prestamo_id"),
                it.get("caso_finiquito_id"),
                it.get("cliente_id"),
                it.get("nombres"),
            ]
        )

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
