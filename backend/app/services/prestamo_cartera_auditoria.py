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
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import bindparam, text
from sqlalchemy.orm import Session

from app.models.configuracion import Configuracion
from app.services.auditoria_cartera_revision_service import pares_ultimo_evento_marcar_ok
from app.services.cuota_estado import clasificar_estado_cuota, hoy_negocio
from app.utils.cedula_almacenamiento import (
    max_aprobados_permitidos_por_prefijo,
    normalizar_cedula_almacenamiento,
    normalizar_cedula_clave_cupo,
    prefijo_politica_cupo_aprobados,
)

logger = logging.getLogger(__name__)

_TOL = Decimal("0.02")
CFG_ULTIMA = "auditoria_cartera_ultima_ejecucion"
CFG_RESUMEN = "auditoria_cartera_ultima_resumen"

# Identificador estable de la definicion de controles en este modulo (17 reglas en add_control).
# Subir solo cuando se agregue, quite o renombre un control en la auditoria de cartera.
AUDITORIA_CARTERA_REGLAS_VERSION = "23-control5-excluir-sufijo-ap-2026-04-09"

_ESTADOS_FILAS_PRESTAMO_PERMITIDOS = frozenset({"APROBADO", "LIQUIDADO"})


def normalizar_estados_filas_prestamo(
    estados_filas_prestamo: Optional[tuple[str, ...]],
) -> tuple[str, ...]:
    """
    Estados permitidos para acotar el universo de filas de prestamo en auditoria de cartera.
    None = ('APROBADO','LIQUIDADO') (comportamiento historico).
    """
    if estados_filas_prestamo is None:
        return ("APROBADO", "LIQUIDADO")
    out: list[str] = []
    for raw in estados_filas_prestamo:
        e = (raw or "").strip().upper()
        if e in _ESTADOS_FILAS_PRESTAMO_PERMITIDOS and e not in out:
            out.append(e)
    if not out:
        raise ValueError(
            "estados_filas_prestamo vacio o invalido: use APROBADO y/o LIQUIDADO"
        )
    return tuple(out)


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


def _sql_fragment_pago_cuenta_para_control5_duplicado_fecha_monto(alias: str) -> str:
    """
    Condicion (para AND ...) de filas que cuentan en el control pagos_mismo_dia_monto.
    Excluye: pagos no operativos, Visto (bit), y documentos con sufijo _A#### / _P#### (misma convencion
    que aplicar_visto_control5_duplicado_fecha_monto: recibo partido en varias cuotas / carga masiva).
    """
    a = alias.strip()
    if not a.replace("_", "").isalnum():
        raise ValueError("alias SQL invalido")
    excl_estado = _sql_fragment_pago_excluido_cartera(a)
    return f"""(
      NOT ({excl_estado})
      AND NOT COALESCE({a}.excluir_control_pagos_mismo_dia_monto, false)
      AND NOT (TRIM(COALESCE({a}.numero_documento, '')) ~* '_[ap][0-9]{{4}}$')
    )"""


def _dec(x: Any) -> Decimal:
    if x is None:
        return Decimal("0")
    if isinstance(x, Decimal):
        return x
    return Decimal(str(x))


def totales_pagos_operativos_y_aplicado_cuotas_prestamo(
    db: Session, prestamo_id: int
) -> tuple[Decimal, Decimal]:
    """
    Suma `monto_pagado` de pagos operativos y suma `monto_aplicado` vía cuota_pagos,
    mismo criterio de exclusion que la auditoria de cartera (anulados, reversados, etc.).
    """
    excl_pg = _sql_fragment_pago_excluido_cartera("pg")
    q = text(
        f"""
        SELECT
          COALESCE(
            (SELECT SUM(pg.monto_pagado) FROM pagos pg
             WHERE pg.prestamo_id = :pid AND NOT ({excl_pg})), 0),
          COALESCE(
            (SELECT SUM(cp.monto_aplicado)
             FROM cuotas cu
             JOIN cuota_pagos cp ON cp.cuota_id = cu.id
             JOIN pagos pg ON pg.id = cp.pago_id
             WHERE cu.prestamo_id = :pid AND NOT ({excl_pg})), 0)
        """
    )
    row = db.execute(q, {"pid": prestamo_id}).fetchone()
    if not row:
        return Decimal("0"), Decimal("0")
    return _dec(row[0]), _dec(row[1])


