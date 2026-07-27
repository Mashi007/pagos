"""Tabla concesionarios (catalogo) y FK prestamos.concesionario_id; relleno desde distinct prestamos.concesionario.

Revision ID: 080_concesionarios_catalogo
Revises: 079_envios_notificacion_tipo_tab_varchar40
Create Date: 2026-07-27
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "080_concesionarios_catalogo"
down_revision = "079_envios_notificacion_tipo_tab_varchar40"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())

    if "concesionarios" not in tables:
        op.create_table(
            "concesionarios",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("nombre", sa.String(length=255), nullable=False),
            sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_concesionarios_nombre", "concesionarios", ["nombre"], unique=True)
    else:
        cols = {c["name"] for c in inspector.get_columns("concesionarios")}
        if "activo" not in cols:
            op.add_column(
                "concesionarios",
                sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            )
        if "created_at" not in cols:
            op.add_column(
                "concesionarios",
                sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            )
        if "updated_at" not in cols:
            op.add_column(
                "concesionarios",
                sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
            )
        if "nombre" not in cols:
            op.add_column(
                "concesionarios",
                sa.Column("nombre", sa.String(length=255), nullable=False, server_default=""),
            )

        inspector = inspect(bind)
        indexes = inspector.get_indexes("concesionarios")
        has_nombre_ix = any(ix.get("column_names") == ["nombre"] for ix in indexes)
        index_names = {ix["name"] for ix in indexes}
        if not has_nombre_ix and "ix_concesionarios_nombre" not in index_names:
            op.create_index("ix_concesionarios_nombre", "concesionarios", ["nombre"], unique=True)

    op.execute(
        """
        INSERT INTO concesionarios (nombre, activo, created_at, updated_at)
        SELECT d.nombre, true, now(), now()
        FROM (
            SELECT DISTINCT btrim(concesionario) AS nombre
            FROM prestamos
            WHERE concesionario IS NOT NULL AND btrim(concesionario) <> ''
        ) d
        WHERE NOT EXISTS (
            SELECT 1 FROM concesionarios c WHERE c.nombre = d.nombre
        )
        """
    )
    op.execute(
        """
        UPDATE prestamos p
        SET concesionario_id = c.id
        FROM concesionarios c
        WHERE btrim(p.concesionario) = c.nombre
          AND (p.concesionario_id IS NULL OR p.concesionario_id <> c.id)
        """
    )

    inspector = inspect(bind)
    fks = {fk["name"] for fk in inspector.get_foreign_keys("prestamos")}
    already_linked = any(
        fk.get("constrained_columns") == ["concesionario_id"]
        and fk.get("referred_table") == "concesionarios"
        for fk in inspector.get_foreign_keys("prestamos")
    )
    if "fk_prestamos_concesionario_id_concesionarios" not in fks and not already_linked:
        op.create_foreign_key(
            "fk_prestamos_concesionario_id_concesionarios",
            "prestamos",
            "concesionarios",
            ["concesionario_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)
    fks = {fk["name"] for fk in inspector.get_foreign_keys("prestamos")}
    if "fk_prestamos_concesionario_id_concesionarios" in fks:
        op.drop_constraint(
            "fk_prestamos_concesionario_id_concesionarios",
            "prestamos",
            type_="foreignkey",
        )
