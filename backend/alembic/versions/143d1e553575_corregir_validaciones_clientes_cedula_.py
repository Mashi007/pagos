"""corregir_validaciones_clientes_cedula_email_estado

Revision ID: 143d1e553575
Revises: 8fe8e0281801
Create Date: 2025-12-11 00:10:34.989460

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '143d1e553575'
down_revision: Union[str, None] = '8fe8e0281801'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Aplicar cambios a la base de datos."""
    
    # 1. Eliminar restricciones CHECK antiguas
    op.execute("""
        ALTER TABLE clientes 
        DROP CONSTRAINT IF EXISTS chk_cedula_longitud;
    """)
    
    op.execute("""
        ALTER TABLE clientes 
        DROP CONSTRAINT IF EXISTS chk_telefono_longitud;
    """)
    
    op.execute("""
        ALTER TABLE clientes 
        DROP CONSTRAINT IF EXISTS chk_email_valido;
    """)
    
    op.execute("""
        ALTER TABLE clientes 
        DROP CONSTRAINT IF EXISTS chk_estado_valido;
    """)
    
    op.execute("""
        ALTER TABLE clientes 
        DROP CONSTRAINT IF EXISTS chk_fecha_nacimiento_valida;
    """)
    
    # 2. Crear nuevas restricciones CHECK
    
    # Cédula: 6 a 13 caracteres, sin guiones
    op.execute("""
        ALTER TABLE clientes 
        ADD CONSTRAINT chk_cedula_longitud 
        CHECK (length(cedula) >= 6 AND length(cedula) <= 13);
    """)
    
    op.execute("""
        ALTER TABLE clientes 
        ADD CONSTRAINT chk_cedula_sin_guiones 
        CHECK (cedula !~ '-');
    """)
    
    # Teléfono: mantener validación existente (8-15 caracteres)
    op.execute("""
        ALTER TABLE clientes 
        ADD CONSTRAINT chk_telefono_longitud 
        CHECK (length(telefono) >= 8 AND length(telefono) <= 15);
    """)
    
    # Email: formato válido (se normalizará a minúsculas con trigger)
    op.execute("""
        ALTER TABLE clientes 
        ADD CONSTRAINT chk_email_valido 
        CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$');
    """)
    
    # Estado: solo ACTIVO, INACTIVO, FINALIZADO (con default ACTIVO si es NULL)
    op.execute("""
        ALTER TABLE clientes 
        ADD CONSTRAINT chk_estado_valido 
        CHECK (estado = ANY (ARRAY['ACTIVO'::character varying, 'INACTIVO'::character varying, 'FINALIZADO'::character varying]));
    """)
    
    # Fecha nacimiento: no puede ser futura
    op.execute("""
        ALTER TABLE clientes 
        ADD CONSTRAINT chk_fecha_nacimiento_valida 
        CHECK (fecha_nacimiento <= CURRENT_DATE);
    """)
    
    # 3. Crear función para normalizar email a minúsculas
    op.execute("""
        CREATE OR REPLACE FUNCTION normalize_clientes_email()
        RETURNS TRIGGER AS $$
        BEGIN
            -- Normalizar email a minúsculas
            IF NEW.email IS NOT NULL THEN
                NEW.email = LOWER(TRIM(NEW.email));
            END IF;
            
            -- Normalizar cédula: eliminar guiones y espacios
            IF NEW.cedula IS NOT NULL THEN
                NEW.cedula = REPLACE(REPLACE(TRIM(NEW.cedula), '-', ''), ' ', '');
            END IF;
            
            -- Si estado es NULL, establecer ACTIVO por defecto
            IF NEW.estado IS NULL THEN
                NEW.estado = 'ACTIVO';
                NEW.activo = true;
            END IF;
            
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    # 4. Crear trigger para normalizar email y cédula antes de insertar/actualizar
    op.execute("""
        DROP TRIGGER IF EXISTS trigger_normalize_clientes_email ON clientes;
    """)
    
    op.execute("""
        CREATE TRIGGER trigger_normalize_clientes_email
        BEFORE INSERT OR UPDATE ON clientes
        FOR EACH ROW
        EXECUTE FUNCTION normalize_clientes_email();
    """)
    
    # 5. Actualizar datos existentes: normalizar emails a minúsculas y cédulas sin guiones
    op.execute("""
        UPDATE clientes 
        SET email = LOWER(TRIM(email)),
            cedula = REPLACE(REPLACE(TRIM(cedula), '-', ''), ' ', '')
        WHERE email != LOWER(TRIM(email))
           OR cedula != REPLACE(REPLACE(TRIM(cedula), '-', ''), ' ', '');
    """)
    
    # 6. Actualizar estados NULL a ACTIVO
    op.execute("""
        UPDATE clientes 
        SET estado = 'ACTIVO', activo = true
        WHERE estado IS NULL;
    """)


def downgrade() -> None:
    """Revertir cambios de la base de datos."""
    
    # Eliminar trigger
    op.execute("""
        DROP TRIGGER IF EXISTS trigger_normalize_clientes_email ON clientes;
    """)
    
    # Eliminar función
    op.execute("""
        DROP FUNCTION IF EXISTS normalize_clientes_email();
    """)
    
    # Eliminar nuevas restricciones
    op.execute("""
        ALTER TABLE clientes 
        DROP CONSTRAINT IF EXISTS chk_cedula_longitud;
    """)
    
    op.execute("""
        ALTER TABLE clientes 
        DROP CONSTRAINT IF EXISTS chk_cedula_sin_guiones;
    """)
    
    op.execute("""
        ALTER TABLE clientes 
        DROP CONSTRAINT IF EXISTS chk_telefono_longitud;
    """)
    
    op.execute("""
        ALTER TABLE clientes 
        DROP CONSTRAINT IF EXISTS chk_email_valido;
    """)
    
    op.execute("""
        ALTER TABLE clientes 
        DROP CONSTRAINT IF EXISTS chk_estado_valido;
    """)
    
    op.execute("""
        ALTER TABLE clientes 
        DROP CONSTRAINT IF EXISTS chk_fecha_nacimiento_valida;
    """)
    
    # Restaurar restricciones antiguas (8-20 caracteres para cédula)
    op.execute("""
        ALTER TABLE clientes 
        ADD CONSTRAINT chk_cedula_longitud 
        CHECK (length(cedula) >= 8 AND length(cedula) <= 20);
    """)
    
    op.execute("""
        ALTER TABLE clientes 
        ADD CONSTRAINT chk_telefono_longitud 
        CHECK (length(telefono) >= 8 AND length(telefono) <= 15);
    """)
    
    op.execute("""
        ALTER TABLE clientes 
        ADD CONSTRAINT chk_email_valido 
        CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}$');
    """)
    
    op.execute("""
        ALTER TABLE clientes 
        ADD CONSTRAINT chk_estado_valido 
        CHECK (estado = ANY (ARRAY['ACTIVO'::character varying, 'INACTIVO'::character varying, 'FINALIZADO'::character varying]));
    """)
    
    op.execute("""
        ALTER TABLE clientes 
        ADD CONSTRAINT chk_fecha_nacimiento_valida 
        CHECK (fecha_nacimiento <= CURRENT_DATE);
    """)
