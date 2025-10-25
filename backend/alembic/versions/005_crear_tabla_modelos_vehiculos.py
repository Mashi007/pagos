
from datetime import date
Revision ID: 005
Revises: 004
Create Date: 2025-10-15 01:55:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade():

    op.create_table
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("marca", sa.String(50), nullable=False),
        sa.Column("modelo", sa.String(100), nullable=False),
        sa.Column("nombre_completo", sa.String(150), nullable=False),
        sa.Column
            "categoria", sa.String(50), nullable=True
        ),  # Sedán, SUV, Hatchback, etc.
        sa.Column("precio_base", sa.Numeric(12, 2), nullable=True),
        sa.Column("activo", sa.Boolean(), nullable=False, default=True),
        sa.Column("descripcion", sa.Text(), nullable=True),
        sa.Column
            "especificaciones", sa.JSON(), nullable=True
        ),  # Motor, transmisión, etc.
        sa.Column
            "created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.Column
            "updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nombre_completo"),

    # Crear índices
    op.create_index

        # Toyota
        
        },
        
        },
        
        },
        
        },
        # Nissan
        
        },
        
        },
        
        },
        
        },
        # Chevrolet
        
        },
        
        },
        
        },
        
        },
        # Ford
        
        },
        
        },
        
        },
        
        },
        # Hyundai
        
        },
        
        },
        
        },
        
        },
        # Kia
        
        },
        
        },
        
        },
        
        },
        # Motocicletas
        
        },
        
        },
        
        },
        
        },

        op.execute
                VALUES (:marca, :modelo, :nombre_completo, :categoria, :precio_base, true, now(), now())
                ON CONFLICT (nombre_completo) DO NOTHING
            """
            ).bindparam(**modelo)


def downgrade():
