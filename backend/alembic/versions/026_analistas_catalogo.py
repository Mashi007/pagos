"""Tabla analistas (catálogo) y FK prestamos.analista_id; relleno desde distinct prestamos.analista.

Revision ID: 026_analistas_catalogo
Revises: 025_finiquito_area_trabajo
Create Date: 2026-03-25
"""

from alembic import op
import sqlalchemy as sa


revision = "026_analistas_catalogo"
down_revision = "025_finiquito_area_trabajo"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "analistas",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nombre", sa.String(length=255), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_analistas_nombre", "analistas", ["nombre"], unique=True)

    op.execute(
        """
        INSERT INTO analistas (nombre, activo, created_at, updated_at)
        SELECT DISTINCT btrim(analista), true, now(), now()
        FROM prestamos
        WHERE analista IS NOT NULL AND btrim(analista) <> ''
        """
    )
    op.execute(
        """
        UPDATE prestamos p
        SET analista_id = a.id
        FROM analistas a
        WHERE btrim(p.analista) = a.nombre
        """
    )

    op.create_foreign_key(
        "fk_prestamos_analista_id_analistas",
        "prestamos",
        "analistas",
        ["analista_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_prestamos_analista_id_analistas", "prestamos", type_="foreignkey")
    op.drop_index("ix_analistas_nombre", table_name="analistas")
    op.drop_table("analistas")
