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
