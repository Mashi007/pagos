"""
Hallazgos adicionales de auditoria intensiva para prestamos LIQUIDADO (cierre contable / finiquito / documentos).

Complementa `ejecutar_auditoria_cartera` (mismo universo de exclusion de pagos no operativos) con chequeos
orientados a cierre: fecha_liquidado, materializacion finiquito_casos, alineacion de snapshot finiquito vs BD,
documento canonico duplicado en el mismo prestamo, y pagos con saldo sin aplicar cuyo documento se repite
en otro prestamo (riesgo operativo de doble registro).
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Optional

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.services.prestamo_cartera_auditoria import _sql_fragment_pago_excluido_cartera


def _add(
    por_pid: dict[int, list[dict[str, str]]],
    pid: int,
    codigo: str,
    titulo: str,
    detalle: str,
) -> None:
    por_pid.setdefault(int(pid), []).append(
        {
            "codigo": codigo,
            "titulo": titulo,
            "alerta": "SI",
            "detalle": (detalle or "")[:500],
        }
    )


def hallazgos_cierre_prestamos_liquidados(db: Session) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Lista prestamos LIQUIDADO con al menos un hallazgo de cierre (alerta SI).
    No usa bitacora MARCAR_OK: es motor objetivo sobre tablas reales.
    """
    excl = _sql_fragment_pago_excluido_cartera("p")

    por_pid: dict[int, list[dict[str, str]]] = defaultdict(list)

    sin_fecha = db.execute(
        text(
            """
            SELECT p.id
            FROM prestamos p
            WHERE UPPER(TRIM(COALESCE(p.estado, ''))) = 'LIQUIDADO'
              AND p.fecha_liquidado IS NULL
            """
        )
    ).fetchall()
    for r in sin_fecha:
        _add(
            por_pid,
            int(r[0]),
            "liquidado_sin_fecha_liquidado",
            "LIQUIDADO sin fecha_liquidado",
            "El prestamo esta LIQUIDADO pero fecha_liquidado es NULL; conviene fechar el cierre en cartera.",
        )

    elegible_sin_finiquito = db.execute(
        text(
            """
            SELECT p.id
            FROM prestamos p
            INNER JOIN cuotas c ON c.prestamo_id = p.id
            WHERE UPPER(TRIM(COALESCE(p.estado, ''))) = 'LIQUIDADO'
            GROUP BY p.id, p.total_financiamiento
            HAVING COALESCE(SUM(COALESCE(c.total_pagado, 0)), 0) = p.total_financiamiento
              AND NOT EXISTS (SELECT 1 FROM finiquito_casos f WHERE f.prestamo_id = p.id)
            """
        )
    ).fetchall()
    for r in elegible_sin_finiquito:
        _add(
            por_pid,
            int(r[0]),
            "elegible_finiquito_sin_caso_materializado",
            "Elegible finiquito (suma cuotas = TF) sin fila en finiquito_casos",
            "Misma regla de igualdad exacta que el job de refresco finiquito; revisar cron o refresco puntual.",
        )

    finiquito_desalineado = db.execute(
        text(
            """
            SELECT
              p.id,
              f.sum_total_pagado AS snap_sum,
              (SELECT COALESCE(SUM(COALESCE(c.total_pagado, 0)), 0)
               FROM cuotas c WHERE c.prestamo_id = p.id) AS live_sum
            FROM prestamos p
            INNER JOIN finiquito_casos f ON f.prestamo_id = p.id
            WHERE UPPER(TRIM(COALESCE(p.estado, ''))) = 'LIQUIDADO'
              AND (
                f.total_financiamiento IS DISTINCT FROM p.total_financiamiento
                OR ABS(
                  (SELECT COALESCE(SUM(COALESCE(c.total_pagado, 0)), 0)
                   FROM cuotas c WHERE c.prestamo_id = p.id)::numeric
                  - f.sum_total_pagado::numeric
                ) > 0.02
              )
            """
        )
    ).fetchall()
    for r in finiquito_desalineado:
        pid = int(r[0])
        snap = r[1]
        live = r[2]
        _add(
            por_pid,
            pid,
            "finiquito_caso_desalineado_vs_bd",
            "finiquito_casos desalineado vs prestamo/cuotas vivas",
            f"snap_sum_total_pagado={snap} live_sum_total_pagado={live}",
        )

    dup_doc_mismo_prestamo = db.execute(
        text(
            f"""
            SELECT DISTINCT p.prestamo_id
            FROM pagos p
            INNER JOIN prestamos pr ON pr.id = p.prestamo_id
            WHERE UPPER(TRIM(COALESCE(pr.estado, ''))) = 'LIQUIDADO'
              AND p.prestamo_id IS NOT NULL
              AND TRIM(COALESCE(p.doc_canon_numero, '')) <> ''
              AND NOT ({excl})
            GROUP BY p.prestamo_id, p.doc_canon_numero
            HAVING COUNT(*) > 1
            """
        )
    ).fetchall()
    for r in dup_doc_mismo_prestamo:
        _add(
            por_pid,
            int(r[0]),
            "doc_operativo_duplicado_mismo_prestamo",
            "Documento operativo duplicado (doc_canon_numero) en el mismo prestamo",
            "Dos o mas pagos activos comparten el mismo documento canonico; revisar duplicados reales vs recibo partido.",
        )

    excl_p1 = _sql_fragment_pago_excluido_cartera("p1")
    excl_p2 = _sql_fragment_pago_excluido_cartera("p2")
    pendiente_doc_otro_prestamo = db.execute(
        text(
            f"""
            SELECT DISTINCT p1.prestamo_id
            FROM pagos p1
            INNER JOIN prestamos pr1 ON pr1.id = p1.prestamo_id
            INNER JOIN pagos p2 ON p1.doc_canon_numero = p2.doc_canon_numero
              AND p1.id <> p2.id
            INNER JOIN prestamos pr2 ON pr2.id = p2.prestamo_id
            WHERE UPPER(TRIM(COALESCE(pr1.estado, ''))) = 'LIQUIDADO'
              AND p1.prestamo_id IS NOT NULL
              AND p2.prestamo_id IS NOT NULL
              AND p1.prestamo_id <> p2.prestamo_id
              AND TRIM(COALESCE(p1.doc_canon_numero, '')) <> ''
              AND NOT ({excl_p1})
              AND NOT ({excl_p2})
              AND p1.monto_pagado > 0
              AND (
                NOT EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = p1.id)
                OR COALESCE((
                     SELECT SUM(cp2.monto_aplicado) FROM cuota_pagos cp2 WHERE cp2.pago_id = p1.id
                   ), 0) < (p1.monto_pagado::numeric - 0.02)
              )
            """
        )
    ).fetchall()
    for r in pendiente_doc_otro_prestamo:
        _add(
            por_pid,
            int(r[0]),
            "pago_pendiente_aplicacion_doc_repetido_otro_prestamo",
            "Pago con saldo sin aplicar y documento repetido en otro prestamo",
            "El comprobante canonico aparece en otro prestamo y aqui queda saldo sin aplicar a cuotas (tol 0.02 USD).",
        )

    pids = sorted(por_pid.keys())
    if not pids:
        return [], {
            "prestamos_con_hallazgo_cierre": 0,
            "hallazgos_totales": 0,
            "conteos_por_codigo": {},
        }

    rows_meta = db.execute(
        text(
            """
            SELECT p.id, p.cliente_id, p.cedula, p.nombres, p.estado, c.email AS cliente_email
            FROM prestamos p
            JOIN clientes c ON c.id = p.cliente_id
            WHERE p.id IN :ids
            ORDER BY p.id
            """
        ).bindparams(bindparam("ids", expanding=True)),
        {"ids": pids},
    ).fetchall()
    by_id = {int(r[0]): r for r in rows_meta}

    out: list[dict[str, Any]] = []
    conteos: dict[str, int] = {}
    total_hallazgos = 0
    for pid in pids:
        r = by_id.get(pid)
        if not r:
            continue
        ctrls = por_pid.get(pid, [])
        for c in ctrls:
            cod = str(c.get("codigo") or "").strip()
            if cod:
                conteos[cod] = conteos.get(cod, 0) + 1
                total_hallazgos += 1
        out.append(
            {
                "prestamo_id": pid,
                "cliente_id": int(r[1]),
                "cedula": (r[2] or "").strip(),
                "nombres": r[3] or "",
                "estado_prestamo": (r[4] or "").strip(),
                "cliente_email": (r[5] or "") or "",
                "tiene_alerta": True,
                "controles": ctrls,
            }
        )

    resumen = {
        "prestamos_con_hallazgo_cierre": len(out),
        "hallazgos_totales": int(total_hallazgos),
        "conteos_por_codigo": conteos,
    }
    return out, resumen


