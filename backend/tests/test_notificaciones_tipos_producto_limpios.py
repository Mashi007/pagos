"""Contrato: tipos retirados no figuran en sets de producto (manual / plantilla)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TABS = (
    ROOT
    / "app"
    / "api"
    / "v1"
    / "endpoints"
    / "notificaciones_tabs"
    / "routes.py"
).read_text(encoding="utf-8")
NOTIF = (
    ROOT / "app" / "api" / "v1" / "endpoints" / "notificaciones" / "routes.py"
).read_text(encoding="utf-8")

RETIRADOS = (
    "PAGO_5_DIAS_ANTES",
    "PAGO_3_DIAS_ANTES",
    "PAGO_1_DIA_ANTES",
    "PAGO_DIA_0",
    "COBRANZAS_EXCEL",
    "CUOTAS_4_MAS",
    "MASIVOS",
)


def _frozenset_block(src: str, name: str) -> str:
    i = src.index(name)
    j = src.index(")", src.index("frozenset", i))
    return src[i:j]


def test_tipos_caso_manual_sin_retirados():
    block = _frozenset_block(TABS, "TIPOS_CASO_MANUAL")
    for t in RETIRADOS:
        assert f'"{t}"' not in block, t
    for t in (
        "PAGO_1_DIA_ATRASADO",
        "PAGO_10_DIAS_ATRASADO",
        "PREJUDICIAL",
        "ESTADO_CUENTA",
        "PAGO_2_DIAS_ANTES_PENDIENTE",
    ):
        assert f'"{t}"' in block, t


def test_tipos_plantilla_sin_retirados():
    block = _frozenset_block(NOTIF, "TIPOS_PLANTILLA_PERMITIDOS")
    for t in (
        "PAGO_5_DIAS_ANTES",
        "PAGO_3_DIAS_ANTES",
        "PAGO_DIA_0",
        "MASIVOS",
        "MORA_61",
        "MORA_90",
    ):
        assert f'"{t}"' not in block, t
    assert '"PREJUDICIAL"' in block
    assert '"ESTADO_CUENTA"' in block
