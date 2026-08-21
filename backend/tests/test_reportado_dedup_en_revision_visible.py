"""Cola Cobros: en_revision no se oculta por dedupe de nº operación."""
from types import SimpleNamespace

from app.api.v1.endpoints.cobros.reportados_dedup_helpers import (
    _reportado_pasa_filtro_dedup_num_op,
)


def test_en_revision_siempre_pasa_filtro_dedup_num_op():
    primer = {"449886745606242304": 100}
    junior = SimpleNamespace(
        id=17439,
        estado="en_revision",
        numero_operacion="449886745606242304",
    )
    assert _reportado_pasa_filtro_dedup_num_op(junior, primer) is True


def test_pendiente_junior_se_oculta_por_dedup_num_op():
    primer = {"449886745606242304": 100}
    junior = SimpleNamespace(
        id=17439,
        estado="pendiente",
        numero_operacion="449886745606242304",
    )
    assert _reportado_pasa_filtro_dedup_num_op(junior, primer) is False


def test_pendiente_lider_pasa_filtro_dedup_num_op():
    primer = {"449886745606242304": 100}
    lead = SimpleNamespace(
        id=100,
        estado="pendiente",
        numero_operacion="449886745606242304",
    )
    assert _reportado_pasa_filtro_dedup_num_op(lead, primer) is True
