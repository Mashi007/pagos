"""
Pares de numero_documento similares entre pagos operativos de prestamos LIQUIDADO.

Usa difflib.SequenceMatcher (ratio 0..1). Umbral por defecto 0,70: no sustituye el control de
duplicado por doc_canon exacto; complementa capturas con errores tipograficos o variantes.
"""
from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.prestamo_cartera_auditoria import _sql_fragment_pago_excluido_cartera

# Max pagos con documento por prestamo para comparar O(n^2) sin explotar CPU.
_MAX_DOCS_POR_PRESTAMO_PAIRWISE = 100


def _norm_doc(s: str) -> str:
    return (s or "").strip().upper()


def _similitud(a: str, b: str) -> float:
    na, nb = _norm_doc(a), _norm_doc(b)
    if not na or not nb:
        return 0.0
    return float(SequenceMatcher(None, na, nb).ratio())


def documentos_similares_liquidados(
    db: Session,
    *,
    min_ratio: float = 0.70,
    prestamo_id: Optional[int] = None,
    cedula_contiene: Optional[str] = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Devuelve (tarjetas_por_prestamo, resumen).
    Cada tarjeta: prestamo_id, cedula, nombres, pares[{pago_id_a, pago_id_b, numero_documento_a,
    numero_documento_b, similitud, doc_canon_numero_a, doc_canon_numero_b}].
    """
    excl = _sql_fragment_pago_excluido_cartera("p")
    q = f"""
        SELECT
          p.prestamo_id,
          TRIM(COALESCE(pr.cedula, '')) AS cedula,
          TRIM(COALESCE(pr.nombres, '')) AS nombres,
          p.id AS pago_id,
          TRIM(COALESCE(p.numero_documento, '')) AS numero_documento,
          TRIM(COALESCE(p.doc_canon_numero, '')) AS doc_canon
        FROM pagos p
        INNER JOIN prestamos pr ON pr.id = p.prestamo_id
        WHERE UPPER(TRIM(COALESCE(pr.estado, ''))) = 'LIQUIDADO'
          AND p.prestamo_id IS NOT NULL
          AND TRIM(COALESCE(p.numero_documento, '')) <> ''
          AND NOT ({excl})
    """
    params: dict[str, Any] = {}
    if prestamo_id is not None:
        q += " AND p.prestamo_id = :pid"
        params["pid"] = int(prestamo_id)
    if cedula_contiene and str(cedula_contiene).strip():
        q += " AND UPPER(REPLACE(TRIM(pr.cedula), ' ', '')) LIKE :cedfrag"
        frag = f"%{str(cedula_contiene).strip().upper().replace(' ', '')}%"
        params["cedfrag"] = frag
    q += " ORDER BY p.prestamo_id, p.id"

    rows = db.execute(text(q), params).fetchall()

    por_pid: dict[int, dict[str, Any]] = {}
    for r in rows:
        pid = int(r[0])
        if pid not in por_pid:
            por_pid[pid] = {
                "prestamo_id": pid,
                "cedula": (r[1] or "").strip(),
                "nombres": (r[2] or "").strip(),
                "filas": [],
            }
        por_pid[pid]["filas"].append(
            {
                "pago_id": int(r[3]),
                "numero_documento": (r[4] or "").strip(),
                "doc_canon": (r[5] or "").strip(),
            }
        )

    min_r = max(0.5, min(1.0, float(min_ratio)))
    tarjetas: list[dict[str, Any]] = []
    total_pares = 0

    for pid in sorted(por_pid.keys()):
        info = por_pid[pid]
        filas = info["filas"]
        if len(filas) < 2:
            continue
        # Cap para coste O(n^2)
        filas_use = filas[:_MAX_DOCS_POR_PRESTAMO_PAIRWISE]
        pares: list[dict[str, Any]] = []
        seen: set[tuple[int, int]] = set()
        for i in range(len(filas_use)):
            for j in range(i + 1, len(filas_use)):
                a, b = filas_use[i], filas_use[j]
                doc_a, doc_b = a["numero_documento"], b["numero_documento"]
                r_sim = _similitud(doc_a, doc_b)
                if r_sim < min_r:
                    continue
                # Evitar repetir el mismo par (orden estable)
                pa, pb = sorted([a["pago_id"], b["pago_id"]])
                key = (pa, pb)
                if key in seen:
                    continue
                seen.add(key)
                pares.append(
                    {
                        "pago_id_a": a["pago_id"],
                        "pago_id_b": b["pago_id"],
                        "numero_documento_a": doc_a,
                        "numero_documento_b": doc_b,
                        "similitud": round(r_sim, 4),
                        "doc_canon_numero_a": a["doc_canon"] or None,
                        "doc_canon_numero_b": b["doc_canon"] or None,
                    }
                )
        if not pares:
            continue
        pares.sort(key=lambda x: (-float(x["similitud"]), x["pago_id_a"], x["pago_id_b"]))
        total_pares += len(pares)
        tarjetas.append(
            {
                "prestamo_id": pid,
                "cedula": info["cedula"],
                "nombres": info["nombres"],
                "pares": pares,
                "pares_truncados": len(filas) > _MAX_DOCS_POR_PRESTAMO_PAIRWISE,
                "n_pagos_con_documento": len(filas),
            }
        )

    resumen = {
        "umbral_similitud": min_r,
        "prestamos_con_pares_similares": len(tarjetas),
        "total_pares_listados": total_pares,
        "max_pagos_analizados_por_prestamo": _MAX_DOCS_POR_PRESTAMO_PAIRWISE,
        "metodo": "difflib.SequenceMatcher.ratio sobre numero_documento normalizado (trim + mayusculas)",
    }
    return tarjetas, resumen
