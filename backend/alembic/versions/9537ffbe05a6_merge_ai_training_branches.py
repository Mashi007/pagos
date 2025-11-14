"""merge_ai_training_branches

Revision ID: 9537ffbe05a6
Revises: 20250127_performance_indexes, 20251114_04_modelos_riesgo
Create Date: 2025-11-14 15:53:49.962828

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9537ffbe05a6'
down_revision: Union[str, None] = ('20250127_performance_indexes', '20251114_04_modelos_riesgo')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Aplicar cambios a la base de datos."""
    pass


def downgrade() -> None:
    """Revertir cambios de la base de datos."""
    pass
