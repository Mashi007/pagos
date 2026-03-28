"""
Auditoria de cartera por prestamo: controles desde tablas reales (prestamos, clientes, cuotas, pagos, cuota_pagos).

La lista de alertas es orientativa; debe revisarla un humano. La corrida automatica (03:00 America/Caracas)
alinea antes `cuotas.estado` con `clasificar_estado_cuota`, luego evalua y actualiza metadatos en
`configuracion`; el GET del API recalcula en tiempo real para reflejar la BD actual.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.models.configuracion import Configuracion
from app.services.cuota_estado import clasificar_estado_cuota, hoy_negocio
from app.utils.cedula_almacenamiento import normalizar_cedula_almacenamiento

logger = logging.getLogger(__name__)

_TOL = Decimal("0.02")
CFG_ULTIMA = "auditoria_cartera_ultima_ejecucion"
CFG_RESUMEN = "auditoria_cartera_ultima_resumen"


def _dec(x: Any) -> Decimal:
    if x is None:
        return Decimal("0")
    if isinstance(x, Decimal):
        return x
    return Decimal(str(x))


def _upsert_config_valor(db: Session, clave: str, valor: str) -> None:
    row = db.get(Configuracion, clave)
    if row:
        row.valor = valor
    else:
        db.add(Configuracion(clave=clave, valor=valor))


def persistir_meta_ejecucion(
    db: Session,
    *,
    total_evaluados: int,
    con_alerta: int,
    commit: bool = True,
) -> None:
    """Guarda hora y resumen de la ultima corrida (job 03:00 o manual)."""
    now = datetime.now(timezone.utc).isoformat()
    resumen = json.dumps(
        {
            "ultima_ejecucion_utc": now,
            "prestamos_evaluados": total_evaluados,
            "prestamos_con_alerta": con_alerta,
        },
        ensure_ascii=False,
    )
    _upsert_config_valor(db, CFG_ULTIMA, now)
    _upsert_config_valor(db, CFG_RESUMEN, resumen)
    if commit:
        db.commit()


def leer_meta_ejecucion(db: Session) -> dict[str, Any]:
    r1 = db.get(Configuracion, CFG_RESUMEN)
    raw = (r1.valor if r1 and r1.valor else "") or "{}"
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def ejecutar_auditoria_cartera(
    db: Session,
    *,
    solo_con_alerta: bool = True,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Evalua prestamos en estados operativos. Retorna (filas, resumen).
    Solo se devuelven prestamos con al menos un control en alerta SI.
    En cada fila, `controles` solo incluye entradas con alerta SI (no se exponen los NO).
    Param solo_con_alerta: reservado por compatibilidad con la API; no altera el resultado.
    """
    _ = solo_con_alerta

    hoy = hoy_negocio()

    rows_p = db.execute(
        text(
            """
            SELECT p.id, p.cliente_id, p.cedula, p.nombres, p.estado, p.numero_cuotas, p.total_financiamiento,
                   c.email AS cliente_email, c.cedula AS cliente_cedula
            FROM prestamos p
            JOIN clientes c ON c.id = p.cliente_id
            WHERE p.estado IN ('APROBADO', 'LIQUIDADO')
            ORDER BY p.id
            """
        )
    ).fetchall()

    if not rows_p:
        meta = {"prestamos_evaluados": 0, "prestamos_con_alerta": 0, "fecha_referencia": str(hoy)}
        return [], meta

    prestamo_ids = [int(r[0]) for r in rows_p]

    # Cedulas con mas de un prestamo en APROBADO (misma cedula)
    dup_cedulas_rows = db.execute(
        text(
            """
            SELECT UPPER(TRIM(BOTH FROM cedula)) AS ced_norm, COUNT(*) AS n
            FROM prestamos
            WHERE estado = 'APROBADO'
            GROUP BY UPPER(TRIM(BOTH FROM cedula))
            HAVING COUNT(*) > 1
            """
        )
    ).fetchall()
    dup_cedulas = {str(r[0]).strip() for r in dup_cedulas_rows if r[0]}

    # Misma cedula + mismo nombre + mismo dia de fecha_registro (varios prestamos activos)
    dup_nombre_cedula_fecha_rows = db.execute(
        text(
            """
            SELECT DISTINCT p.id
            FROM prestamos p
            INNER JOIN (
              SELECT
                UPPER(TRIM(BOTH FROM cedula)) AS ced,
                UPPER(TRIM(BOTH FROM nombres)) AS nom,
                CAST(fecha_registro AS date) AS fd,
                COUNT(*) AS cnt
              FROM prestamos
              WHERE estado IN ('APROBADO', 'LIQUIDADO')
              GROUP BY
                UPPER(TRIM(BOTH FROM cedula)),
                UPPER(TRIM(BOTH FROM nombres)),
                CAST(fecha_registro AS date)
              HAVING COUNT(*) > 1
            ) d ON UPPER(TRIM(BOTH FROM p.cedula)) = d.ced
               AND UPPER(TRIM(BOTH FROM p.nombres)) = d.nom
               AND CAST(p.fecha_registro AS date) = d.fd
            WHERE p.estado IN ('APROBADO', 'LIQUIDADO')
            """
        )
    ).fetchall()
    prestamos_dup_nombre_cedula_fecha = {int(r[0]) for r in dup_nombre_cedula_fecha_rows if r[0] is not None}

    # Pagos duplicados mismo dia y monto (posible fraude / doble registro)
    dup_pagos_rows = db.execute(
        text(
            """
            SELECT DISTINCT prestamo_id
            FROM (
              SELECT prestamo_id, CAST(fecha_pago AS date) AS fd, monto_pagado, COUNT(*) AS cnt
              FROM pagos
              WHERE prestamo_id IS NOT NULL
              GROUP BY prestamo_id, CAST(fecha_pago AS date), monto_pagado
              HAVING COUNT(*) > 1
            ) t
            """
        )
    ).fetchall()
    prestamos_pagos_duplicados = {int(r[0]) for r in dup_pagos_rows if r[0] is not None}

    # Pagos con monto no positivo
    bad_monto_rows = db.execute(
        text(
            """
            SELECT DISTINCT prestamo_id FROM pagos
            WHERE prestamo_id IS NOT NULL AND monto_pagado <= 0
            """
        )
    ).fetchall()
    prestamos_monto_mal = {int(r[0]) for r in bad_monto_rows if r[0] is not None}

    tot_sql = (
        text(
            """
            SELECT p.id,
              COALESCE(sp.s, 0) AS sum_pagos,
              COALESCE(sa.s, 0) AS sum_aplicado,
              COALESCE(sc.s, 0) AS sum_cuotas
            FROM prestamos p
            LEFT JOIN LATERAL (
              SELECT SUM(monto_pagado) AS s FROM pagos WHERE prestamo_id = p.id
            ) sp ON true
            LEFT JOIN LATERAL (
              SELECT SUM(cp.monto_aplicado) AS s
              FROM cuotas cu
              JOIN cuota_pagos cp ON cp.cuota_id = cu.id
              WHERE cu.prestamo_id = p.id
            ) sa ON true
            LEFT JOIN LATERAL (
              SELECT SUM(monto_cuota) AS s FROM cuotas cu WHERE cu.prestamo_id = p.id
            ) sc ON true
            WHERE p.id IN :ids
            """
        ).bindparams(bindparam("ids", expanding=True))
    )
    tot_rows2 = db.execute(tot_sql, {"ids": prestamo_ids}).fetchall()
    tot_map = {int(tr[0]): (_dec(tr[1]), _dec(tr[2]), _dec(tr[3])) for tr in tot_rows2}

    # LIQUIDADO con cuota aun con saldo
    liq_incoherent = db.execute(
        text(
            """
            SELECT DISTINCT p.id
            FROM prestamos p
            JOIN cuotas cu ON cu.prestamo_id = p.id
            WHERE p.estado = 'LIQUIDADO'
              AND (cu.total_pagado IS NULL OR cu.total_pagado < cu.monto_cuota - 0.01)
            """
        )
    ).fetchall()
    prestamos_liq_incoherent = {int(r[0]) for r in liq_incoherent}

    # Conteo de cuotas por prestamo
    ncu_sql = (
        text(
            """
            SELECT prestamo_id, COUNT(*) FROM cuotas WHERE prestamo_id IN :ids GROUP BY prestamo_id
            """
        ).bindparams(bindparam("ids", expanding=True))
    )
    ncu_rows = db.execute(ncu_sql, {"ids": prestamo_ids}).fetchall()
    ncu_map = {int(r[0]): int(r[1]) for r in ncu_rows}

    # Cuotas para coherencia de estado
    cuo_sql = (
        text(
            """
            SELECT id, prestamo_id, monto_cuota, total_pagado, fecha_vencimiento, estado
            FROM cuotas
            WHERE prestamo_id IN :ids
            ORDER BY prestamo_id, numero_cuota
            """
        ).bindparams(bindparam("ids", expanding=True))
    )
    cuo_rows = db.execute(cuo_sql, {"ids": prestamo_ids}).fetchall()

    cuotas_por_prestamo: dict[int, list[tuple[Any, ...]]] = {}
    for cr in cuo_rows:
        pid = int(cr[1])
        cuotas_por_prestamo.setdefault(pid, []).append(cr)

    out: list[dict[str, Any]] = []
    con_alerta_count = 0

    for r in rows_p:
        pid = int(r[0])
        cliente_id = int(r[1])
        cedula_p = (r[2] or "").strip()
        nombres = r[3] or ""
        estado_p = (r[4] or "").strip()
        numero_cuotas_cfg = int(r[5] or 0)
        total_fin = _dec(r[6])
        email_c = r[7]
        cedula_c = (r[8] or "").strip()

        controles: list[dict[str, str]] = []

        def add_control(codigo: str, titulo: str, alerta: str, detalle: str) -> None:
            controles.append(
                {
                    "codigo": codigo,
                    "titulo": titulo,
                    "alerta": alerta,
                    "detalle": detalle[:500] if detalle else "",
                }
            )

        nc_p = normalizar_cedula_almacenamiento(cedula_p) or ""
        nc_c = normalizar_cedula_almacenamiento(cedula_c) or ""
        ced_mismatch = "SI" if nc_p != nc_c else "NO"
        add_control(
            "cedula_cliente_vs_prestamo",
            "Cedula cliente vs prestamo",
            ced_mismatch,
            f"Prestamo={nc_p or cedula_p} Cliente={nc_c or cedula_c}" if ced_mismatch == "SI" else "Coinciden",
        )

        ced_norm_upper = (cedula_p or "").strip().upper()
        dup_prest = "SI" if ced_norm_upper in dup_cedulas else "NO"
        add_control(
            "prestamos_duplicados_misma_cedula",
            "Varios prestamos activos (APROBADO/APROBADO) misma cedula",
            dup_prest,
            "Existe otro prestamo APROBADO en cartera con la misma cedula" if dup_prest == "SI" else "Unico o sin otro APROBADO duplicado por cedula",
        )

        dup_triple = "SI" if pid in prestamos_dup_nombre_cedula_fecha else "NO"
        add_control(
            "prestamos_duplicados_nombre_cedula_fecha_registro",
            "Prestamos duplicados (mismo nombre, cedula y fecha de registro)",
            dup_triple,
            (
                "Otro prestamo APROBADO/LIQUIDADO comparte cedula, nombres y el mismo dia de fecha_registro"
                if dup_triple == "SI"
                else "Sin duplicado por nombre+cedula+dia de registro"
            ),
        )

        dup_pay = "SI" if pid in prestamos_pagos_duplicados else "NO"
        add_control(
            "pagos_mismo_dia_monto",
            "Pagos duplicados (misma fecha y monto)",
            dup_pay,
            "Dos o mas pagos el mismo dia con igual monto" if dup_pay == "SI" else "Sin duplicados por fecha+monto",
        )

        bad_m = "SI" if pid in prestamos_monto_mal else "NO"
        add_control(
            "pagos_monto_no_positivo",
            "Pagos con monto cero o negativo",
            bad_m,
            "Hay pagos asociados con monto <= 0" if bad_m == "SI" else "OK",
        )

        sp, sa, sc = tot_map.get(pid, (Decimal("0"), Decimal("0"), Decimal("0")))
        diff_ap = abs(sp - sa)
        alert_ap = "SI" if diff_ap > _TOL else "NO"
        add_control(
            "total_pagado_vs_aplicado_cuotas",
            "Total pagos vs total aplicado a cuotas (cuota_pagos)",
            alert_ap,
            f"Suma pagos={sp} aplicado cuotas={sa} diff={diff_ap}" if alert_ap == "SI" else f"Cuadrado dentro de tolerancia (diff={diff_ap})",
        )

        diff_tf = abs(total_fin - sc)
        alert_tf = "SI" if sc > 0 and diff_tf > _TOL else "NO"
        add_control(
            "total_financiamiento_vs_suma_cuotas",
            "Total financiamiento vs suma de cuotas",
            alert_tf,
            f"TF={total_fin} suma cuotas={sc} diff={diff_tf}" if alert_tf == "SI" else f"OK (diff={diff_tf})",
        )

        n_cu = ncu_map.get(pid, 0)
        if estado_p == "APROBADO" and numero_cuotas_cfg > 0 and n_cu == 0:
            add_control("sin_cuotas", "Prestamo aprobado sin filas en cuotas", "SI", "numero_cuotas>0 pero tabla cuotas vacia")
        else:
            add_control("sin_cuotas", "Prestamo aprobado sin filas en cuotas", "NO", f"Cuotas en BD: {n_cu}")

        if n_cu > 0 and numero_cuotas_cfg > 0 and n_cu != numero_cuotas_cfg:
            add_control(
                "numero_cuotas_inconsistente",
                "Numero de cuotas configurado vs filas en BD",
                "SI",
                f"prestamo.numero_cuotas={numero_cuotas_cfg} filas={n_cu}",
            )
        else:
            add_control(
                "numero_cuotas_inconsistente",
                "Numero de cuotas configurado vs filas en BD",
                "NO",
                f"prestamo.numero_cuotas={numero_cuotas_cfg} filas={n_cu}",
            )

        liq_bad = "SI" if pid in prestamos_liq_incoherent else "NO"
        add_control(
            "liquidado_con_cuota_pendiente",
            "LIQUIDADO con cuota sin cubrir al 100%",
            liq_bad,
            "Incoherencia estado prestamo vs saldos de cuotas" if liq_bad == "SI" else "OK",
        )

        # Estado de cuota en columna vs calculado (misma regla que API)
        estado_cuotas_mal = False
        det_parts: list[str] = []
        for cu in cuotas_por_prestamo.get(pid, []):
            _cid, _pid, monto_c, tot_p, fv, est_col = cu[0], cu[1], cu[2], cu[3], cu[4], cu[5]
            calc = clasificar_estado_cuota(
                float(tot_p or 0),
                float(monto_c or 0),
                fv,
                hoy,
            )
            col = (est_col or "").strip().upper().replace("PAGADA", "PAGADO")
            calc_u = (calc or "").strip().upper()
            if col != calc_u:
                estado_cuotas_mal = True
                det_parts.append(f"cuota_id={_cid} columna={col} calculado={calc_u}")
        add_control(
            "estado_cuota_vs_calculo",
            "Estado en tabla cuotas vs regla de negocio (vencimiento y pagos)",
            "SI" if estado_cuotas_mal else "NO",
            "; ".join(det_parts[:5]) + ("..." if len(det_parts) > 5 else "") if estado_cuotas_mal else "Columna alineada con calculo",
        )


        controles_si = [c for c in controles if c.get("alerta") == "SI"]
        tiene_alerta = bool(controles_si)
        if tiene_alerta:
            con_alerta_count += 1

        if not controles_si:
            continue

        out.append(
            {
                "prestamo_id": pid,
                "cliente_id": cliente_id,
                "cedula": cedula_p,
                "nombres": nombres,
                "estado_prestamo": estado_p,
                "cliente_email": email_c or "",
                "tiene_alerta": True,
                "controles": controles_si,
            }
        )

    meta = {
        "prestamos_evaluados": len(rows_p),
        "prestamos_con_alerta": con_alerta_count,
        "prestamos_listados": len(out),
        "fecha_referencia": str(hoy),
    }
    return out, meta


def prestamos_ids_alerta_total_pagos_vs_aplicado(rows: list[dict[str, Any]]) -> list[int]:
    """IDs de prestamos con control SI `total_pagado_vs_aplicado_cuotas` (salida de ejecutar_auditoria_cartera)."""
    out: list[int] = []
    for r in rows:
        pid = int(r["prestamo_id"])
        for c in r.get("controles", []):
            if c.get("codigo") == "total_pagado_vs_aplicado_cuotas":
                out.append(pid)
                break
    return sorted(set(out))
