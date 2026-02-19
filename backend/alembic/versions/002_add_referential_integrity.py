"""Add referential integrity to DefinicionCampo

Revision ID: 002_add_referential_integrity
Revises: 001_initial
Create Date: 2026-02-19 

This migration adds foreign key constraints and indexed lookup tables for DefinicionCampo
to ensure referential integrity when referencing database tables and columns.
"""
from alembic import op
import sqlalchemy as sa

# Revision identifiers, used by Alembic.
revision = '002_add_referential_integrity'
down_revision = '001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add FK constraints and indices for DefinicionCampo references."""
    
    # Create tabla_esquema lookup table for referenced tables
    op.create_table(
        'tablas_esquema',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nombre_tabla', sa.String(200), nullable=False, unique=True),
        sa.Column('descripcion', sa.Text(), nullable=True),
        sa.Column('activa', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('creada_en', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('idx_tablas_esquema_nombre', 'nombre_tabla')
    )
    
    # Create campos_esquema lookup table for referenced columns
    op.create_table(
        'campos_esquema',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tabla_id', sa.Integer(), nullable=False),
        sa.Column('nombre_campo', sa.String(200), nullable=False),
        sa.Column('tipo_dato', sa.String(100), nullable=True),
        sa.Column('activo', sa.Boolean(), nullable=False, server_default='true'),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tabla_id'], ['tablas_esquema.id']),
        sa.UniqueConstraint('tabla_id', 'nombre_campo', name='_tabla_campo_uc'),
        sa.Index('idx_campos_esquema_tabla', 'tabla_id'),
        sa.Index('idx_campos_esquema_nombre', 'nombre_campo')
    )
    
    # Add FK columns to definiciones_campos (backward compatible)
    op.add_column('definiciones_campos', 
                  sa.Column('tabla_id', sa.Integer(), nullable=True))
    op.add_column('definiciones_campos', 
                  sa.Column('tabla_referenciada_id', sa.Integer(), nullable=True))
    op.add_column('definiciones_campos', 
                  sa.Column('campo_referenciado_id', sa.Integer(), nullable=True))
    
    # Add foreign key constraints
    op.create_foreign_key(
        'fk_def_campo_tabla_id',
        'definiciones_campos', 'tablas_esquema',
        ['tabla_id'], ['id'],
        ondelete='RESTRICT'
    )
    
    op.create_foreign_key(
        'fk_def_campo_tabla_ref_id',
        'definiciones_campos', 'tablas_esquema',
        ['tabla_referenciada_id'], ['id'],
        ondelete='SET NULL'
    )
    
    op.create_foreign_key(
        'fk_def_campo_campo_ref_id',
        'definiciones_campos', 'campos_esquema',
        ['campo_referenciado_id'], ['id'],
        ondelete='SET NULL'
    )
    
    # Add indices for existing string columns (for backward compatibility)
    op.create_index('idx_definiciones_campos_tabla_str', 'definiciones_campos', ['tabla'])
    op.create_index('idx_definiciones_campos_tabla_ref_str', 'definiciones_campos', ['tabla_referenciada'])
    op.create_index('idx_definiciones_campos_creado', 'definiciones_campos', ['creado_en'])


def downgrade() -> None:
    """Remove referential integrity constraints."""
    
    # Drop foreign keys
    op.drop_constraint('fk_def_campo_campo_ref_id', 'definiciones_campos', type_='foreignkey')
    op.drop_constraint('fk_def_campo_tabla_ref_id', 'definiciones_campos', type_='foreignkey')
    op.drop_constraint('fk_def_campo_tabla_id', 'definiciones_campos', type_='foreignkey')
    
    # Drop indices
    op.drop_index('idx_definiciones_campos_creado', table_name='definiciones_campos')
    op.drop_index('idx_definiciones_campos_tabla_ref_str', table_name='definiciones_campos')
    op.drop_index('idx_definiciones_campos_tabla_str', table_name='definiciones_campos')
    
    # Drop columns
    op.drop_column('definiciones_campos', 'campo_referenciado_id')
    op.drop_column('definiciones_campos', 'tabla_referenciada_id')
    op.drop_column('definiciones_campos', 'tabla_id')
    
    # Drop lookup tables
    op.drop_table('campos_esquema')
    op.drop_table('tablas_esquema')
