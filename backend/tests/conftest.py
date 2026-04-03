# -*- coding: utf-8 -*-
"""Pytest: BD existente sin migracion Alembic recibe columnas nuevas del modelo."""

from __future__ import annotations

import pytest
from sqlalchemy import inspect, text

from app.core.database import engine


@pytest.fixture(scope="session", autouse=True)
def _ensure_pagos_link_comprobante() -> None:
    try:
        insp = inspect(engine)
        if "pagos" not in insp.get_table_names():
            return
        col_names = {c["name"] for c in insp.get_columns("pagos")}
        if "link_comprobante" in col_names:
            return
        with engine.connect() as conn:
            conn.execute(
                text("ALTER TABLE pagos ADD COLUMN link_comprobante TEXT NULL")
            )
            conn.commit()
    except Exception:
        pass


@pytest.fixture(scope="session", autouse=True)
def _ensure_pagos_excluir_control5_visto() -> None:
    try:
        insp = inspect(engine)
        if "pagos" not in insp.get_table_names():
            return
        col_names = {c["name"] for c in insp.get_columns("pagos")}
        if "excluir_control_pagos_mismo_dia_monto" in col_names:
            return
        with engine.connect() as conn:
            conn.execute(
                text(
                    "ALTER TABLE pagos ADD COLUMN excluir_control_pagos_mismo_dia_monto BOOLEAN NOT NULL DEFAULT false"
                )
            )
            conn.commit()
    except Exception:
        pass


@pytest.fixture(scope="session", autouse=True)
def _ensure_finiquito_historial_nota() -> None:
    try:
        insp = inspect(engine)
        if "finiquito_estado_historial" not in insp.get_table_names():
            return
        col_names = {
            c["name"] for c in insp.get_columns("finiquito_estado_historial")
        }
        if "nota" in col_names:
            return
        with engine.connect() as conn:
            conn.execute(
                text("ALTER TABLE finiquito_estado_historial ADD COLUMN nota TEXT NULL")
            )
            conn.commit()
    except Exception:
        pass
