"""merge_heads_foreign_keys_normalization

Revision ID: 8fe8e0281801
Revises: e2ee661f42a6, 20250127_02_normalize_catalogs
Create Date: 2025-12-02 23:36:15.253645

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8fe8e0281801'
down_revision: Union[str, None] = ('e2ee661f42a6', '20250127_02_normalize_catalogs')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Aplicar cambios a la base de datos."""
    pass


def downgrade() -> None:
    """Revertir cambios de la base de datos."""
    pass
