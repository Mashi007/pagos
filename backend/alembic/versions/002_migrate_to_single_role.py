"""Migrar todos los usuarios al rol USER único

Revision ID: 002_migrate_to_single_role
Revises: 001_expandir_cliente_financiamiento
Create Date: 2025-10-16 08:44:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_migrate_to_single_role'
down_revision = '001_expandir_cliente_financiamiento'
branch_labels = None
depends_on = None


def upgrade():
    """
    Migración para convertir el sistema de múltiples roles a un único rol USER.
    
    Pasos:
    1. Actualizar todos los usuarios existentes al rol 'USER'
    2. Modificar el enum en PostgreSQL para solo tener 'USER'
    """
    
    # Paso 1: Actualizar todos los usuarios al rol USER
    # Esto incluye: ADMINISTRADOR_GENERAL, GERENTE, COBRANZAS, etc.
    op.execute("""
        UPDATE usuarios 
        SET rol = 'USER' 
        WHERE rol IN ('ADMINISTRADOR_GENERAL', 'GERENTE', 'COBRANZAS', 'ADMIN')
    """)
    
    # Paso 2: Recrear el enum con solo USER
    # Primero, convertir la columna a texto temporalmente
    op.execute("ALTER TABLE usuarios ALTER COLUMN rol TYPE VARCHAR(50)")
    
    # Eliminar el enum antiguo
    op.execute("DROP TYPE IF EXISTS userrole")
    
    # Crear el nuevo enum con solo USER
    op.execute("CREATE TYPE userrole AS ENUM ('USER')")
    
    # Convertir la columna de vuelta al enum usando el nuevo tipo
    op.execute("""
        ALTER TABLE usuarios 
        ALTER COLUMN rol TYPE userrole 
        USING rol::text::userrole
    """)
    
    # Paso 3: Asegurar que el usuario correcto existe
    op.execute("""
        INSERT INTO usuarios (
            email, 
            hashed_password, 
            nombre, 
            apellido, 
            telefono, 
            rol, 
            is_active, 
            email_verified
        )
        VALUES (
            'itmaster@rapicreditca.com',
            '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYvIYUX.lHm',
            'IT',
            'Master',
            '1234567890',
            'USER',
            true,
            true
        )
        ON CONFLICT (email) DO UPDATE
        SET 
            rol = 'USER',
            is_active = true,
            email_verified = true
    """)
    
    # Paso 4: Eliminar usuarios incorrectos si existen
    op.execute("""
        DELETE FROM usuarios 
        WHERE email = 'admin@financiamiento.com'
    """)
    
    print("✅ Migración completada:")
    print("   - Todos los usuarios actualizados al rol USER")
    print("   - Enum actualizado a solo USER")
    print("   - Usuario itmaster@rapicreditca.com verificado")
    print("   - Usuario admin@financiamiento.com eliminado")


def downgrade():
    """
    Revertir al sistema de múltiples roles (solo para desarrollo/testing).
    NO SE RECOMIENDA usar en producción.
    """
    
    # Convertir la columna a texto temporalmente
    op.execute("ALTER TABLE usuarios ALTER COLUMN rol TYPE VARCHAR(50)")
    
    # Eliminar el enum actual
    op.execute("DROP TYPE IF EXISTS userrole")
    
    # Recrear el enum con los roles antiguos
    op.execute("""
        CREATE TYPE userrole AS ENUM (
            'USER', 
            'ADMINISTRADOR_GENERAL', 
            'GERENTE', 
            'COBRANZAS'
        )
    """)
    
    # Convertir la columna de vuelta al enum
    op.execute("""
        ALTER TABLE usuarios 
        ALTER COLUMN rol TYPE userrole 
        USING rol::text::userrole
    """)
    
    print("⚠️  Downgrade completado - sistema revertido a múltiples roles")

