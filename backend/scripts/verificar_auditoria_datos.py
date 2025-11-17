"""
Script para verificar datos de auditoría en la base de datos
Verifica si las tablas existen y tienen datos
"""

import sys
from pathlib import Path

# Agregar el directorio raíz del proyecto al path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.auditoria import Auditoria
from app.models.prestamo_auditoria import PrestamoAuditoria
from app.models.pago_auditoria import PagoAuditoria


def verificar_auditoria():
    """Verifica el estado de las tablas de auditoría"""
    print("=" * 80)
    print("🔍 VERIFICACIÓN DE DATOS DE AUDITORÍA")
    print("=" * 80)
    print()

    db: Session = SessionLocal()
    try:
        # 1. Verificar que las tablas existan
        print("📋 PASO 1: Verificar existencia de tablas")
        print("-" * 80)
        inspector = inspect(db.bind)
        tablas = inspector.get_table_names()

        tablas_auditoria = {
            "auditoria": "Tabla general de auditoría",
            "prestamos_auditoria": "Auditoría de préstamos",
            "pagos_auditoria": "Auditoría de pagos",
        }

        tablas_existentes = {}
        for tabla, descripcion in tablas_auditoria.items():
            existe = tabla in tablas
            tablas_existentes[tabla] = existe
            if existe:
                print(f"✅ {tabla}: EXISTE - {descripcion}")
            else:
                print(f"❌ {tabla}: NO EXISTE - {descripcion}")

        print()

        # 2. Contar registros en cada tabla
        print("📊 PASO 2: Contar registros en cada tabla")
        print("-" * 80)

        # Tabla auditoria
        if tablas_existentes.get("auditoria"):
            try:
                count_auditoria = db.query(Auditoria).count()
                print(f"✅ Tabla 'auditoria': {count_auditoria:,} registros")

                if count_auditoria > 0:
                    # Mostrar algunos ejemplos
                    ejemplos = db.query(Auditoria).order_by(Auditoria.fecha.desc()).limit(3).all()
                    print(f"   📝 Últimos 3 registros:")
                    for e in ejemplos:
                        print(f"      - ID: {e.id}, Acción: {e.accion}, Módulo: {e.entidad}, Fecha: {e.fecha}")
            except Exception as e:
                print(f"❌ Error consultando 'auditoria': {e}")
        else:
            print("⚠️  Tabla 'auditoria' no existe, no se puede contar")

        # Tabla prestamos_auditoria
        if tablas_existentes.get("prestamos_auditoria"):
            try:
                count_prestamos = db.query(PrestamoAuditoria).count()
                print(f"✅ Tabla 'prestamos_auditoria': {count_prestamos:,} registros")

                if count_prestamos > 0:
                    # Mostrar algunos ejemplos
                    ejemplos = db.query(PrestamoAuditoria).order_by(PrestamoAuditoria.fecha_cambio.desc()).limit(3).all()
                    print(f"   📝 Últimos 3 registros:")
                    for e in ejemplos:
                        print(f"      - ID: {e.id}, Campo: {e.campo_modificado}, Usuario: {e.usuario}, Fecha: {e.fecha_cambio}")
            except Exception as e:
                print(f"❌ Error consultando 'prestamos_auditoria': {e}")
        else:
            print("⚠️  Tabla 'prestamos_auditoria' no existe, no se puede contar")

        # Tabla pagos_auditoria
        if tablas_existentes.get("pagos_auditoria"):
            try:
                count_pagos = db.query(PagoAuditoria).count()
                print(f"✅ Tabla 'pagos_auditoria': {count_pagos:,} registros")

                if count_pagos > 0:
                    # Mostrar algunos ejemplos
                    ejemplos = db.query(PagoAuditoria).order_by(PagoAuditoria.fecha_cambio.desc()).limit(3).all()
                    print(f"   📝 Últimos 3 registros:")
                    for e in ejemplos:
                        print(f"      - ID: {e.id}, Campo: {e.campo_modificado}, Usuario: {e.usuario}, Fecha: {e.fecha_cambio}")
            except Exception as e:
                print(f"❌ Error consultando 'pagos_auditoria': {e}")
        else:
            print("⚠️  Tabla 'pagos_auditoria' no existe, no se puede contar")

        print()

        # 3. Total unificado
        print("📊 PASO 3: Total unificado de auditoría")
        print("-" * 80)
        total = 0
        if tablas_existentes.get("auditoria"):
            try:
                total += db.query(Auditoria).count()
            except:
                pass
        if tablas_existentes.get("prestamos_auditoria"):
            try:
                total += db.query(PrestamoAuditoria).count()
            except:
                pass
        if tablas_existentes.get("pagos_auditoria"):
            try:
                total += db.query(PagoAuditoria).count()
            except:
                pass

        print(f"📈 Total de registros de auditoría: {total:,}")
        print()

        # 4. Verificar estructura de tablas
        print("🔧 PASO 4: Verificar estructura de tablas")
        print("-" * 80)
        for tabla in tablas_auditoria.keys():
            if tablas_existentes.get(tabla):
                try:
                    columnas = inspector.get_columns(tabla)
                    print(f"✅ {tabla}: {len(columnas)} columnas")
                    # Mostrar columnas principales
                    nombres = [col["name"] for col in columnas[:5]]
                    print(f"   Columnas principales: {', '.join(nombres)}...")
                except Exception as e:
                    print(f"❌ Error verificando estructura de '{tabla}': {e}")

        print()

        # 5. Recomendaciones
        print("💡 RECOMENDACIONES")
        print("-" * 80)
        if total == 0:
            print("⚠️  No hay registros de auditoría en ninguna tabla.")
            print()
            print("   Posibles causas:")
            print("   1. El sistema no está registrando auditoría automáticamente")
            print("   2. No se han realizado acciones que generen auditoría")
            print("   3. Las tablas están vacías porque es un sistema nuevo")
            print()
            print("   Para generar datos de prueba:")
            print("   - Realizar acciones en el sistema (crear/editar préstamos, pagos, etc.)")
            print("   - Hacer login/logout (debería registrar en tabla 'auditoria')")
            print("   - Exportar reportes (debería registrar en tabla 'auditoria')")
        else:
            print(f"✅ Hay {total:,} registros de auditoría disponibles")
            print("   El dashboard debería mostrar estos datos correctamente")

        print()
        print("=" * 80)
        print("✅ VERIFICACIÓN COMPLETADA")
        print("=" * 80)

    except Exception as e:
        print(f"❌ Error durante la verificación: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    verificar_auditoria()

