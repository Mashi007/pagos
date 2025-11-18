"""merge heads conversaciones_whatsapp y ml_impago_calculado

Revision ID: e2ee661f42a6
Revises: 20250117_conversaciones_whatsapp, 20251118_ml_impago_calculado
Create Date: 2025-11-18 06:54:43.480661

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e2ee661f42a6'
down_revision: Union[str, None] = ('20250117_conversaciones_whatsapp', '20251118_ml_impago_calculado')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Aplicar cambios a la base de datos."""
    pass


def downgrade() -> None:
    """Revertir cambios de la base de datos."""
    pass