def filtrar_filas_cierre(
    rows: list[dict[str, Any]],
    *,
    prestamo_id: Optional[int] = None,
    cedula_contiene: Optional[str] = None,
) -> list[dict[str, Any]]:
    if prestamo_id is not None:
        rows = [r for r in rows if int(r.get("prestamo_id") or 0) == int(prestamo_id)]
    if cedula_contiene and str(cedula_contiene).strip():
        q = str(cedula_contiene).strip().upper().replace(" ", "")
        rows = [
            r
            for r in rows
            if q in str(r.get("cedula") or "").strip().upper().replace(" ", "")
        ]
    return rows


def paginar_filas(
    rows: list[dict[str, Any]],
    *,
    skip: int = 0,
    limit: Optional[int] = None,
) -> list[dict[str, Any]]:
    s = max(0, int(skip))
    page = rows[s:] if s else rows
    if limit is not None:
        page = page[: int(limit)]
    return page


def resumen_cierre_desde_filas(rows: list[dict[str, Any]]) -> dict[str, Any]:
    conteos: dict[str, int] = {}
    total = 0
    for r in rows:
        for c in r.get("controles", []) or []:
            cod = str(c.get("codigo") or "").strip()
            if not cod:
                continue
            conteos[cod] = conteos.get(cod, 0) + 1
            total += 1
    return {
        "prestamos_con_hallazgo_cierre": len(rows),
        "hallazgos_totales": int(total),
        "conteos_por_codigo": conteos,
    }
