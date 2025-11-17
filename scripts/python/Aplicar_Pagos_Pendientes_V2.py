"""
Script para aplicar pagos pendientes a cuotas (VERSION CORREGIDA)
Identifica pagos que tienen prestamo_id pero no se aplicaron a cuotas
"""

import sys
import os
from pathlib import Path

# Manejar encoding para Windows PRIMERO (antes de cualquier import)
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

# Agregar el directorio backend al path
backend_dir = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session
from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
import urllib.parse

# Importar modelos y funciones DESPUÉS de configurar encoding
from app.models.pago import Pago
from app.models.prestamo import Prestamo
from app.models.amortizacion import Cuota
from app.models.user import User

# Importar la función de aplicar pagos
from app.api.v1.endpoints.pagos import aplicar_pago_a_cuotas


def get_safe_database_url():
    """Obtiene DATABASE_URL de forma segura"""
    try:
        from app.core.config import settings
        database_url = os.getenv("DATABASE_URL", getattr(settings, 'DATABASE_URL', None))
    except:
        database_url = os.getenv("DATABASE_URL")

    if not database_url:
        return None

    # Decodificar si es bytes
    if isinstance(database_url, bytes):
        try:
            database_url = database_url.decode('utf-8')
        except UnicodeDecodeError:
            database_url = database_url.decode('latin1', errors='replace')

    return str(database_url)


def create_safe_session():
    """Crea una sesión con manejo robusto de encoding"""
    database_url = get_safe_database_url()

    if not database_url:
        # Fallback: usar la configuración del backend directamente
        try:
            from app.db.session import SessionLocal
            return SessionLocal()
        except:
            raise Exception("No se pudo obtener DATABASE_URL ni crear SessionLocal")

    # Parsear y reconstruir URL
    try:
        parsed = urllib.parse.urlparse(database_url)

        if parsed.password:
            password = urllib.parse.quote(str(parsed.password), safe='')
        else:
            password = ''

        if parsed.username:
            username = urllib.parse.quote(str(parsed.username), safe='')
        else:
            username = ''

        netloc = f"{username}:{password}@{parsed.hostname}" if username or password else parsed.hostname
        if parsed.port:
            netloc += f":{parsed.port}"

        safe_url = urllib.parse.urlunparse((
            parsed.scheme,
            netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment
        ))
    except Exception as e:
        print(f"⚠️ Error parseando URL: {e}")
        safe_url = database_url

    # Crear engine con encoding UTF-8
    connect_args = {}
    if safe_url.startswith("postgresql"):
        connect_args = {"client_encoding": "UTF8"}

    engine = create_engine(
        safe_url,
        pool_pre_ping=True,
        pool_recycle=300,
        echo=False,
        connect_args=connect_args,
        pool_reset_on_return="commit",
    )

    SessionMaker = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionMaker()


def identificar_pagos_pendientes(db: Session):
    """Identifica pagos que tienen prestamo_id pero no se aplicaron a cuotas"""
    print("🔍 Identificando pagos pendientes...")

    # Obtener todos los pagos con prestamo_id
    pagos = db.query(Pago).filter(
        Pago.prestamo_id.isnot(None),
        Pago.monto_pagado > 0
    ).order_by(Pago.fecha_pago.asc(), Pago.id.asc()).all()

    print(f"📊 Encontrados {len(pagos)} pagos con prestamo_id para procesar")
    return pagos


def aplicar_pago_a_cuotas_directo(pago: Pago, db: Session):
    """Aplica un pago directamente a las cuotas"""
    try:
        # Obtener un usuario real de la BD
        user = db.query(User).first()

        if not user:
            # Crear objeto temporal (no se guarda en BD)
            class UserDummy:
                def __init__(self):
                    self.email = 'sistema@aplicacion-pagos-automatico'
                    self.id = 0
                    self.nombre = 'Sistema'
                    self.apellido = 'Automatico'

            user = UserDummy()

        cuotas_completadas = aplicar_pago_a_cuotas(pago, db, user)
        db.commit()

        print(f"✅ Pago ID {pago.id} aplicado. Cuotas completadas: {cuotas_completadas}")
        return True
    except Exception as e:
        print(f"❌ Error aplicando pago ID {pago.id}: {str(e)}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False


def main():
    """Función principal"""
    db: Session = None

    try:
        db = create_safe_session()
        print("=" * 60)
        print("APLICAR PAGOS PENDIENTES A CUOTAS")
        print("=" * 60)

        # Identificar pagos pendientes
        pagos_pendientes = identificar_pagos_pendientes(db)

        if not pagos_pendientes:
            print("✅ No hay pagos pendientes para aplicar")
            return

        print(f"\n📋 Aplicando {len(pagos_pendientes)} pagos...")
        print("-" * 60)

        aplicados = 0
        errores = 0

        for i, pago in enumerate(pagos_pendientes, 1):
            if i % 100 == 0:
                print(f"🔄 Progreso: {i}/{len(pagos_pendientes)} pagos procesados...")

            if aplicar_pago_a_cuotas_directo(pago, db):
                aplicados += 1
            else:
                errores += 1

        print("-" * 60)
        print(f"✅ Resumen Final:")
        print(f"   - Aplicados exitosamente: {aplicados}")
        print(f"   - Errores: {errores}")
        print("=" * 60)

    except Exception as e:
        print(f"❌ Error general: {str(e)}")
        import traceback
        traceback.print_exc()
        if db:
            db.rollback()
    finally:
        if db:
            db.close()


if __name__ == "__main__":
    main()

