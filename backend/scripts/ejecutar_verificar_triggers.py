"""
Script para ejecutar la verificación de triggers en la tabla users
Ejecuta el script SQL verificar_triggers_users.sql y muestra los resultados
"""

import sys
import os
from pathlib import Path

# Configurar encoding UTF-8 para Windows (solo para stdout, no para la conexión DB)
if sys.platform == 'win32':
    try:
        import codecs
        if hasattr(sys.stdout, 'buffer'):
            sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')
        if hasattr(sys.stderr, 'buffer'):
            sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'replace')
    except Exception:
        pass  # Si falla, continuar sin cambiar encoding

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.db.session import SessionLocal, engine
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def ejecutar_verificacion_triggers():
    """Ejecuta las consultas de verificación de triggers"""

    try:
        # Intentar crear la sesión
        db = SessionLocal()
        # Probar la conexión
        db.execute(text("SELECT 1"))
    except Exception as conn_error:
        print(f"[ERROR] No se pudo conectar a la base de datos: {conn_error}")
        print("\nPor favor verifica:")
        print("1. Que la variable de entorno DATABASE_URL esté configurada correctamente")
        print("2. Que la base de datos esté accesible")
        print("3. Que las credenciales sean correctas")
        return

    try:
        print("=" * 80)
        print("VERIFICACION DE TRIGGERS EN LA TABLA USERS")
        print("=" * 80)
        print()

        # 1. Verificar triggers relacionados con la tabla 'users'
        print("1. TRIGGERS EN LA TABLA 'users':")
        print("-" * 80)
        query1 = text("""
            SELECT
                trigger_name,
                event_manipulation,
                event_object_table,
                action_statement,
                action_timing,
                action_orientation
            FROM information_schema.triggers
            WHERE event_object_table = 'users'
            ORDER BY trigger_name;
        """)
        result1 = db.execute(query1)
        triggers = result1.fetchall()

        if triggers:
            for trigger in triggers:
                print(f"  [OK] Trigger encontrado: {trigger.trigger_name}")
                print(f"     - Evento: {trigger.event_manipulation}")
                print(f"     - Timing: {trigger.action_timing}")
                print(f"     - Statement: {trigger.action_statement[:100]}...")
                print()
        else:
            print("  [OK] No se encontraron triggers en la tabla 'users'")
        print()

        # 2. Verificar funciones que puedan estar relacionadas con users
        print("2. FUNCIONES RELACIONADAS CON 'users' O 'cargo':")
        print("-" * 80)
        query2 = text("""
            SELECT
                routine_name,
                routine_type,
                routine_definition
            FROM information_schema.routines
            WHERE routine_definition LIKE '%users%'
               OR routine_definition LIKE '%cargo%'
            ORDER BY routine_name;
        """)
        result2 = db.execute(query2)
        funciones = result2.fetchall()

        if funciones:
            for func in funciones:
                print(f"  [ADVERTENCIA] Funcion encontrada: {func.routine_name} ({func.routine_type})")
                print(f"     - Definicion: {func.routine_definition[:150]}...")
                print()
        else:
            print("  [OK] No se encontraron funciones relacionadas con 'users' o 'cargo'")
        print()

        # 3. Verificar constraints o defaults en la columna cargo
        print("3. INFORMACION DE LA COLUMNA 'cargo':")
        print("-" * 80)
        query3 = text("""
            SELECT
                column_name,
                column_default,
                is_nullable,
                data_type
            FROM information_schema.columns
            WHERE table_name = 'users'
              AND column_name = 'cargo';
        """)
        result3 = db.execute(query3)
        columna = result3.fetchone()

        if columna:
            print("  [OK] Columna 'cargo' encontrada:")
            print(f"     - Tipo de dato: {columna.data_type}")
            print(f"     - Nullable: {columna.is_nullable}")
            print(f"     - Default: {columna.column_default or 'NULL'}")
        else:
            print("  [ADVERTENCIA] Columna 'cargo' no encontrada")
        print()

        # 4. Verificar constraints relacionados con cargo
        print("4. CONSTRAINTS RELACIONADOS CON 'cargo':")
        print("-" * 80)
        query4 = text("""
            SELECT
                conname AS constraint_name,
                contype AS constraint_type,
                pg_get_constraintdef(oid) AS constraint_definition
            FROM pg_constraint
            WHERE conrelid = 'users'::regclass
              AND (pg_get_constraintdef(oid) LIKE '%cargo%' OR conname LIKE '%cargo%');
        """)
        result4 = db.execute(query4)
        constraints = result4.fetchall()

        if constraints:
            for constraint in constraints:
                print(f"  [ADVERTENCIA] Constraint encontrado: {constraint.constraint_name}")
                print(f"     - Tipo: {constraint.constraint_type}")
                print(f"     - Definicion: {constraint.constraint_definition}")
                print()
        else:
            print("  [OK] No se encontraron constraints relacionados con 'cargo'")
        print()

        # 5. Verificar valores actuales de cargo en la tabla users
        print("5. VALORES ACTUALES DE 'cargo' EN LA TABLA 'users':")
        print("-" * 80)
        query5 = text("""
            SELECT
                id,
                email,
                nombre,
                apellido,
                cargo,
                CASE
                    WHEN cargo IS NULL THEN 'NULL'
                    WHEN cargo = '' THEN 'VACÍO'
                    ELSE cargo
                END AS cargo_estado
            FROM users
            ORDER BY id;
        """)
        result5 = db.execute(query5)
        usuarios = result5.fetchall()

        if usuarios:
            print(f"  Total de usuarios: {len(usuarios)}")
            print()
            for usuario in usuarios:
                cargo_display = usuario.cargo if usuario.cargo else "NULL"
                print(f"  - ID {usuario.id}: {usuario.nombre} {usuario.apellido} ({usuario.email})")
                print(f"    Cargo: {cargo_display}")
            print()
        else:
            print("  [ADVERTENCIA] No se encontraron usuarios en la tabla")
        print()

        print("=" * 80)
        print("[OK] Verificacion completada")
        print("=" * 80)

    except Exception as e:
        logger.error(f"Error ejecutando verificacion: {e}")
        print(f"\n[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    try:
        ejecutar_verificacion_triggers()
    except KeyboardInterrupt:
        print("\n\n[ADVERTENCIA] Verificacion cancelada por el usuario")
    except Exception as e:
        print(f"\n\n[ERROR] Error fatal: {e}")
        import traceback
        traceback.print_exc()
