"""
Script para aplicar pagos pendientes a cuotas
Identifica pagos que tienen prestamo_id pero no se aplicaron a cuotas
y los reaplica usando el endpoint API o la función directamente
"""

import sys
import os
from pathlib import Path
import urllib.parse

# Manejar encoding para Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, "strict")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, "strict")

# Agregar el directorio backend al path
backend_dir = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.session import SessionLocal
from app.models.pago import Pago
from app.models.prestamo import Prestamo
from app.models.amortizacion import Cuota
from app.api.v1.endpoints.pagos import aplicar_pago_a_cuotas
from app.models.user import User


def create_safe_session():
    """Crea una sesión de base de datos con manejo robusto de encoding"""
    try:
        # Intentar obtener DATABASE_URL de múltiples fuentes
        database_url = None

        # Primero desde variables de entorno (raw)
        try:
            raw_url = os.getenv("DATABASE_URL")
            if raw_url:
                if isinstance(raw_url, bytes):
                    try:
                        database_url = raw_url.decode('utf-8')
                    except UnicodeDecodeError:
                        database_url = raw_url.decode('latin1', errors='replace')
                else:
                    database_url = raw_url
        except:
            pass

        # Si no está disponible, intentar desde settings
        if not database_url:
            try:
                from app.core.config import settings
                database_url = getattr(settings, 'DATABASE_URL', None)
                if isinstance(database_url, bytes):
                    try:
                        database_url = database_url.decode('utf-8')
                    except UnicodeDecodeError:
                        database_url = database_url.decode('latin1', errors='replace')
            except:
                pass

        if not database_url:
            print("⚠️ No se encontró DATABASE_URL, usando SessionLocal")
            return SessionLocal()

        # Parsear y reconstruir la URL de forma segura
        try:
            parsed = urllib.parse.urlparse(str(database_url))

            # Re-codificar componentes de manera segura
            if parsed.password:
                password = urllib.parse.quote(str(parsed.password), safe='')
            else:
                password = ''

            if parsed.username:
                username = urllib.parse.quote(str(parsed.username), safe='')
            else:
                username = ''

            # Reconstruir URL
            netloc = f"{username}:{password}@{parsed.hostname}" if username or password else parsed.hostname
            if parsed.port:
                netloc += f":{parsed.port}"

            database_url = urllib.parse.urlunparse((
                parsed.scheme,
                netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment
            ))
        except Exception as e:
            print(f"⚠️ Error parseando DATABASE_URL: {e}, usando SessionLocal")
            return SessionLocal()

        # Configurar connect_args para PostgreSQL
        connect_args = {}
        if database_url.startswith("postgresql"):
            connect_args = {
                "client_encoding": "UTF8",
                "connect_timeout": 10
            }

        # Crear engine
        engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_recycle=300,
            echo=False,
            connect_args=connect_args,
            pool_reset_on_return="commit",
        )

        # Crear y retornar sesión
        SessionMaker = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return SessionMaker()

    except Exception as e:
        print(f"⚠️ Error en create_safe_session: {e}")
        print("Usando SessionLocal como fallback...")
        return SessionLocal()


def identificar_pagos_pendientes(db: Session):
    """Identifica pagos que tienen prestamo_id pero no se aplicaron a cuotas"""
    print("🔍 Identificando pagos pendientes...")

    # Estrategia simple: obtener todos los pagos con prestamo_id
    # La función aplicar_pago_a_cuotas ya maneja si el pago ya fue aplicado
    # Si el préstamo no tiene cuotas, la función retornará 0 pero no fallará
    pagos_pendientes = db.query(Pago).filter(
        Pago.prestamo_id.isnot(None),
        Pago.monto_pagado > 0
    ).order_by(Pago.fecha_pago.asc(), Pago.id.asc()).all()

    print(f"📊 Encontrados {len(pagos_pendientes)} pagos con prestamo_id para procesar")
    return pagos_pendientes


def aplicar_pago_a_cuotas_directo(pago: Pago, db: Session):
    """Aplica un pago directamente a las cuotas"""
    try:
        # Intentar obtener un usuario real del sistema, o crear uno temporal
        from app.models.user import User

        # Buscar cualquier usuario en la BD
        user = db.query(User).first()

        if not user:
            # Si no hay usuarios, crear uno temporal (solo para este proceso, NO se guarda en BD)
            # Usar campos mínimos requeridos según el modelo
            user = type('UserDummy', (), {
                'email': 'sistema@aplicacion-pagos-automatico',
                'id': 0,
                'nombre': 'Sistema',
                'apellido': 'Automatico'
            })()

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
    # Usar SessionLocal directamente (ya tiene encoding configurado)
    db: Session = SessionLocal()

    try:
        print("=" * 60)
        print("APLICAR PAGOS PENDIENTES A CUOTAS")
        print("=" * 60)

        # Identificar pagos pendientes
        pagos_pendientes = identificar_pagos_pendientes(db)

        if not pagos_pendientes:
            print("✅ No hay pagos pendientes para aplicar")
            return

        print(f"\n📋 Aplicando {len(pagos_pendientes)} pagos pendientes...")
        print("-" * 60)

        aplicados = 0
        errores = 0

        for pago in pagos_pendientes:
            print(f"🔄 Procesando pago ID {pago.id} (Préstamo {pago.prestamo_id}, ${pago.monto_pagado})...")

            if aplicar_pago_a_cuotas_directo(pago, db):
                aplicados += 1
            else:
                errores += 1

        print("-" * 60)
        print(f"✅ Resumen:")
        print(f"   - Aplicados exitosamente: {aplicados}")
        print(f"   - Errores: {errores}")
        print("=" * 60)

    except Exception as e:
        print(f"❌ Error general: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()

