"""Añadir LIQUIDADO como estado válido en prestamos.

Cuando todas las cuotas están pagadas, el backend marca el préstamo como LIQUIDADO.
La restricción ck_prestamos_estado_valido en BD no lo permitía y provocaba IntegrityError al aprobar pagos reportados.

Revision ID: 019_prestamos_liquidado
Revises: 018_cedulas_reportar_bs
Create Date: 2026-03-18

"""
from alembic import op

revision = "019_prestamos_liquidado"
down_revision = "018_cedulas_reportar_bs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE public.prestamos
        DROP CONSTRAINT IF EXISTS ck_prestamos_estado_valido;
    """)
    op.execute("""
        ALTER TABLE public.prestamos
        ADD CONSTRAINT ck_prestamos_estado_valido
        CHECK (estado IN ('DRAFT', 'EN_REVISION', 'APROBADO', 'DESEMBOLSADO', 'EVALUADO', 'RECHAZADO', 'LIQUIDADO'));
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE public.prestamos
        DROP CONSTRAINT IF EXISTS ck_prestamos_estado_valido;
    """)
    op.execute("""
        ALTER TABLE public.prestamos
        ADD CONSTRAINT ck_prestamos_estado_valido
        CHECK (estado IN ('DRAFT', 'EN_REVISION', 'APROBADO', 'DESEMBOLSADO', 'EVALUADO', 'RECHAZADO'));
    """)