def prestamo_cuadrado_pagos_operativos_vs_aplicado(
    db: Session, prestamo_id: int, tol: Optional[Decimal] = None
) -> bool:
    """True si |suma pagos operativos - suma aplicado| <= tolerancia (defecto 0.02 USD)."""
    t = tol if tol is not None else _TOL
    sp, sa = totales_pagos_operativos_y_aplicado_cuotas_prestamo(db, prestamo_id)
    return abs(sp - sa) <= t


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


def _prestamo_ids_alerta_por_control_desde_pares(
    pares: set[tuple[int, str]],
    *,
    excluir_marcar_ok: bool,
    ok_pairs: set[tuple[int, str]],
) -> dict[str, list[int]]:
    """Mapa control -> prestamo_ids (unicos ordenados), respetando exclusion MARCAR_OK si aplica."""
    eff = pares
    if excluir_marcar_ok:
        eff = {(p, c) for p, c in pares if (p, c) not in ok_pairs}
    by_c: dict[str, list[int]] = {}
    for p, c in eff:
        cod = str(c or "").strip()
        if not cod:
            continue
        by_c.setdefault(cod, []).append(int(p))
    return {k: sorted(set(v)) for k, v in by_c.items()}


def ejecutar_auditoria_cartera(
    db: Session,
    *,
    solo_con_alerta: bool = True,
    prestamo_id: Optional[int] = None,
    cedula_contiene: Optional[str] = None,
    skip: int = 0,
    limit: Optional[int] = None,
    incluir_filas: bool = True,
    incluir_mapa_ids_por_control: bool = False,
    excluir_marcar_ok: bool = False,
    codigo_control: Optional[str] = None,
    estados_filas_prestamo: Optional[tuple[str, ...]] = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """
    Evalua prestamos en estados operativos. Retorna (filas, resumen).
    Solo se devuelven prestamos con al menos un control en alerta SI.
    En cada fila, `controles` solo incluye entradas con alerta SI (no se exponen los NO).
    Param solo_con_alerta: reservado por compatibilidad con la API; no altera el resultado.
    prestamo_id / cedula_contiene: acotan que prestamos se evaluan (misma logica de controles sobre el universo completo).
    skip / limit: paginacion sobre la lista de prestamos con alerta (despues de filtrar por prestamo/cedula).
    incluir_filas: si False, no construye la lista de prestamos (ahorra memoria); resumen y conteos igual.
    incluir_mapa_ids_por_control: si True, meta incluye `prestamo_ids_alerta_por_control` (codigo -> ids) para
        evitar una segunda pasada con filas completas (p. ej. POST corregir antes de reaplicar cascada).
    excluir_marcar_ok: si True, omite solo pares con ultimo MARCAR_OK en bitacora (aceptacion); el resto de filas
        desaparecen del listado unicamente cuando el motor deja de marcar SI. Job 03:00 y persistencia usan False.
    codigo_control: si se indica, solo entran prestamos con ese control en SI; la paginacion skip/limit aplica a esa lista.
        Los conteos por control en meta siguen siendo globales (para el desplegable de filtros).
    estados_filas_prestamo: acota el SELECT inicial de prestamos (p.ej. solo LIQUIDADO). None = APROBADO+LIQUIDADO.
    """
    _ = solo_con_alerta

    hoy = hoy_negocio()
    estados_univ = normalizar_estados_filas_prestamo(estados_filas_prestamo)

    rows_p = db.execute(
        text(
            """
            SELECT p.id, p.cliente_id, p.cedula, p.nombres, p.estado, p.numero_cuotas, p.total_financiamiento,
                   c.email AS cliente_email, c.cedula AS cliente_cedula
            FROM prestamos p
            JOIN clientes c ON c.id = p.cliente_id
            WHERE p.estado IN :ests
            ORDER BY p.id
            """
        ).bindparams(bindparam("ests", expanding=True)),
        {"ests": list(estados_univ)},
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
            "universo_estados_prestamo": list(estados_univ),
        }
        return [], meta

    prestamo_ids = [int(r[0]) for r in rows_p]

    # Cedulas con mas prestamos APROBADO de los permitidos por prefijo (alineado a cupo E/V=1, J=5).
    _j_max_dup = max_aprobados_permitidos_por_prefijo("J")
    _ev_max_dup = max_aprobados_permitidos_por_prefijo("E")
    if _j_max_dup is None:
        _j_max_dup = 5
    if _ev_max_dup is None:
        _ev_max_dup = 1
    dup_cedulas_rows = db.execute(
        text(
            """
            WITH agr AS (
              SELECT UPPER(TRIM(BOTH FROM cedula)) AS ced_norm, COUNT(*)::int AS n
              FROM prestamos
              WHERE estado = 'APROBADO'
              GROUP BY UPPER(TRIM(BOTH FROM cedula))
            )
            SELECT ced_norm FROM agr
            WHERE ced_norm IS NOT NULL
              AND TRIM(BOTH FROM ced_norm::text) <> ''
              AND (
                (SUBSTRING(agr.ced_norm FROM 1 FOR 1) = 'J' AND agr.n > :j_max)
                OR (SUBSTRING(agr.ced_norm FROM 1 FOR 1) <> 'J' AND agr.n > :ev_max)
              )
            """
        ),
        {"j_max": _j_max_dup, "ev_max": _ev_max_dup},
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
    ctrl5_cuenta = _sql_fragment_pago_cuenta_para_control5_duplicado_fecha_monto("p")

    # Pagos duplicados mismo dia y monto (posible fraude / doble registro); excluye anulados/reversados,
    # Visto (excluir_control_pagos_mismo_dia_monto) y numero_documento con sufijo _A#### / _P#### (recibo en varias cuotas).
    # Alcance: mismo prestamo + fecha calendario + monto (no sustituye unicidad global de numero_documento).
    dup_pagos_rows = db.execute(
        text(
            f"""
            SELECT DISTINCT prestamo_id
            FROM (
              SELECT p.prestamo_id, CAST(p.fecha_pago AS date) AS fd, p.monto_pagado, COUNT(*) AS cnt
              FROM pagos p
              WHERE p.prestamo_id IS NOT NULL AND ({ctrl5_cuenta})
              GROUP BY p.prestamo_id, CAST(p.fecha_pago AS date), p.monto_pagado
              HAVING COUNT(*) > 1
            ) t
            """
        )
    ).fetchall()
    prestamos_pagos_duplicados = {int(r[0]) for r in dup_pagos_rows if r[0] is not None}

    # Misma huella funcional que el indice ux_pagos_fingerprint_activos (prestamo, dia, monto, ref_norm).
    # Complementario al control 5 (fecha+monto sin ref_norm en el agrupamiento); colisiones por ref copiado
    # suelen corregirse en origen o con sufijos en carga masiva (ver auditoria UI control 16).
    dup_huella_rows = db.execute(
        text(
            f"""
            SELECT DISTINCT prestamo_id
            FROM (
              SELECT p.prestamo_id, COUNT(*) AS cnt
              FROM pagos p
              WHERE p.prestamo_id IS NOT NULL
                AND NOT {excl_p}
                AND TRIM(COALESCE(p.ref_norm, '')) <> ''
              GROUP BY
                p.prestamo_id,
                CAST(p.fecha_pago AS date),
                p.monto_pagado,
                TRIM(COALESCE(p.ref_norm, ''))
              HAVING COUNT(*) > 1
            ) t
            """
        )
    ).fetchall()
    prestamos_huella_funcional_dup = {int(r[0]) for r in dup_huella_rows if r[0] is not None}

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

    counts_aprobado_clave: Counter[str] = Counter()
    for _r in rows_p:
        if str(_r[4] or "").strip() != "APROBADO":
            continue
        _ck = normalizar_cedula_clave_cupo(_r[2] or "")
        if _ck:
            counts_aprobado_clave[_ck] += 1

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
            "Cedula cliente vs prestamo (API alinea al guardar)",
            ced_mismatch,
            f"Prestamo={nc_p or cedula_p} Cliente={nc_c or cedula_c}" if ced_mismatch == "SI" else "Coinciden",
        )

        ced_norm_upper = (cedula_p or "").strip().upper()
        dup_prest = "SI" if ced_norm_upper in dup_cedulas else "NO"
        add_control(
            "prestamos_duplicados_misma_cedula",
            "Prestamos APROBADO misma cedula por encima del cupo (E/V max 1, J max 5)",
            dup_prest,
            (
                "Mas APROBADOS con esta cedula que el permitido (E/V mas de 1, J mas de 5)"
                if dup_prest == "SI"
                else "En cupo: hasta 1 APROBADO (E/V) o hasta 5 (J) con la misma cedula normalizada"
            ),
        )

        if estado_p == "APROBADO":
            clave_cupo = normalizar_cedula_clave_cupo(cedula_p)
            pref_cupo = prefijo_politica_cupo_aprobados(clave_cupo)
            max_cupo = max_aprobados_permitidos_por_prefijo(pref_cupo)
            if max_cupo is None or not clave_cupo:
                cupo_si = "SI"
                cupo_det = (
                    "Cedula vacia o prefijo no permitido (solo E, V, J tras normalizar guiones y espacios)."
                )
            else:
                n_clave = int(counts_aprobado_clave.get(clave_cupo, 0))
                cupo_si = "SI" if n_clave > max_cupo else "NO"
                cupo_det = (
                    f"Clave={clave_cupo} prefijo={pref_cupo} APROBADOS_misma_clave={n_clave} max_permitido={max_cupo}"
                    if cupo_si == "SI"
                    else f"OK clave={clave_cupo} n={n_clave} max={max_cupo}"
                )
        else:
            cupo_si = "NO"
            cupo_det = "Solo aplica a prestamos APROBADO"
        add_control(
            "cupo_cedula_aprobados_politica",
            "Cupo cedula: E/V max 1 APROBADO, J max 5 APROBADO, prefijos validos E V J",
            cupo_si,
            cupo_det,
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

        dup_huella = "SI" if pid in prestamos_huella_funcional_dup else "NO"
        add_control(
            "pagos_huella_funcional_duplicada",
            "Pagos con misma huella funcional (fecha, monto, ref_norm)",
            dup_huella,
            (
                "Dos o mas pagos activos: mismo prestamo, dia, monto y ref_norm (colision de indice; "
                "p. ej. BNC/REF y REF sin prefijo)."
                if dup_huella == "SI"
                else "Sin colision de huella funcional"
            ),
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
        estado_upper = (estado_p or "").strip().upper()
        es_liquidado = estado_upper == "LIQUIDADO"
        # Alerta SI solo en LIQUIDADO: en APROBADO el descuadre total es referencial (cartera viva).
        alert_ap = "SI" if es_liquidado and diff_ap > _TOL else "NO"
        if es_liquidado:
            detalle_ap = (
                f"Suma pagos(operativos)={sp} aplicado(desde pagos operativos)={sa} diff={diff_ap}. "
                f"Es total del prestamo; si diff es grande, revisar pagos donde monto_pagado <> sum(cuota_pagos) "
                f"por pago_id (el control 15 marca saldo sin aplicar por pago)."
                if alert_ap == "SI"
                else f"Cuadrado USD tol={_TOL} (diff={diff_ap}); excluye anulados/reversados/duplicado en sumas"
            )
        else:
            detalle_ap = (
                f"Solo LIQUIDADO marca SI: este credito esta en {estado_upper or '(sin estado)'}; "
                f"diff referencial={diff_ap} (pagos op={sp}, aplicado={sa})."
            )
        add_control(
            "total_pagado_vs_aplicado_cuotas",
            "Total pagos vs total aplicado a cuotas (cuota_pagos); alerta solo si LIQUIDADO",
            alert_ap,
            detalle_ap,
        )

        if (estado_p or "").strip().upper() == "LIQUIDADO":
            liq_des = "SI" if diff_ap > _TOL else "NO"
            if liq_des == "SI":
                neto = sp - sa
                liq_det = (
                    f"LIQUIDADO con suma operativa pagos={sp} y aplicado cuotas={sa} (diff={diff_ap} USD). "
                    f"Neto operativo-aplicado={neto}. Revisar BS mal cargados como USD, pagos duplicados, "
                    f"filas sin anular o aplicacion en cuota_pagos (controles 7 y 15)."
                )
            else:
                liq_det = f"Cuadrado con tolerancia {_TOL} (diff={diff_ap})."
        else:
            liq_des = "NO"
            liq_det = "Solo aplica cuando el prestamo esta en LIQUIDADO."
        add_control(
            "liquidado_descuadre_total_pagos_vs_aplicado_cuotas",
            "LIQUIDADO con descuadre: total pagos operativos vs aplicado a cuotas",
            liq_des,
            liq_det,
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

    mapa_ids_por_control: Optional[dict[str, list[int]]] = None
    if incluir_mapa_ids_por_control:
        mapa_ids_por_control = _prestamo_ids_alerta_por_control_desde_pares(
            pares_alerta_si,
            excluir_marcar_ok=excluir_marcar_ok,
            ok_pairs=ok_pairs,
        )

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
            "universo_estados_prestamo": list(estados_univ),
        }
        if mapa_ids_por_control is not None:
            meta["prestamo_ids_alerta_por_control"] = mapa_ids_por_control
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
        "universo_estados_prestamo": list(estados_univ),
    }
    if mapa_ids_por_control is not None:
        meta["prestamo_ids_alerta_por_control"] = mapa_ids_por_control
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


def prestamos_ids_alerta_pagos_sin_aplicacion_cuotas(rows: list[dict[str, Any]]) -> list[int]:
    """IDs de prestamos con control SI `pagos_sin_aplicacion_a_cuotas`."""
    out: list[int] = []
    for r in rows:
        pid = int(r["prestamo_id"])
        for c in r.get("controles", []):
            if c.get("codigo") == "pagos_sin_aplicacion_a_cuotas":
                out.append(pid)
                break
    return sorted(set(out))


def listar_pagos_sin_aplicacion_cuotas_por_prestamo(db: Session, prestamo_id: int) -> list[dict[str, Any]]:
    """
    Detalle del control `pagos_sin_aplicacion_a_cuotas` para un prestamo: pagos operativos
    sin filas en cuota_pagos o con sum(monto_aplicado) < monto_pagado - 0.02 USD.
    """
    excl = _sql_fragment_pago_excluido_cartera("p")
    sql = text(
        f"""
        SELECT
          p.id AS pago_id,
          p.prestamo_id,
          p.fecha_pago,
          p.monto_pagado,
          COALESCE(SUM(cp.monto_aplicado), 0) AS sum_monto_aplicado,
          CASE
            WHEN NOT EXISTS (SELECT 1 FROM cuota_pagos cp0 WHERE cp0.pago_id = p.id)
            THEN 'sin_filas_cuota_pagos'
            ELSE 'sum_aplicado_menor_que_monto_menos_tol'
          END AS motivo
        FROM pagos p
        LEFT JOIN cuota_pagos cp ON cp.pago_id = p.id
        WHERE p.prestamo_id = :pid
          AND p.prestamo_id IS NOT NULL
          AND p.monto_pagado > 0
          AND NOT ({excl})
        GROUP BY p.id, p.prestamo_id, p.fecha_pago, p.monto_pagado
        HAVING
          NOT EXISTS (SELECT 1 FROM cuota_pagos cp1 WHERE cp1.pago_id = p.id)
          OR COALESCE(SUM(cp.monto_aplicado), 0) < (p.monto_pagado::numeric - 0.02)
        ORDER BY p.fecha_pago NULLS LAST, p.id
        """
    )
    rows = db.execute(sql, {"pid": prestamo_id}).fetchall()
    out: list[dict[str, Any]] = []
    for row in rows:
        pago_id = int(row[0])
        prid = int(row[1]) if row[1] is not None else prestamo_id
        fp = row[2]
        mp = _dec(row[3])
        sma = _dec(row[4])
        motivo = str(row[5] or "")
        saldo = mp - sma
        fp_s: Optional[str] = None
        if fp is not None:
            if hasattr(fp, "isoformat"):
                fp_s = fp.isoformat()
            else:
                fp_s = str(fp)
        out.append(
            {
                "pago_id": pago_id,
                "prestamo_id": prid,
                "fecha_pago": fp_s,
                "monto_pagado": float(mp),
                "sum_monto_aplicado_cuotas": float(sma),
                "saldo_sin_aplicar_usd": float(saldo),
                "motivo": motivo,
            }
        )
    return out
