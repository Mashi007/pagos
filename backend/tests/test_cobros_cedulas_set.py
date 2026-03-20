import os
import sys
from unittest.mock import MagicMock

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-32-chars-123456")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api.v1.endpoints.cobros import _cedulas_en_clientes_set


def test_cedulas_en_clientes_set_usa_escalar_completo():
    """Debe tomar la cédula completa de scalars().all(), no solo el primer carácter."""
    db = MagicMock()
    db.execute.return_value.scalars.return_value.all.return_value = ["V20149164", "00123456", None, "  "]

    result = _cedulas_en_clientes_set(db)

    assert "V20149164" in result
    assert "V123456" in result
    assert "123456" in result
    assert "V" not in result
