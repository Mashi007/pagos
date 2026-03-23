# -*- coding: utf-8 -*-
"""One-off patch: estadisticas-por-tab, resumen, TIPOS_TAB, datetime import."""
from pathlib import Path

p = Path(__file__).resolve().parents[1] / "backend" / "app" / "api" / "v1" / "endpoints" / "notificaciones.py"
text = p.read_text(encoding="utf-8", errors="replace")

old1 = "from datetime import date\n"
new1 = "from datetime import date, datetime, timedelta\n"
if old1 not in text:
    raise SystemExit("import block not found")
text = text.replace(old1, new1, 1)

old_resumen = '''@router.get("/estadisticas/resumen")
def get_notificaciones_resumen(db: Session = Depends(get_db)):
    """Resumen para sidebar. El frontend espera: no_leidas, total. get_db inyectado para consistencia."""
    return {"no_leidas": 0, "total": 0}
'''

new_resumen = '''@router.get("/estadisticas/resumen")
def get_notificaciones_resumen(db: Session = Depends(get_db)):
    """
    Resumen para sidebar: total de envios registrados y fallidos en ventana reciente.
    no_leidas = envios con exito=False (atencion / rebotados) en los ultimos 30 dias.
    total = todos los registros de envios_notificacion en los ultimos 30 dias.
    """
    desde = datetime.utcnow() - timedelta(days=30)
    try:
        total = (
            db.scalar(
                select(func.count(EnvioNotificacion.id)).where(
                    EnvioNotificacion.fecha_envio >= desde
                )
            )
            or 0
        )
        fallidos = (
            db.scalar(
                select(func.count(EnvioNotificacion.id)).where(
                    EnvioNotificacion.fecha_envio >= desde,
                    EnvioNotificacion.exito.is_(False),
                )
            )
            or 0
        )
        return {"no_leidas": int(fallidos), "total": int(total)}
    except Exception as e:
        logger.warning("get_notificaciones_resumen: %s", e)
        return {"no_leidas": 0, "total": 0}
'''

if old_resumen not in text:
    raise SystemExit("resumen block not found")
text = text.replace(old_resumen, new_resumen, 1)

# Match estadisticas block by unique substring (avoid docstring encoding issues)
marker = '    result = {\n        "dias_5": {"enviados": 0, "rebotados": 0},\n        "dias_3": {"enviados": 0, "rebotados": 0},\n        "dias_1": {"enviados": 0, "rebotados": 0},\n        "hoy": {"enviados": 0, "rebotados": 0},\n        "dias_1_retraso": {"enviados": 0, "rebotados": 0},\n    }\n    try:\n        for tipo in ("dias_5", "dias_3", "dias_1", "hoy", "dias_1_retraso"):\n'

new_block = '''    result = {
        "dias_5": {"enviados": 0, "rebotados": 0},
        "dias_3": {"enviados": 0, "rebotados": 0},
        "dias_1": {"enviados": 0, "rebotados": 0},
        "hoy": {"enviados": 0, "rebotados": 0},
        "dias_1_retraso": {"enviados": 0, "rebotados": 0},
        "dias_3_retraso": {"enviados": 0, "rebotados": 0},
        "dias_5_retraso": {"enviados": 0, "rebotados": 0},
        "prejudicial": {"enviados": 0, "rebotados": 0},
        "liquidados": {"enviados": 0, "rebotados": 0},
    }
    try:
        for tipo in (
            "dias_5",
            "dias_3",
            "dias_1",
            "hoy",
            "dias_1_retraso",
            "dias_3_retraso",
            "dias_5_retraso",
            "prejudicial",
            "liquidados",
        ):
'''

if marker not in text:
    raise SystemExit("estadisticas result block not found")
text = text.replace(marker, new_block, 1)

# Update docstring of get_estadisticas_por_tab (first occurrence after router)
old_doc = '    """\n    KPIs por pestaña / tipo_tab: correos enviados y rebotados.'
# File may have corrupted enye - find line starting with KPIs
import re

text = re.sub(
    r'(@router\.get\("/estadisticas-por-tab"[^\n]*\n'
    r'def get_estadisticas_por_tab\([^)]*\):\n)'
    r'    """\n'
    r'    KPIs[^\n]*\n'
    r'    Datos desde tabla envios_notificacion[^\n]*\n'
    r'    """\n',
    r'\1    """\n'
    r'    KPIs por pestaña / tipo_tab: correos enviados y rebotados.\n'
    r'    Incluye previas (dias_5, dias_3, dias_1, hoy), retrasadas (dias_*_retraso),\n'
    r'    prejudicial y credito pagado (liquidados). Datos desde envios_notificacion.\n'
    r'    """\n',
    text,
    count=1,
)
if 'Incluye previas' not in text:
    raise SystemExit("docstring replace failed")

old_tipos = 'TIPOS_TAB_NOTIFICACIONES = ("dias_5", "dias_3", "dias_1", "hoy", "dias_1_retraso")\n'
new_tipos = '''TIPOS_TAB_NOTIFICACIONES = (
    "dias_5",
    "dias_3",
    "dias_1",
    "hoy",
    "dias_1_retraso",
    "dias_3_retraso",
    "dias_5_retraso",
    "prejudicial",
    "liquidados",
)
'''
if old_tipos not in text:
    raise SystemExit("TIPOS_TAB line not found")
text = text.replace(old_tipos, new_tipos, 1)

# Query description: replace line if it matches pattern
text = re.sub(
    r'    tipo: str = Query\(\.\.\., description="[^"]*"\),\n',
    '    tipo: str = Query(\n'
    '        ...,\n'
    '        description="tipo_tab: dias_5, dias_3, dias_1, hoy, dias_1_retraso, '
    'dias_3_retraso, dias_5_retraso, prejudicial, liquidados",\n'
    '    ),\n',
    text,
    count=1,
)

p.write_text(text, encoding="utf-8", newline="\n")
print("OK patched", p)
