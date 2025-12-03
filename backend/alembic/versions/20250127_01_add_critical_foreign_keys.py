"""add critical foreign keys for referential integrity

Revision ID: 20250127_01_critical_fks
Revises: 20251118_ml_impago_calculado
Create Date: 2025-01-27

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '20250127_01_critical_fks'
down_revision = '20251118_ml_impago_calculado'
branch_labels = None
depends_on = None


def upgrade():
    """
    Agregar ForeignKeys críticos faltantes para integridad referencial:
    1. pagos.prestamo_id → prestamos.id
    2. pagos.cliente_id → clientes.id (nueva columna)
    3. prestamos_evaluacion.prestamo_id → prestamos.id
    4. pagos_auditoria.pago_id → pagos.id
    5. prestamos_auditoria.prestamo_id → prestamos.id
    """
    connection = op.get_bind()
    inspector = inspect(connection)

    # Verificar que las tablas críticas existan
    required_tables = ['pagos', 'prestamos', 'clientes', 'prestamos_evaluacion']
    optional_tables = ['pagos_auditoria', 'prestamos_auditoria']  # Tablas opcionales
    
    for table in required_tables:
        if table not in inspector.get_table_names():
            print(f"⚠️ Tabla crítica '{table}' no existe, saltando migración")
            return
    
    # Verificar tablas opcionales
    tables = inspector.get_table_names()
    pagos_auditoria_exists = 'pagos_auditoria' in tables
    prestamos_auditoria_exists = 'prestamos_auditoria' in tables
    
    if not pagos_auditoria_exists:
        print("⚠️ Tabla 'pagos_auditoria' no existe, se omitirá su ForeignKey")
    if not prestamos_auditoria_exists:
        print("⚠️ Tabla 'prestamos_auditoria' no existe, se omitirá su ForeignKey")

    # 1. Agregar cliente_id a pagos si no existe
    pagos_columns = [col['name'] for col in inspector.get_columns('pagos')]
    if 'cliente_id' not in pagos_columns:
        print("✅ Agregando columna cliente_id a tabla pagos...")
        op.add_column('pagos', sa.Column('cliente_id', sa.Integer(), nullable=True))
        
        # Poblar cliente_id basado en cedula
        print("✅ Poblando cliente_id basado en cedula...")
        op.execute("""
            UPDATE pagos p
            SET cliente_id = (
                SELECT c.id 
                FROM clientes c 
                WHERE c.cedula = p.cedula 
                LIMIT 1
            )
            WHERE cliente_id IS NULL;
        """)
        
        # Crear índice
        op.create_index('ix_pagos_cliente_id', 'pagos', ['cliente_id'])
        print("✅ Columna cliente_id agregada y poblada")

    # 2. Agregar ForeignKey pagos.prestamo_id → prestamos.id
    try:
        # Verificar si el FK ya existe
        fks = inspector.get_foreign_keys('pagos')
        fk_exists = any(fk['referred_table'] == 'prestamos' and 'prestamo_id' in fk['constrained_columns'] for fk in fks)
        
        if not fk_exists:
            print("✅ Agregando ForeignKey pagos.prestamo_id → prestamos.id...")
            op.create_foreign_key(
                'fk_pagos_prestamo',
                'pagos',
                'prestamos',
                ['prestamo_id'],
                ['id'],
                ondelete='SET NULL'
            )
            print("✅ ForeignKey pagos.prestamo_id creado")
    except Exception as e:
        print(f"⚠️ Error al crear FK pagos.prestamo_id: {e}")

    # 3. Agregar ForeignKey pagos.cliente_id → clientes.id
    try:
        fks = inspector.get_foreign_keys('pagos')
        fk_exists = any(fk['referred_table'] == 'clientes' and 'cliente_id' in fk['constrained_columns'] for fk in fks)
        
        if not fk_exists:
            print("✅ Agregando ForeignKey pagos.cliente_id → clientes.id...")
            op.create_foreign_key(
                'fk_pagos_cliente',
                'pagos',
                'clientes',
                ['cliente_id'],
                ['id'],
                ondelete='SET NULL'
            )
            print("✅ ForeignKey pagos.cliente_id creado")
    except Exception as e:
        print(f"⚠️ Error al crear FK pagos.cliente_id: {e}")

    # 4. Agregar ForeignKey prestamos_evaluacion.prestamo_id → prestamos.id
    try:
        fks = inspector.get_foreign_keys('prestamos_evaluacion')
        fk_exists = any(fk['referred_table'] == 'prestamos' and 'prestamo_id' in fk['constrained_columns'] for fk in fks)
        
        if not fk_exists:
            print("✅ Agregando ForeignKey prestamos_evaluacion.prestamo_id → prestamos.id...")
            op.create_foreign_key(
                'fk_prestamos_evaluacion_prestamo',
                'prestamos_evaluacion',
                'prestamos',
                ['prestamo_id'],
                ['id'],
                ondelete='CASCADE'
            )
            print("✅ ForeignKey prestamos_evaluacion.prestamo_id creado")
    except Exception as e:
        print(f"⚠️ Error al crear FK prestamos_evaluacion.prestamo_id: {e}")

    # 5. Agregar ForeignKey pagos_auditoria.pago_id → pagos.id (solo si la tabla existe)
    if pagos_auditoria_exists:
        try:
            fks = inspector.get_foreign_keys('pagos_auditoria')
            fk_exists = any(fk['referred_table'] == 'pagos' and 'pago_id' in fk['constrained_columns'] for fk in fks)
            
            if not fk_exists:
                print("✅ Agregando ForeignKey pagos_auditoria.pago_id → pagos.id...")
                op.create_foreign_key(
                    'fk_pagos_auditoria_pago',
                    'pagos_auditoria',
                    'pagos',
                    ['pago_id'],
                    ['id'],
                    ondelete='CASCADE'
                )
                print("✅ ForeignKey pagos_auditoria.pago_id creado")
        except Exception as e:
            print(f"⚠️ Error al crear FK pagos_auditoria.pago_id: {e}")
    else:
        print("⏭️  Omitiendo ForeignKey pagos_auditoria (tabla no existe)")

    # 6. Agregar ForeignKey prestamos_auditoria.prestamo_id → prestamos.id (solo si la tabla existe)
    if prestamos_auditoria_exists:
        try:
            fks = inspector.get_foreign_keys('prestamos_auditoria')
            fk_exists = any(fk['referred_table'] == 'prestamos' and 'prestamo_id' in fk['constrained_columns'] for fk in fks)
            
            if not fk_exists:
                print("✅ Agregando ForeignKey prestamos_auditoria.prestamo_id → prestamos.id...")
                op.create_foreign_key(
                    'fk_prestamos_auditoria_prestamo',
                    'prestamos_auditoria',
                    'prestamos',
                    ['prestamo_id'],
                    ['id'],
                    ondelete='CASCADE'
                )
                print("✅ ForeignKey prestamos_auditoria.prestamo_id creado")
        except Exception as e:
            print(f"⚠️ Error al crear FK prestamos_auditoria.prestamo_id: {e}")
    else:
        print("⏭️  Omitiendo ForeignKey prestamos_auditoria (tabla no existe)")


def downgrade():
    """Revertir ForeignKeys críticos"""
    connection = op.get_bind()
    inspector = inspect(connection)

    # Eliminar ForeignKeys en orden inverso (solo si las tablas existen)
    tables = inspector.get_table_names()
    
    if 'prestamos_auditoria' in tables:
        try:
            op.drop_constraint('fk_prestamos_auditoria_prestamo', 'prestamos_auditoria', type_='foreignkey')
            print("✅ ForeignKey prestamos_auditoria.prestamo_id eliminado")
        except Exception:
            pass

    if 'pagos_auditoria' in tables:
        try:
            op.drop_constraint('fk_pagos_auditoria_pago', 'pagos_auditoria', type_='foreignkey')
            print("✅ ForeignKey pagos_auditoria.pago_id eliminado")
        except Exception:
            pass

    try:
        op.drop_constraint('fk_prestamos_evaluacion_prestamo', 'prestamos_evaluacion', type_='foreignkey')
        print("✅ ForeignKey prestamos_evaluacion.prestamo_id eliminado")
    except Exception:
        pass

    try:
        op.drop_constraint('fk_pagos_cliente', 'pagos', type_='foreignkey')
        print("✅ ForeignKey pagos.cliente_id eliminado")
    except Exception:
        pass

    try:
        op.drop_constraint('fk_pagos_prestamo', 'pagos', type_='foreignkey')
        print("✅ ForeignKey pagos.prestamo_id eliminado")
    except Exception:
        pass

    # Eliminar columna cliente_id si existe
    pagos_columns = [col['name'] for col in inspector.get_columns('pagos')]
    if 'cliente_id' in pagos_columns:
        try:
            op.drop_index('ix_pagos_cliente_id', table_name='pagos')
            op.drop_column('pagos', 'cliente_id')
            print("✅ Columna cliente_id eliminada de pagos")
        except Exception:
            pass

