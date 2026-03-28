"""
Auditoria de cartera por prestamo: controles desde tablas reales (prestamos, clientes, cuotas, pagos, cuota_pagos).

Independencia del motor (objetivo): los SI/NO se calculan solo con reglas deterministicas sobre la BD.
La bitacora `auditoria_cartera_revision` (MARCAR_OK) no altera esos calculos; solo puede filtrarse en
GET chequeos/resumen cuando `excluir_marcar_ok=true` (vista operativa). Job 03:00, POST ejecutar y POST
corregir deben llamar siempre con `excluir_marcar_ok=False` para persistir KPIs objetivos en `configuracion`.

Regla de negocio (cola operativa con `excluir_marcar_ok=true`): un par (prestamo, control) deja de mostrarse
como alarma pendiente solo si (1) existe aceptacion documentada con ultimo evento MARCAR_OK en bitacora, o
(2) el motor ya no evalua ese control en SI (causa raiz corregida en datos; no hay otro camino de ocultacion).

Totales pagos/aplicado en USD: solo pagos operativos (excluye anulados, reversados, duplicados declarados,
cancelado/rechazado). Comparacion agregada con tolerancia 0.02 USD; conversion BS->USD fila a fila sin tolerancia
(2 decimales). Pagos en BS alertan si falta `tasas_cambio_diaria` para la fecha del pago.

La lista de alertas es orientativa; debe revisarla un humano. La corrida automatica (03:00 America/Caracas)
alinea antes `cuotas.estado` con `clasificar_estado_cuota`, luego evalua y actualiza metadatos en
`configuracion`; el GET del API recalcula en tiempo real para reflejar la BD actual.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.models.configuracion import Configuracion
from app.services.auditoria_cartera_revision_service import pares_ultimo_evento_marcar_ok
from app.services.cuota_estado import clasificar_estado_cuota, hoy_negocio
from app.utils.cedula_almacenamiento import normalizar_cedula_almacenamiento

logger = logging.getLogger(__name__)

_TOL = Decimal("0.02")
CFG_ULTIMA = "auditoria_cartera_ultima_ejecucion"
CFG_RESUMEN = "auditoria_cartera_ultima_resumen"

# Identificador estable de la definicion de controles en este modulo (14 reglas en add_control).
# Subir solo cuando se agregue, quite o renombre un control en la auditoria de cartera.
AUDITORIA_CARTERA_REGLAS_VERSION = "14controles-2026-03-27"


def _sql_fragment_pago_excluido_cartera(alias: str) -> str:
    """
    Pagos que no deben contar en totales ni en coherencia BS/USD (anulados, reversados, duplicados, etc.).
    `alias` es el identificador SQL de la tabla pagos en la consulta (ej. p, pg).
    """
    a = alias.strip()
    if not a.replace("_", "").isalnum():
        raise ValueError("alias SQL invalido")
    return f"""(
      UPPER(COALESCE({a}.estado, '')) IN ('ANULADO_IMPORT', 'DUPLICADO', 'CANCELADO', 'RECHAZADO', 'REVERSADO')
      OR UPPER(COALESCE({a}.estado, '')) LIKE '%ANUL%'
      OR UPPER(COALESCE({a}.estado, '')) LIKE '%REVERS%'
      OR LOWER(COALESCE({a}.estado, '')) IN ('cancelado', 'rechazado')
    )"""


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
    conteos_por_control: Optional[dict[str, Any]] = None,
    reglas_version: Optional[str] = None,
    commit: bool = True,
) -> None:
    """Guarda hora y resumen de la ultima corrida (job 03:00 o manual)."""
    now = datetime.now(timezone.utc).isoformat()
    payload: dict[str, Any] = {
        "ultima_ejecucion_utc": now,
        "prestamos_evaluados": total_evaluados,
        "prestamos_con_alerta": con_alerta,
    }
    if conteos_por_control is not None:
        payload["conteos_por_control"] = conteos_por_control
    if reglas_version:
        payload["reglas_version"] = reglas_version
    # Siempre: KPIs guardados = motor sobre tablas reales, sin aplicar revision humana MARCAR_OK.
    payload["criterio_evaluacion_persistido"] = "motor_tablas_sin_excepciones_bitacora"
    resumen = json.dumps(payload, ensure_ascii=False)
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


def _cedula_prestamo_coincide_fragmento(row_prestamo: Any, fragmento: str) -> bool:
    """True si el fragmento (mayusculas, sin espacios) aparece en cedula del prestamo (normalizada o cruda)."""
    q = fragmento.strip().upper().replace(" ", "")
    if not q:
        return True
    raw = (row_prestamo[2] or "").strip()
    nc = (normalizar_cedula_almacenamiento(raw) or raw).upper().replace(" ", "")
    raw_u = raw.upper().replace(" ", "")
    return q in nc or q in raw_u


def _filtrar_filas_marcar_ok(
    rows: list[dict[str, Any]],
    ok_pairs: set[tuple[int, str]],
) -> list[dict[str, Any]]:
    if not ok_pairs:
        return rows
    dedup: list[dict[str, Any]] = []
    for row in rows:
        pid = int(row["prestamo_id"])
        ctrls = [
            c
            for c in row.get("controles", [])
            if (pid, str(c.get("codigo") or "").strip()) not in ok_pairs
        ]
        if ctrls:
            new_row = dict(row)
            new_row["controles"] = ctrls
            dedup.append(new_row)
    return dedup


def _recompute_conteos_desde_filas(rows: list[dict[str, Any]]) -> dict[str, int]:
    cc: dict[str, int] = {}
    for row in rows:
        for c in row.get("controles", []):
            cod = str(c.get("codigo") or "").strip()
            if cod:
                cc[cod] = cc.get(cod, 0) + 1
    return cc


def _ajuste_conteos_sin_filas(
    control_counts: dict[str, int],
    pares_alerta_si: set[tuple[int, str]],
    ok_pairs: set[tuple[int, str]],
) -> tuple[dict[str, int], int]:
    inter = {(p, c) for p, c in pares_alerta_si if (p, c) in ok_pairs}
    cc = dict(control_counts)
    for _p, c in inter:
        cc[c] = max(0, cc.get(c, 0) - 1)
    pids_restantes = {p for p, c in pares_alerta_si if (p, c) not in ok_pairs}
    return cc, len(pids_restantes)


def ejecutar_auditoria_cartera(
    db: Session,
    *,
    solo_con_alerta: bool = True,
    prestamo_id: Optional[int] = None,
    cedula_contiene: Optional[str] = None,
    skip: int = 0,
    limit: Optional[int] = None,
    incluir_filas: bool = True,
    excluir_marcar_ok: bool = False,
    codigo_control: Optional[str] = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Evalua prestamos en estados operativos. Retorna (filas, resumen).
    Solo se devuelven prestamos con al menos un control en alerta SI.
    En cada fila, `controles` solo incluye entradas con alerta SI (no se exponen los NO).
    Param solo_con_alerta: reservado por compatibilidad con la API; no altera el resultado.
    prestamo_id / cedula_contiene: acotan que prestamos se evaluan (misma logica de controles sobre el universo completo).
    skip / limit: paginacion sobre la lista de prestamos con alerta (despues de filtrar por prestamo/cedula).
    incluir_filas: si False, no construye la lista de prestamos (ahorra memoria); resumen y conteos igual.
    excluir_marcar_ok: si True, omite solo pares con ultimo MARCAR_OK en bitacora (aceptacion); el resto de filas
        desaparecen del listado unicamente cuando el motor deja de marcar SI. Job 03:00 y persistencia usan False.
    codigo_control: si se indica, solo entran prestamos con ese control en SI; la paginacion skip/limit aplica a esa lista.
        Los conteos por control en meta siguen siendo globales (para el desplegable de filtros).
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

    if prestamo_id is not None:
        rows_p = [r for r in rows_p if int(r[0]) == prestamo_id]

    if cedula_contiene and str(cedula_contiene).strip():
        rows_p = [r for r in rows_p if _cedula_prestamo_coincide_fragmento(r, str(cedula_contiene))]

    if not rows_p:
        meta: dict[str, Any] = {
            "prestamos_evaluados": 0,
            "prestamos_con_alerta": 0,
            "prestamos_listados_total": 0,
            "prestamos_listados": 0,
            "conteos_por_control": {},
            "fecha_referencia": str(hoy),
            "pagina_skip": max(0, skip),
            "pagina_limit": limit,
            "reglas_version": AUDITORIA_CARTERA_REGLAS_VERSION,
            "excluye_marcar_ok": excluir_marcar_ok,
            "filtrado_por_codigo_control": (codigo_control or "").strip() or None,
        }
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

    excl_p = _sql_fragment_pago_excluido_cartera("p")
    excl_pg = _sql_fragment_pago_excluido_cartera("pg")

    # Pagos duplicados mismo dia y monto (posible fraude / doble registro); excluye anulados/reversados
    dup_pagos_rows = db.execute(
        text(
            f"""
            SELECT DISTINCT prestamo_id
            FROM (
              SELECT p.prestamo_id, CAST(p.fecha_pago AS date) AS fd, p.monto_pagado, COUNT(*) AS cnt
              FROM pagos p
              WHERE p.prestamo_id IS NOT NULL AND NOT {excl_p}
              GROUP BY p.prestamo_id, CAST(p.fecha_pago AS date), p.monto_pagado
              HAVING COUNT(*) > 1
            ) t
            """
        )
    ).fetchall()
    prestamos_pagos_duplicados = {int(r[0]) for r in dup_pagos_rows if r[0] is not None}

    # Pagos con monto no positivo (solo pagos operativos)
    bad_monto_rows = db.execute(
        text(
            f"""
            SELECT DISTINCT prestamo_id FROM pagos p
            WHERE p.prestamo_id IS NOT NULL AND p.monto_pagado <= 0 AND NOT {excl_p}
            """
        )
    ).fetchall()
    prestamos_monto_mal = {int(r[0]) for r in bad_monto_rows if r[0] is not None}

    # Pago en BS sin fila en tasas_cambio_diaria para la fecha del pago (bloqueo operativo / auditoria)
    bs_sin_tasa_rows = db.execute(
        text(
            f"""
            SELECT DISTINCT p.prestamo_id
            FROM pagos p
            WHERE p.prestamo_id IS NOT NULL
              AND UPPER(COALESCE(p.moneda_registro, '')) = 'BS'
              AND NOT {excl_p}
              AND NOT EXISTS (
                SELECT 1 FROM tasas_cambio_diaria t
                WHERE t.fecha = CAST(p.fecha_pago AS date)
              )
            """
        )
    ).fetchall()
    prestamos_bs_sin_tasa_diaria = {int(r[0]) for r in bs_sin_tasa_rows if r[0] is not None}

    # BS: monto_pagado (USD) debe cuadrar con monto_bs / tasa almacenados, sin tolerancia (2 decimales)
    bs_conv_mal_rows = db.execute(
        text(
            f"""
            SELECT DISTINCT p.prestamo_id
            FROM pagos p
            WHERE p.prestamo_id IS NOT NULL
              AND UPPER(COALESCE(p.moneda_registro, '')) = 'BS'
              AND NOT {excl_p}
              AND (
                p.monto_bs_original IS NULL
                OR p.tasa_cambio_bs_usd IS NULL
                OR p.tasa_cambio_bs_usd = 0
                OR ROUND((p.monto_bs_original / NULLIF(p.tasa_cambio_bs_usd, 0))::numeric, 2)
                   <> ROUND(p.monto_pagado::numeric, 2)
              )
            """
        )
    ).fetchall()
    prestamos_bs_conversion_incoherente = {int(r[0]) for r in bs_conv_mal_rows if r[0] is not None}

    # Pago operativo con monto > 0 sin filas en cuota_pagos o con saldo sin aplicar > tolerancia USD
    huerfanos_rows = db.execute(
        text(
            f"""
            SELECT DISTINCT p.prestamo_id
            FROM pagos p
            WHERE p.prestamo_id IS NOT NULL
              AND p.monto_pagado > 0
              AND NOT {excl_p}
              AND (
                NOT EXISTS (SELECT 1 FROM cuota_pagos cp WHERE cp.pago_id = p.id)
                OR COALESCE((
                     SELECT SUM(cp2.monto_aplicado) FROM cuota_pagos cp2 WHERE cp2.pago_id = p.id
                   ), 0) < (p.monto_pagado::numeric - 0.02)
              )
            """
        )
    ).fetchall()
    prestamos_pagos_huerfanos = {int(r[0]) for r in huerfanos_rows if r[0] is not None}

    tot_sql = (
        text(
            f"""
            SELECT p.id,
              COALESCE(sp.s, 0) AS sum_pagos,
              COALESCE(sa.s, 0) AS sum_aplicado,
              COALESCE(sc.s, 0) AS sum_cuotas
            FROM prestamos p
            LEFT JOIN LATERAL (
              SELECT SUM(pg.monto_pagado) AS s FROM pagos pg
              WHERE pg.prestamo_id = p.id AND NOT {excl_pg}
            ) sp ON true
            LEFT JOIN LATERAL (
              SELECT SUM(cp.monto_aplicado) AS s
              FROM cuotas cu
              JOIN cuota_pagos cp ON cp.cuota_id = cu.id
              JOIN pagos pg ON pg.id = cp.pago_id
              WHERE cu.prestamo_id = p.id AND NOT {excl_pg}
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
    control_counts: dict[str, int] = {}
    pares_alerta_si: set[tuple[int, str]] = set()

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
            "Varios prestamos APROBADO misma cedula (duplicidad activa)",
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
            (
                f"Suma pagos(operativos)={sp} aplicado(desde pagos operativos)={sa} diff={diff_ap}"
                if alert_ap == "SI"
                else f"Cuadrado USD tol={_TOL} (diff={diff_ap}); excluye anulados/reversados/duplicado en sumas"
            ),
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

        bs_st = "SI" if pid in prestamos_bs_sin_tasa_diaria else "NO"
        add_control(
            "pago_bs_sin_tasa_cambio_diaria",
            "Pago en bolivares sin tasa oficial del dia (tasas_cambio_diaria)",
            bs_st,
            "Falta fila en tasas_cambio_diaria para la fecha del pago (BS)" if bs_st == "SI" else "OK",
        )

        bs_cv = "SI" if pid in prestamos_bs_conversion_incoherente else "NO"
        add_control(
            "conversion_bs_a_usd_incoherente",
            "Conversion BS a USD incoherente (cero tolerancia en 2 decimales)",
            bs_cv,
            "monto_pagado no cuadra con monto_bs_original/tasa_cambio_bs_usd o faltan campos BS"
            if bs_cv == "SI"
            else "OK",
        )

        hrf = "SI" if pid in prestamos_pagos_huerfanos else "NO"
        add_control(
            "pagos_sin_aplicacion_a_cuotas",
            "Pagos operativos sin aplicacion a cuotas o con saldo sin aplicar",
            hrf,
            "Revisar cuota_pagos: cargar aplicacion o corregir montos (tol USD 0.02)"
            if hrf == "SI"
            else "OK",
        )

        controles_si = [c for c in controles if c.get("alerta") == "SI"]
        tiene_alerta = bool(controles_si)
        if tiene_alerta:
            con_alerta_count += 1

        if not controles_si:
            continue

        for c in controles_si:
            cod = str(c.get("codigo") or "")
            if cod:
                control_counts[cod] = control_counts.get(cod, 0) + 1
                pares_alerta_si.add((pid, cod))

        if incluir_filas:
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

    ok_pairs: set[tuple[int, str]] = set()
    if excluir_marcar_ok:
        ok_pairs = pares_ultimo_evento_marcar_ok(db, prestamo_ids)

    if incluir_filas and excluir_marcar_ok:
        out = _filtrar_filas_marcar_ok(out, ok_pairs)
        control_counts_eff = _recompute_conteos_desde_filas(out)
        con_alerta_eff = len(out)
    elif incluir_filas:
        control_counts_eff = dict(control_counts)
        con_alerta_eff = con_alerta_count
    elif excluir_marcar_ok:
        control_counts_eff, con_alerta_eff = _ajuste_conteos_sin_filas(
            control_counts, pares_alerta_si, ok_pairs
        )
    else:
        control_counts_eff = dict(control_counts)
        con_alerta_eff = con_alerta_count

    conteos_globales_meta = dict(control_counts_eff)
    codigo_f = (codigo_control or "").strip() or None

    if incluir_filas and codigo_f:
        out = [
            {
                **r,
                "controles": [
                    c
                    for c in r.get("controles", [])
                    if str(c.get("codigo") or "").strip() == codigo_f
                ],
            }
            for r in out
            if any(
                str(c.get("codigo") or "").strip() == codigo_f
                for c in r.get("controles", [])
            )
        ]
        con_alerta_eff = len(out)
    elif not incluir_filas and codigo_f:
        pares_cod = {(p, c) for p, c in pares_alerta_si if c == codigo_f}
        if excluir_marcar_ok:
            pares_cod -= {(p, c) for p, c in pares_cod if (p, c) in ok_pairs}
        con_alerta_eff = len({p for p, _ in pares_cod})

    listados_total = con_alerta_eff

    if not incluir_filas:
        meta = {
            "prestamos_evaluados": len(rows_p),
            "prestamos_con_alerta": con_alerta_eff,
            "prestamos_listados_total": listados_total,
            "prestamos_listados": 0,
            "conteos_por_control": conteos_globales_meta,
            "fecha_referencia": str(hoy),
            "pagina_skip": 0,
            "pagina_limit": None,
            "reglas_version": AUDITORIA_CARTERA_REGLAS_VERSION,
            "excluye_marcar_ok": excluir_marcar_ok,
            "filtrado_por_codigo_control": codigo_f,
        }
        return [], meta

    skip_clamped = max(0, int(skip))
    page = out[skip_clamped:] if skip_clamped else out
    if limit is not None:
        page = page[: int(limit)]

    meta = {
        "prestamos_evaluados": len(rows_p),
        "prestamos_con_alerta": con_alerta_eff,
        "prestamos_listados_total": listados_total,
        "prestamos_listados": len(page),
        "conteos_por_control": conteos_globales_meta,
        "fecha_referencia": str(hoy),
        "pagina_skip": skip_clamped,
        "pagina_limit": limit,
        "reglas_version": AUDITORIA_CARTERA_REGLAS_VERSION,
        "excluye_marcar_ok": excluir_marcar_ok,
        "filtrado_por_codigo_control": codigo_f,
    }
    return page, meta


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
