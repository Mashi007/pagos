"""
Script rápido para verificar el estado de los préstamos
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from datetime import date

from app.database import SessionLocal
from app.models.prestamo import Prestamo


def verificar_rapido():
    """Verificación rápida del estado de préstamos"""
    print("=" * 80)
    print("🔍 VERIFICACIÓN RÁPIDA: Préstamos en la Base de Datos")
    print("=" * 80)
    print()

    db: Session = SessionLocal()
    try:
        # 1. Total de préstamos
        total = db.query(Prestamo).count()
        print(f"📊 Total de préstamos en BD: {total:,}")
        print()

        # 2. Por estado
        print("📊 Por estado:")
        estados = db.query(Prestamo.estado, func.count(Prestamo.id)).group_by(Prestamo.estado).all()
        for estado, count in estados:
            print(f"   • {estado}: {count:,}")
        print()

        # 3. Préstamos aprobados
        aprobados = db.query(Prestamo).filter(Prestamo.estado == "APROBADO").count()
        print(f"✅ Préstamos con estado='APROBADO': {aprobados:,}")
        print()

        # 4. Préstamos aprobados con total_financiamiento válido
        validos = db.query(Prestamo).filter(
            and_(
                Prestamo.estado == "APROBADO",
                Prestamo.total_financiamiento.isnot(None),
                Prestamo.total_financiamiento > 0
            )
        ).count()
        print(f"✅ Préstamos aprobados con total_financiamiento > 0: {validos:,}")
        print()

        # 5. Análisis de fechas
        hoy = date.today()
        año_actual = hoy.year
        fecha_inicio = date(año_actual, 1, 1)
        fecha_fin = date(año_actual, 12, 31)

        print(f"📅 Verificando rango del año {año_actual}: {fecha_inicio} a {fecha_fin}")
        print()

        # Con al menos una fecha en el rango
        en_rango = db.query(Prestamo).filter(
            and_(
                Prestamo.estado == "APROBADO",
                Prestamo.total_financiamiento.isnot(None),
                Prestamo.total_financiamiento > 0,
                or_(
                    and_(
                        Prestamo.fecha_registro.isnot(None),
                        Prestamo.fecha_registro >= fecha_inicio,
                        Prestamo.fecha_registro <= fecha_fin
                    ),
                    and_(
                        Prestamo.fecha_aprobacion.isnot(None),
                        Prestamo.fecha_aprobacion >= fecha_inicio,
                        Prestamo.fecha_aprobacion <= fecha_fin
                    ),
                    and_(
                        Prestamo.fecha_base_calculo.isnot(None),
                        Prestamo.fecha_base_calculo >= fecha_inicio,
                        Prestamo.fecha_base_calculo <= fecha_fin
                    )
                )
            )
        ).count()
        print(f"✅ Préstamos válidos en rango del año {año_actual}: {en_rango:,}")
        print()

        # 6. Sin filtros de fecha
        sin_filtro_fecha = db.query(Prestamo).filter(
            and_(
                Prestamo.estado == "APROBADO",
                Prestamo.total_financiamiento.isnot(None),
                Prestamo.total_financiamiento > 0
            )
        ).count()
        print(f"✅ Préstamos válidos SIN filtros de fecha: {sin_filtro_fecha:,}")
        print()

        # 7. Análisis de fechas
        print("📅 Análisis de fechas de préstamos válidos:")
        con_fecha_registro = db.query(Prestamo).filter(
            and_(
                Prestamo.estado == "APROBADO",
                Prestamo.total_financiamiento.isnot(None),
                Prestamo.total_financiamiento > 0,
                Prestamo.fecha_registro.isnot(None)
            )
        ).count()
        print(f"   • Con fecha_registro: {con_fecha_registro:,}")

        con_fecha_aprobacion = db.query(Prestamo).filter(
            and_(
                Prestamo.estado == "APROBADO",
                Prestamo.total_financiamiento.isnot(None),
                Prestamo.total_financiamiento > 0,
                Prestamo.fecha_aprobacion.isnot(None)
            )
        ).count()
        print(f"   • Con fecha_aprobacion: {con_fecha_aprobacion:,}")

        con_fecha_base = db.query(Prestamo).filter(
            and_(
                Prestamo.estado == "APROBADO",
                Prestamo.total_financiamiento.isnot(None),
                Prestamo.total_financiamiento > 0,
                Prestamo.fecha_base_calculo.isnot(None)
            )
        ).count()
        print(f"   • Con fecha_base_calculo: {con_fecha_base:,}")

        sin_ninguna_fecha = db.query(Prestamo).filter(
            and_(
                Prestamo.estado == "APROBADO",
                Prestamo.total_financiamiento.isnot(None),
                Prestamo.total_financiamiento > 0,
                Prestamo.fecha_registro.is_(None),
                Prestamo.fecha_aprobacion.is_(None),
                Prestamo.fecha_base_calculo.is_(None)
            )
        ).count()
        print(f"   ⚠️  Sin ninguna fecha: {sin_ninguna_fecha:,}")
        print()

        # 8. Rango de fechas
        if validos > 0:
            min_fecha_registro = db.query(func.min(Prestamo.fecha_registro)).filter(
                and_(
                    Prestamo.estado == "APROBADO",
                    Prestamo.total_financiamiento.isnot(None),
                    Prestamo.total_financiamiento > 0,
                    Prestamo.fecha_registro.isnot(None)
                )
            ).scalar()

            max_fecha_registro = db.query(func.max(Prestamo.fecha_registro)).filter(
                and_(
                    Prestamo.estado == "APROBADO",
                    Prestamo.total_financiamiento.isnot(None),
                    Prestamo.total_financiamiento > 0,
                    Prestamo.fecha_registro.isnot(None)
                )
            ).scalar()

            min_fecha_aprobacion = db.query(func.min(Prestamo.fecha_aprobacion)).filter(
                and_(
                    Prestamo.estado == "APROBADO",
                    Prestamo.total_financiamiento.isnot(None),
                    Prestamo.total_financiamiento > 0,
                    Prestamo.fecha_aprobacion.isnot(None)
                )
            ).scalar()

            max_fecha_aprobacion = db.query(func.max(Prestamo.fecha_aprobacion)).filter(
                and_(
                    Prestamo.estado == "APROBADO",
                    Prestamo.total_financiamiento.isnot(None),
                    Prestamo.total_financiamiento > 0,
                    Prestamo.fecha_aprobacion.isnot(None)
                )
            ).scalar()

            print("📅 Rangos de fechas:")
            if min_fecha_registro:
                print(f"   • fecha_registro: {min_fecha_registro} a {max_fecha_registro}")
            if min_fecha_aprobacion:
                print(f"   • fecha_aprobacion: {min_fecha_aprobacion} a {max_fecha_aprobacion}")
            print()

        # 9. Resumen y diagnóstico
        print("=" * 80)
        print("📋 DIAGNÓSTICO:")
        print("=" * 80)
        print()

        if aprobados == 0:
            print("❌ PROBLEMA: No hay préstamos con estado='APROBADO'")
            print(f"   → Total préstamos: {total:,}")
            print(f"   → Estados encontrados: {[e[0] for e in estados]}")
        elif validos == 0:
            print("❌ PROBLEMA: No hay préstamos aprobados con total_financiamiento > 0")
            print(f"   → Préstamos aprobados: {aprobados:,}")
            print("   → Verificar que el campo total_financiamiento esté poblado")
        elif en_rango == 0 and sin_filtro_fecha > 0:
            print("⚠️  PROBLEMA: Los filtros de fecha están excluyendo todos los préstamos")
            print(f"   → Préstamos válidos: {sin_filtro_fecha:,}")
            print(f"   → Préstamos en rango {año_actual}: {en_rango:,}")
            print()
            print("   ✅ SOLUCIÓN: El endpoint debería usar el fallback (sin filtros de fecha)")
            print("   → Verificar logs del backend para ver si el fallback se activó")
        elif en_rango > 0:
            print(f"✅ Todo parece estar bien")
            print(f"   → Préstamos válidos: {sin_filtro_fecha:,}")
            print(f"   → Préstamos en rango {año_actual}: {en_rango:,}")
            print()
            print("   Si el dashboard muestra 0, verificar:")
            print("   1. Logs del backend para errores")
            print("   2. Que el endpoint esté funcionando correctamente")
            print("   3. Que el frontend esté enviando los parámetros correctos")
        else:
            print(f"⚠️  No hay préstamos válidos en ningún caso")
            print(f"   → Préstamos válidos: {sin_filtro_fecha:,}")

        print()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    verificar_rapido()

