#!/usr/bin/env python3
"""Split monolithic cobros/routes.py and pagos/routes.py into submodules."""
from __future__ import annotations

import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COBROS_DIR = ROOT / "app" / "api" / "v1" / "endpoints" / "cobros"
PAGOS_DIR = ROOT / "app" / "api" / "v1" / "endpoints" / "pagos"


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines(keepends=True)


def write_module(path: Path, prefix: str, body_lines: list[str], suffix: str = "") -> None:
    content = prefix + "".join(body_lines) + suffix
    path.write_text(content, encoding="utf-8")
    print(f"  wrote {path.name} ({len(body_lines)} body lines)")


def slice_lines(lines: list[str], start: int, end: int) -> list[str]:
    return lines[start - 1 : end]


def cobros_imports(lines: list[str]) -> str:
    return "".join(lines[0:92])


def split_cobros() -> None:
    src = COBROS_DIR / "routes.py"
    backup = COBROS_DIR / "routes_monolith.py.bak"
    if not backup.exists():
        backup.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    lines = read_lines(backup)
    imp = cobros_imports(lines)

    schemas_prefix = (
        '"""Pydantic schemas for cobros pagos reportados."""\n'
        "from typing import List, Optional\n\n"
        "from pydantic import BaseModel\n\n"
        "from app.services.cobros.recibo_pdf import WHATSAPP_DISPLAY, WHATSAPP_LINK\n\n"
    )
    schemas_body = slice_lines(lines, 520, 645) + slice_lines(lines, 3744, 3760) + slice_lines(lines, 647, 652)
    write_module(COBROS_DIR / "schemas.py", schemas_prefix, schemas_body)

    cache_prefix = '"""Cache KPIs listado cobros y rate limit escaner."""\n' + imp
    write_module(COBROS_DIR / "listado_kpis_cache.py", cache_prefix, slice_lines(lines, 96, 516))

    helpers_prefix = (
        '"""Helpers internos cobros: validadores, dedup, payloads listado/KPIs."""\n'
        + imp
        + "from .listado_kpis_cache import (\n"
        "    _cobros_listado_kpis_cache_get,\n"
        "    _cobros_listado_kpis_cache_get_stale,\n"
        "    _cobros_listado_kpis_cache_set,\n"
        "    _cobros_listado_kpis_release_singleflight,\n"
        "    _cobros_listado_kpis_try_acquire_singleflight,\n"
        "    _drop_pago_from_listado_kpis_cache,\n"
        "    _drop_pagos_from_listado_kpis_cache,\n"
        "    _invalidate_cobros_listado_kpis_cache,\n"
        ")\n"
        "from .schemas import MENSAJE_RECHAZO_GENERICO, PagoReportadoListItem\n\n"
    )
    helpers_body = slice_lines(lines, 655, 2496)
    write_module(COBROS_DIR / "reportados_helpers.py", helpers_prefix, helpers_body)

    reportados_prefix = (
        '"""Endpoints HTTP cobros: pagos reportados."""\n'
        + imp
        + "from .listado_kpis_cache import _invalidate_cobros_listado_kpis_cache\n"
        "from .reportados_helpers import (\n"
        "    _crear_pago_desde_reportado_y_aplicar_cuotas,\n"
        "    _diagnostico_duplicado_reportado,\n"
        "    _kpis_pagos_reportados_payload,\n"
        "    _list_pagos_reportados_payload,\n"
        "    _marcar_reportados_como_eliminado_duplicado,\n"
        "    _persist_marcar_exportados_y_cola,\n"
        "    _rechazar_aprobacion_si_documento_ya_en_pagos,\n"
        "    _rechazar_si_documento_reportado_duplicado_en_pagos,\n"
        "    _registrar_historial,\n"
        "    actualizar_flag_falla_validadores,\n"
        "    reportado_falla_validadores_cobros,\n"
        ")\n"
        "from .schemas import (\n"
        "    AprobarRechazarBody,\n"
        "    CambiarEstadoBody,\n"
        "    EditarPagoReportadoBody,\n"
        "    MarcarExportadosBody,\n"
        "    PagoReportadoDetalle,\n"
        "    PagoReportadoDuplicadoDiagnostico,\n"
        "    PagoReportadoHistorialItem,\n"
        "    PagoReportadoListItem,\n"
        ")\n\n"
        "router = APIRouter(dependencies=[Depends(get_current_user)])\n\n"
    )
    write_module(
        COBROS_DIR / "reportados_routes.py",
        reportados_prefix,
        slice_lines(lines, 2497, 4335),
    )

    escaner_prefix = (
        '"""Endpoints HTTP cobros: escaner Infopagos."""\n'
        + imp
        + "from .listado_kpis_cache import _enforce_escaner_rate_limit, _invalidate_cobros_listado_kpis_cache\n"
        "from .reportados_helpers import _reencolar_escaner_infopagos_aprobado_sin_gestion_por_cedula\n\n"
        "router = APIRouter(dependencies=[Depends(get_current_user)])\n\n"
    )
    write_module(
        COBROS_DIR / "escaner_routes.py",
        escaner_prefix,
        slice_lines(lines, 4337, len(lines)),
    )

    aggregator = textwrap.dedent(
        '''\
        """
        Cobros (admin): agregador de routers y reexport de utilidades internas.
        """
        from .escaner_routes import router as _escaner_router
        from .listado_kpis_cache import _invalidate_cobros_listado_kpis_cache
        from .reportados_helpers import (
            _cedulas_en_clientes_set,
            _list_pagos_reportados_payload,
            actualizar_flag_falla_validadores,
            reportado_falla_validadores_cobros,
        )
        from .reportados_routes import router as _reportados_router

        router = _reportados_router
        router.routes.extend(_escaner_router.routes)

        __all__ = [
            "_cedulas_en_clientes_set",
            "_invalidate_cobros_listado_kpis_cache",
            "_list_pagos_reportados_payload",
            "actualizar_flag_falla_validadores",
            "reportado_falla_validadores_cobros",
            "router",
        ]
        '''
    )
    (COBROS_DIR / "routes.py").write_text(aggregator, encoding="utf-8")

    init_py = textwrap.dedent(
        '''\
        """Cobros (admin): router y utilidades internas reutilizadas en tests."""

        from .reportados_helpers import _cedulas_en_clientes_set
        from .routes import (
            _invalidate_cobros_listado_kpis_cache,
            _list_pagos_reportados_payload,
            actualizar_flag_falla_validadores,
            reportado_falla_validadores_cobros,
            router,
        )

        __all__ = [
            "_cedulas_en_clientes_set",
            "_invalidate_cobros_listado_kpis_cache",
            "_list_pagos_reportados_payload",
            "actualizar_flag_falla_validadores",
            "reportado_falla_validadores_cobros",
            "router",
        ]
        '''
    )
    (COBROS_DIR / "__init__.py").write_text(init_py, encoding="utf-8")
    print("  cobros split complete")


