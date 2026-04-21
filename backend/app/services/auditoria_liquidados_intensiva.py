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


def _where_prestamo_cedula_sql(
    *,
    alias_pr: str,
    alias_p: Optional[str],
    prestamo_id: Optional[int],
    cedula_contiene: Optional[str],
    params: dict[str, Any],
) -> str:
    """
    Fragmentos AND alineados con otras consultas de intensiva liquidados (misma cédula LIKE).
    `alias_p` se usa solo si prestamo_id no es None (columna prestamo_id del pago).
    """
    pr = alias_pr.strip()
    extra = ""
    if prestamo_id is not None:
        col = f"{alias_p.strip()}.prestamo_id" if alias_p else f"{pr}.id"
        extra += f" AND {col} = :cov_pid"
        params["cov_pid"] = int(prestamo_id)
    if cedula_contiene and str(cedula_contiene).strip():
        extra += (
            f" AND UPPER(REPLACE(TRIM({pr}.cedula), ' ', '')) LIKE :cov_cedfrag"
        )
        frag = f"%{str(cedula_contiene).strip().upper().replace(' ', '')}%"
        params["cov_cedfrag"] = frag
    return extra


def cobertura_pagos_prestamos_liquidados(
    db: Session,
    *,
    prestamo_id: Optional[int] = None,
    cedula_contiene: Optional[str] = None,
) -> dict[str, Any]:
    """
    Conteos para auditoria de **completitud**: todo pago del universo LIQUIDADO (con filtros) frente al
    subconjunto **operativo cartera** (misma exclusion que totales / duplicados / similitud de documento).

    No sustituye listados detallados; evita la sensacion de 'pagos invisibles' cuando solo se miran
    heuristicas sobre `numero_documento` o cuadres sobre operativos.
    """
    excl = _sql_fragment_pago_excluido_cartera("p")
    params: dict[str, Any] = {}
    w_extra_pr = _where_prestamo_cedula_sql(
        alias_pr="pr",
        alias_p=None,
        prestamo_id=prestamo_id,
        cedula_contiene=cedula_contiene,
        params=params,
    )
    w_extra_join = _where_prestamo_cedula_sql(
        alias_pr="pr",
        alias_p="p",
        prestamo_id=prestamo_id,
        cedula_contiene=cedula_contiene,
        params=params,
    )

    row = db.execute(
        text(
            f"""
            SELECT
              COUNT(DISTINCT pr.id)::bigint AS n_prestamos_distintos_con_algun_pago,
              COUNT(*)::bigint AS n_pagos_total_filas,
              COALESCE(SUM(CASE WHEN NOT ({excl}) THEN 1 ELSE 0 END), 0)::bigint
                AS n_pagos_operativos_cartera,
              COALESCE(SUM(CASE WHEN ({excl}) THEN 1 ELSE 0 END), 0)::bigint
                AS n_pagos_excluidos_cartera,
              COALESCE(
                SUM(
                  CASE
                    WHEN NOT ({excl}) AND TRIM(COALESCE(p.numero_documento, '')) = ''
                    THEN 1 ELSE 0
                  END
                ),
                0
              )::bigint AS n_pagos_operativos_sin_numero_documento
            FROM pagos p
            INNER JOIN prestamos pr ON pr.id = p.prestamo_id
            WHERE UPPER(TRIM(COALESCE(pr.estado, ''))) = 'LIQUIDADO'
              AND p.prestamo_id IS NOT NULL
              {w_extra_join}
            """
        ),
        params,
    ).fetchone()

    n_sin = db.execute(
        text(
            f"""
            SELECT COUNT(*)::bigint
            FROM prestamos pr
            WHERE UPPER(TRIM(COALESCE(pr.estado, ''))) = 'LIQUIDADO'
              AND NOT EXISTS (SELECT 1 FROM pagos p WHERE p.prestamo_id = pr.id)
              {w_extra_pr}
            """
        ),
        params,
    ).scalar()

    n_solo_excl = db.execute(
        text(
            f"""
            SELECT COUNT(*)::bigint
            FROM (
              SELECT pr.id
              FROM prestamos pr
              INNER JOIN pagos p ON p.prestamo_id = pr.id
              WHERE UPPER(TRIM(COALESCE(pr.estado, ''))) = 'LIQUIDADO'
                AND p.prestamo_id IS NOT NULL
                {w_extra_join}
              GROUP BY pr.id
              HAVING SUM(CASE WHEN NOT ({excl}) THEN 1 ELSE 0 END) = 0
            ) t
            """
        ),
        params,
    ).scalar()

    regla = (
        "Operativo cartera = pago NO anulado/reversado/duplicado declarado: excluye estados "
        "ANULADO_IMPORT, DUPLICADO, CANCELADO, RECHAZADO, REVERSADO; cualquier estado que contenga "
        "ANUL o REVERS; y cancelado/rechazado en minusculas (misma regla que totales de cartera)."
    )
    nota = (
        "Los cuadres motor, duplicados por canon y similitud de documento trabajan sobre **pagos operativos**. "
        "Las filas excluidas siguen en BD: si un estado fue mal clasificado, revoque el exclusion revisando "
        "el pago en Cobros / historial. Use 'operativos sin numero_documento' para cierre sin huella de comprobante."
    )

    if not row:
        return {
            "n_prestamos_distintos_con_algun_pago": 0,
            "n_pagos_total_filas": 0,
            "n_pagos_operativos_cartera": 0,
            "n_pagos_excluidos_cartera": 0,
            "n_pagos_operativos_sin_numero_documento": 0,
            "n_prestamos_liquidados_sin_ningun_pago": int(n_sin or 0),
            "n_prestamos_con_pagos_todos_excluidos_cartera": int(n_solo_excl or 0),
            "regla_exclusion_operativo_resumen": regla,
            "nota_completitud_auditoria": nota,
        }

    return {
        "n_prestamos_distintos_con_algun_pago": int(row[0] or 0),
        "n_pagos_total_filas": int(row[1] or 0),
        "n_pagos_operativos_cartera": int(row[2] or 0),
        "n_pagos_excluidos_cartera": int(row[3] or 0),
        "n_pagos_operativos_sin_numero_documento": int(row[4] or 0),
        "n_prestamos_liquidados_sin_ningun_pago": int(n_sin or 0),
        "n_prestamos_con_pagos_todos_excluidos_cartera": int(n_solo_excl or 0),
        "regla_exclusion_operativo_resumen": regla,
        "nota_completitud_auditoria": nota,
    }


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
