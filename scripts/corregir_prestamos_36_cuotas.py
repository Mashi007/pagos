"""
Script para corregir préstamos que se aprobaron con 36 cuotas
cuando deberían tener 12 cuotas

Ejecutar: python scripts/corregir_prestamos_36_cuotas.py
"""

import sys
from pathlib import Path

# Agregar el directorio backend al path
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from datetime import date, timedelta
from decimal import Decimal
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.services.prestamo_amortizacion_service import generar_tabla_amortizacion

# Crear engine y sesión
engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def corregir_prestamos_afectados():
    """Corrige préstamos que se aprobaron con 36 cuotas cuando deberían tener 12"""

    db = SessionLocal()

    try:
        print("=" * 70)
        print("CORRECCIÓN: Préstamos con cuotas incorrectas")
        print("=" * 70)

        # Buscar préstamos afectados
        query = text("""
            SELECT
                id, cedula, nombres, numero_cuotas, total_financiamiento,
                estado, fecha_aprobacion
            FROM prestamos
            WHERE estado = 'APROBADO'
            AND numero_cuotas = 36
            ORDER BY id DESC
        """)

        result = db.execute(query)
        prestamos_afectados = result.fetchall()

        if not prestamos_afectados:
            print("\n✅ No hay préstamos afectados")
            return

        print(f"\n⚠️  Encontrados {len(prestamos_afectados)} préstamos afectados:")
        for p in prestamos_afectados:
            print(f"  - ID {p.id}: {p.nombres} ({p.cedula}) - {p.numero_cuotas} cuotas")

        # Confirmar corrección
        print("\n" + "=" * 70)
        respuesta = input("¿Deseas corregir estos préstamos? (s/n): ")

        if respuesta.lower() != 's':
            print("Operación cancelada")
            return

        # Corregir cada préstamo
        for prestamo in prestamos_afectados:
            print(f"\n📝 Corrigiendo préstamo #{prestamo.id}: {prestamo.nombres}")

            # 1. Eliminar cuotas incorrectas
            delete_query = text("DELETE FROM cuotas WHERE prestamo_id = :prestamo_id")
            db.execute(delete_query, {"prestamo_id": prestamo.id})
            print(f"  ✓ Cuotas eliminadas")

            # 2. Actualizar numero_cuotas a 12
            update_query = text("""
                UPDATE prestamos
                SET
                    numero_cuotas = 12,
                    cuota_periodo = :total / 12.0
                WHERE id = :prestamo_id
            """)
            db.execute(update_query, {
                "prestamo_id": prestamo.id,
                "total": prestamo.total_financiamiento
            })
            print(f"  ✓ numero_cuotas actualizado a 12")

            # 3. Regenerar tabla de amortización con fecha aprobación
            if prestamo.fecha_aprobacion:
                fecha_desembolso = prestamo.fecha_aprobacion + timedelta(days=30)

                # Obtener préstamo actualizado
                prestamo_obj = db.execute(
                    text("SELECT * FROM prestamos WHERE id = :id"),
                    {"id": prestamo.id}
                ).fetchone()

                # Generar cuotas (código simplificado)
                # Esto lo hacemos manualmente porque necesitamos el objeto Prestamo
                print(f"  ⚠️  Necesitas regenerar las cuotas para préstamo {prestamo.id}")
                print(f"      Usa: POST /api/v1/prestamos/{prestamo.id}/generar-amortizacion")

            db.commit()
            print(f"  ✅ Préstamo {prestamo.id} corregido")

        print("\n" + "=" * 70)
        print("✅ CORRECCIÓN COMPLETADA")
        print("=" * 70)
        print("\nNOTA: Necesitas regenerar las tablas de amortización desde el frontend o API")
        print("      para cada préstamo corregido.")
        print("\nComando API para regenerar:")
        for p in prestamos_afectados:
            print(f"  POST /api/v1/prestamos/{p.id}/generar-amortizacion")

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        db.rollback()
        import traceback
        traceback.print_exc()

    finally:
        db.close()

if __name__ == "__main__":
    corregir_prestamos_afectados()