def pagos_imports(lines: list[str]) -> str:
    return "".join(lines[0:269])


def split_pagos() -> None:
    src = PAGOS_DIR / "routes.py"
    backup = PAGOS_DIR / "routes_monolith.py.bak"
    if not backup.exists():
        backup.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    lines = read_lines(backup)
    imp = pagos_imports(lines)
    router_block = (
        "\nlogger = logging.getLogger(__name__)\n\n"
        "router = APIRouter(dependencies=[Depends(get_current_user)])\n\n"
    )

    sections = [
        ("comprobante_routes.py", 275, 362),
        ("listado_routes.py", 363, 1210),
        ("upload_excel_routes.py", 1211, 2803),
        ("importar_cobros_routes.py", 2804, 3207),
        ("export_batch_routes.py", 3208, 4009),
        ("conciliacion_routes.py", 4010, 4163),
        ("kpis_routes.py", 4164, 4781),
        ("crud_routes.py", 4782, 6947),
        ("cedulas_bs_routes.py", 6948, len(lines)),
    ]

    for filename, start, end in sections:
        prefix = f'"""Pagos API: {filename.replace("_routes.py", "")}."""\n' + imp + router_block
        write_module(PAGOS_DIR / filename, prefix, slice_lines(lines, start, end))

    aggregator = textwrap.dedent(
        '''\
        """
        Pagos: agregador de routers y reexport de utilidades compartidas.
        """
        from app.services.pagos_aplicacion_prestamo import (
            aplicar_pagos_pendientes_prestamo,
            aplicar_pagos_pendientes_prestamo_con_diagnostico,
        )
        from app.services.pagos_cascada_aplicacion import (
            _aplicar_pago_a_cuotas_interno,
            _marcar_prestamo_liquidado_si_corresponde,
        )
        from app.services.pagos_cascada_mensajes import _mensaje_sin_aplicacion_cascada

        from .cedulas_bs_routes import router as _cedulas_bs_router
        from .comprobante_routes import router as _comprobante_router
        from .conciliacion_routes import router as _conciliacion_router
        from .constants import TZ_NEGOCIO
        from .crud_routes import router as _crud_router
        from .export_batch_routes import router as _export_batch_router
        from .importar_cobros_routes import importar_un_pago_reportado_a_pagos
        from .importar_cobros_routes import router as _importar_router
        from .kpis_routes import get_pagos_kpis, get_pagos_stats
        from .kpis_routes import router as _kpis_router
        from .listado_routes import listar_pagos
        from .listado_routes import router as _listado_router
        from .pago_conciliacion_estado import _estado_conciliacion_post_cascada
        from .sql_where_pagos import _where_pago_elegible_reaplicacion_cascada
        from .upload_excel_routes import router as _upload_router

        router = _comprobante_router
        for sub in (
            _listado_router,
            _upload_router,
            _importar_router,
            _export_batch_router,
            _conciliacion_router,
            _kpis_router,
            _crud_router,
            _cedulas_bs_router,
        ):
            router.routes.extend(sub.routes)

        __all__ = [
            "TZ_NEGOCIO",
            "_aplicar_pago_a_cuotas_interno",
            "_estado_conciliacion_post_cascada",
            "_marcar_prestamo_liquidado_si_corresponde",
            "_mensaje_sin_aplicacion_cascada",
            "_where_pago_elegible_reaplicacion_cascada",
            "aplicar_pagos_pendientes_prestamo",
            "aplicar_pagos_pendientes_prestamo_con_diagnostico",
            "get_pagos_kpis",
            "get_pagos_stats",
            "importar_un_pago_reportado_a_pagos",
            "listar_pagos",
            "router",
        ]
        '''
    )
    (PAGOS_DIR / "routes.py").write_text(aggregator, encoding="utf-8")
    print("  pagos split complete")


if __name__ == "__main__":
    print("Splitting cobros...")
    split_cobros()
    print("Splitting pagos...")
    split_pagos()
    print("Done.")
