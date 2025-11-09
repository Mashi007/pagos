"""
🔍 AUDITORÍA COMPLETA: Endpoint financiamiento-por-rangos
Script para diagnosticar por qué el endpoint retorna 0 préstamos
"""

import sys
from pathlib import Path
from datetime import date, datetime

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from decimal import Decimal

from app.database import SessionLocal
from app.models.prestamo import Prestamo
from app.utils.filtros_dashboard import FiltrosDashboard


def auditoria_completa():
    """Realiza auditoría completa del endpoint financiamiento-por-rangos"""
    print("=" * 80)
    print("🔍 AUDITORÍA COMPLETA: Endpoint financiamiento-por-rangos")
    print("=" * 80)
    print()

    db: Session = SessionLocal()
    try:
        # 1. VERIFICAR PRÉSTAMOS APROBADOS EN TOTAL
        print("📊 PASO 1: Verificar préstamos aprobados en la BD")
        print("-" * 80)
        total_aprobados = db.query(Prestamo).filter(Prestamo.estado == "APROBADO").count()
        print(f"✅ Total préstamos con estado='APROBADO': {total_aprobados:,}")
        
        if total_aprobados == 0:
            total_todos = db.query(Prestamo).count()
            print(f"⚠️  No hay préstamos APROBADOS. Total préstamos en BD: {total_todos:,}")
            print("   → PROBLEMA: No hay préstamos aprobados en la base de datos")
            return
        
        print()

        # 2. VERIFICAR PRÉSTAMOS CON total_financiamiento VÁLIDO
        print("📊 PASO 2: Verificar préstamos con total_financiamiento > 0")
        print("-" * 80)
        prestamos_validos = db.query(Prestamo).filter(
            and_(
                Prestamo.estado == "APROBADO",
                Prestamo.total_financiamiento.isnot(None),
                Prestamo.total_financiamiento > 0
            )
        ).count()
        print(f"✅ Préstamos aprobados con total_financiamiento > 0: {prestamos_validos:,}")
        
        prestamos_null = db.query(Prestamo).filter(
            and_(
                Prestamo.estado == "APROBADO",
                Prestamo.total_financiamiento.is_(None)
            )
        ).count()
        print(f"⚠️  Préstamos aprobados con total_financiamiento NULL: {prestamos_null:,}")
        
        prestamos_cero = db.query(Prestamo).filter(
            and_(
                Prestamo.estado == "APROBADO",
                Prestamo.total_financiamiento == 0
            )
        ).count()
        print(f"⚠️  Préstamos aprobados con total_financiamiento = 0: {prestamos_cero:,}")
        
        if prestamos_validos == 0:
            print("   → PROBLEMA: No hay préstamos con total_financiamiento > 0")
            return
        
        print()

        # 3. VERIFICAR FECHAS DE PRÉSTAMOS
        print("📊 PASO 3: Análisis de fechas de préstamos")
        print("-" * 80)
        hoy = date.today()
        año_actual = hoy.year
        
        # Préstamos con fecha_registro
        con_fecha_registro = db.query(Prestamo).filter(
            and_(
                Prestamo.estado == "APROBADO",
                Prestamo.total_financiamiento.isnot(None),
                Prestamo.total_financiamiento > 0,
                Prestamo.fecha_registro.isnot(None)
            )
        ).count()
        print(f"✅ Con fecha_registro: {con_fecha_registro:,}")
        
        # Préstamos con fecha_aprobacion
        con_fecha_aprobacion = db.query(Prestamo).filter(
            and_(
                Prestamo.estado == "APROBADO",
                Prestamo.total_financiamiento.isnot(None),
                Prestamo.total_financiamiento > 0,
                Prestamo.fecha_aprobacion.isnot(None)
            )
        ).count()
        print(f"✅ Con fecha_aprobacion: {con_fecha_aprobacion:,}")
        
        # Préstamos con fecha_base_calculo
        con_fecha_base = db.query(Prestamo).filter(
            and_(
                Prestamo.estado == "APROBADO",
                Prestamo.total_financiamiento.isnot(None),
                Prestamo.total_financiamiento > 0,
                Prestamo.fecha_base_calculo.isnot(None)
            )
        ).count()
        print(f"✅ Con fecha_base_calculo: {con_fecha_base:,}")
        
        # Préstamos SIN ninguna fecha
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
        print(f"⚠️  Sin ninguna fecha (todas NULL): {sin_ninguna_fecha:,}")
        
        print()

        # 4. VERIFICAR PRÉSTAMOS EN RANGO DEL AÑO ACTUAL
        print("📊 PASO 4: Verificar préstamos en rango del año actual (2025)")
        print("-" * 80)
        fecha_inicio_año = date(año_actual, 1, 1)
        fecha_fin_año = date(año_actual, 12, 31)
        
        print(f"Rango: {fecha_inicio_año} a {fecha_fin_año}")
        
        # Con filtros de fecha (usando FiltrosDashboard)
        query_con_fecha = db.query(Prestamo).filter(Prestamo.estado == "APROBADO")
        query_con_fecha = FiltrosDashboard.aplicar_filtros_prestamo(
            query_con_fecha, None, None, None, fecha_inicio_año, fecha_fin_año
        )
        query_con_fecha = query_con_fecha.filter(
            and_(Prestamo.total_financiamiento.isnot(None), Prestamo.total_financiamiento > 0)
        )
        prestamos_en_rango = query_con_fecha.count()
        print(f"✅ Préstamos válidos en rango del año actual: {prestamos_en_rango:,}")
        
        # Sin filtros de fecha
        query_sin_fecha = db.query(Prestamo).filter(
            and_(
                Prestamo.estado == "APROBADO",
                Prestamo.total_financiamiento.isnot(None),
                Prestamo.total_financiamiento > 0
            )
        )
        prestamos_sin_filtro_fecha = query_sin_fecha.count()
        print(f"✅ Préstamos válidos sin filtros de fecha: {prestamos_sin_filtro_fecha:,}")
        
        if prestamos_en_rango == 0 and prestamos_sin_filtro_fecha > 0:
            print(f"⚠️  PROBLEMA: Los filtros de fecha están excluyendo todos los préstamos")
            print(f"   → El endpoint debería usar datos sin filtros de fecha como fallback")
        
        print()

        # 5. VERIFICAR RANGOS DE FECHAS DE PRÉSTAMOS
        print("📊 PASO 5: Análisis de rangos de fechas")
        print("-" * 80)
        
        # Obtener fechas mínimas y máximas
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
        
        print(f"📅 fecha_registro: {min_fecha_registro} a {max_fecha_registro}")
        print(f"📅 fecha_aprobacion: {min_fecha_aprobacion} a {max_fecha_aprobacion}")
        
        if min_fecha_registro and min_fecha_registro.year > año_actual:
            print(f"⚠️  PROBLEMA: La fecha_registro mínima ({min_fecha_registro}) es mayor al año actual")
        if min_fecha_aprobacion and min_fecha_aprobacion.year > año_actual:
            print(f"⚠️  PROBLEMA: La fecha_aprobacion mínima ({min_fecha_aprobacion}) es mayor al año actual")
        
        print()

        # 6. RESUMEN Y RECOMENDACIONES
        print("📋 RESUMEN Y RECOMENDACIONES")
        print("=" * 80)
        print()
        
        if total_aprobados == 0:
            print("❌ PROBLEMA CRÍTICO: No hay préstamos aprobados en la base de datos")
            print("   Acción: Verificar que los datos se hayan migrado correctamente")
        elif prestamos_validos == 0:
            print("❌ PROBLEMA CRÍTICO: No hay préstamos con total_financiamiento > 0")
            print("   Acción: Verificar que el campo total_financiamiento esté correctamente poblado")
        elif prestamos_en_rango == 0 and prestamos_sin_filtro_fecha > 0:
            print("⚠️  PROBLEMA: No hay préstamos válidos en el rango del año actual")
            print(f"   • Total aprobados: {total_aprobados:,}")
            print(f"   • Con monto > 0: {prestamos_validos:,}")
            print(f"   • En rango del año: {prestamos_en_rango:,}")
            print(f"   • Válidos sin filtro de fecha: {prestamos_sin_filtro_fecha:,}")
            print()
            print("   Posibles causas:")
            if sin_ninguna_fecha > 0:
                print(f"   • {sin_ninguna_fecha:,} préstamos no tienen ninguna fecha (se excluyen del filtro)")
            if min_fecha_registro and min_fecha_registro.year > año_actual:
                print(f"   • Las fechas de los préstamos son del futuro")
            if max_fecha_registro and max_fecha_registro.year < año_actual:
                print(f"   • Las fechas de los préstamos son de años anteriores")
            print()
            print("   Soluciones sugeridas:")
            print("   1. El endpoint debería usar datos sin filtros de fecha como fallback (ya implementado)")
            print("   2. Verificar que las fechas de los préstamos estén correctamente pobladas")
            print("   3. Considerar cambiar el período en el dashboard a 'mes' o 'semana'")
        else:
            print(f"✅ Todo parece estar bien. Hay {prestamos_validos:,} préstamos válidos")
            if prestamos_en_rango > 0:
                print(f"✅ Hay {prestamos_en_rango:,} préstamos en el rango del año actual")
            else:
                print(f"⚠️  No hay préstamos en el rango del año actual, pero hay {prestamos_sin_filtro_fecha:,} sin filtros")
        
        print()

    except Exception as e:
        print(f"❌ Error en auditoría: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    auditoria_completa()

