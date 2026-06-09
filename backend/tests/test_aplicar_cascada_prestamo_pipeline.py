"""Pipeline cascada compartido (finiquito Visto recrear-ocr + POST aplicar-pagos-cuotas)."""

from app.services.pagos_aplicacion_prestamo import aplicar_cascada_prestamo_pipeline


class _FakeSession:
    def get(self, _model, pk):
        return None

    def refresh(self, _obj):
        return None


def test_pipeline_prestamo_inexistente():
    out = aplicar_cascada_prestamo_pipeline(999_999_999, _FakeSession())
    assert out["ok"] is False
    assert out["error"] == "Prestamo no encontrado"
