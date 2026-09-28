"""Post-proceso público: Gemini/import en background no cambia el alta del reporte."""
import os
import sys

os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-with-32-chars-123456")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import MagicMock, patch

import pytest


def test_finalizar_sin_reportado_no_explota():
    import asyncio

    try:
        from app.api.v1.endpoints.cobros_publico import routes as r
    except ImportError as e:
        pytest.skip(str(e))

    db = MagicMock()
    db.get.return_value = None

    async def _gemini(*_a, **_k):
        return {"coincide_exacto": True}

    with patch.object(r, "SessionLocal", return_value=db), patch.object(
        r, "compare_form_with_image_async", side_effect=_gemini
    ):
        asyncio.run(
            r._finalizar_reporte_publico_post_creacion(
                1,
                "RPC-TEST",
                2,
                {},
                b"x",
                "a.jpg",
                10.0,
                "USD",
                False,
            )
        )
    db.close.assert_called()


def test_finalizar_error_marca_en_revision():
    import asyncio

    try:
        from app.api.v1.endpoints.cobros_publico import routes as r
    except ImportError as e:
        pytest.skip(str(e))

    db = MagicMock()
    pr = MagicMock()
    db.get.side_effect = [pr, MagicMock()]
    db.commit.side_effect = RuntimeError("boom")

    async def _gemini(*_a, **_k):
        return {"coincide_exacto": False, "comentario": "x"}

    with patch.object(r, "SessionLocal", return_value=db), patch.object(
        r, "compare_form_with_image_async", side_effect=_gemini
    ), patch.object(
        r, "reportado_falla_validadores_cobros", return_value=False
    ), patch.object(
        r, "_marcar_reporte_en_revision_tras_fallo_post_creacion"
    ) as marcar:
        asyncio.run(
            r._finalizar_reporte_publico_post_creacion(
                9,
                "RPC-ERR",
                3,
                {},
                b"x",
                "a.jpg",
                10.0,
                "USD",
                False,
            )
        )
    marcar.assert_called_once()
