#!/usr/bin/env python3
"""Second-wave splits: reportados_helpers, crud_routes."""
from __future__ import annotations

from pathlib import Path

COBROS = Path(__file__).resolve().parents[1] / "app" / "api" / "v1" / "endpoints" / "cobros"
PAGOS = Path(__file__).resolve().parents[1] / "app" / "api" / "v1" / "endpoints" / "pagos"


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines(keepends=True)


def monolith_header(lines: list[str], end: int = 108) -> str:
    return "".join(lines[0:end])


def write_module(path: Path, doc: str, prefix: str, body: list[str]) -> None:
    path.write_text(f'"""{doc}"""\n' + prefix + "".join(body), encoding="utf-8")
    print(f"  wrote {path.name} ({len(body)} body lines)")


def split_reportados_helpers() -> None:
    backup = COBROS / "reportados_helpers_monolith.py.bak"
    if not backup.exists():
        backup.write_text((COBROS / "reportados_helpers.py").read_text(encoding="utf-8"), encoding="utf-8")
    lines = read_lines(backup)
    header = monolith_header(lines)

    write_module(
        COBROS / "reportados_dedup_helpers.py",
        "Cobros: dedup documentos, cedulas y armado de items.",
        header + "from .schemas import PagoReportadoListItem\n\n",
        lines[109:971],
    )
    write_module(
        COBROS / "reportados_validadores_helpers.py",
        "Cobros: validadores Gemini y falla_validadores.",
        header
        + "from .reportados_dedup_helpers import (\n"
        "    _cedula_lookup_variants,\n"
        "    _collect_candidatos_canon_desde_reportados,\n"
        "    _es_banco_mercantil,\n"
        "    _normalize_cedula_for_client_lookup,\n"
        "    _pago_existente_info_para_reportado,\n"
        "    _pago_reportado_list_items_from_rows,\n"
        "    _pagos_existentes_info_por_clave,\n"
        "    _referencia_display,\n"
        ")\n"
        "from .schemas import PagoReportadoDuplicadoDiagnostico, PagoReportadoListItem\n\n",
        lines[971:1385],
    )
    write_module(
        COBROS / "reportados_listado_payload.py",
        "Cobros: payloads listado/KPIs y caches primer-maps.",
        header
        + "from .listado_kpis_cache import (\n"
        "    _cobros_listado_kpis_cache_get,\n"
        "    _cobros_listado_kpis_cache_get_stale,\n"
        "    _cobros_listado_kpis_cache_set,\n"
        "    _cobros_listado_kpis_release_singleflight,\n"
        "    _cobros_listado_kpis_try_acquire_singleflight,\n"
        ")\n"
        "from .reportados_dedup_helpers import *\n"
        "from .reportados_validadores_helpers import (\n"
        "    _item_falla_validadores_cola_manual,\n"
        "    _regularizar_reportados_guarded,\n"
        "    reportado_falla_validadores_cobros,\n"
        ")\n"
        "from .schemas import PagoReportadoListItem\n\n",
        lines[1385:],
    )

    (COBROS / "reportados_helpers.py").write_text(
        '''"""Reexport helpers cobros (compat imports)."""
from .reportados_dedup_helpers import *  # noqa: F403
from .reportados_listado_payload import *  # noqa: F403
from .reportados_validadores_helpers import *  # noqa: F403
''',
        encoding="utf-8",
    )


def split_crud_routes() -> None:
    backup = PAGOS / "crud_routes_monolith.py.bak"
    if not backup.exists():
        backup.write_text((PAGOS / "crud_routes.py").read_text(encoding="utf-8"), encoding="utf-8")
    lines = read_lines(backup)
    prefix = "".join(lines[0:269]) + (
        "\nlogger = logging.getLogger(__name__)\n\n"
        "router = APIRouter(dependencies=[Depends(get_current_user)])\n\n"
    )

    write_module(PAGOS / "crud_batch_routes.py", "Pagos: batch y mover a revisar.", prefix, lines[275:901])
    write_module(
        PAGOS / "crud_pagos_mutation_routes.py",
        "Pagos: obtener, crear, actualizar.",
        prefix,
        lines[901:1811],
    )
    write_module(
        PAGOS / "crud_pagos_aplicacion_routes.py",
        "Pagos: aplicar cuotas, eliminar, conciliar batch.",
        prefix,
        lines[1811:],
    )

    (PAGOS / "crud_routes.py").write_text(
        '''"""Pagos CRUD: agregador de sub-routers."""
from .crud_batch_routes import router as _batch_router
from .crud_pagos_aplicacion_routes import router as _aplicacion_router
from .crud_pagos_mutation_routes import router as _mutation_router

router = _batch_router
router.routes.extend(_mutation_router.routes)
router.routes.extend(_aplicacion_router.routes)
''',
        encoding="utf-8",
    )


if __name__ == "__main__":
    print("Splitting reportados_helpers...")
    split_reportados_helpers()
    print("Splitting crud_routes...")
    split_crud_routes()
    print("Done.")
