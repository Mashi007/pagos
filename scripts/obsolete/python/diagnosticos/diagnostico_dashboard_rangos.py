"""
Script de diagnóstico para el problema de "Distribución de Financiamiento por Rangos"
Verifica y ajusta la configuración del dashboard
"""

import sys
import os
from pathlib import Path

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_
from datetime import date, datetime
from decimal import Decimal

from app.database import SessionLocal
from app.models.prestamo import Prestamo


def diagnosticar_prestamos(db: Session):
    """Diagnostica el estado de los préstamos en la base de datos"""
    print("=" * 80)
    print("🔍 DIAGNÓSTICO: Distribución de Financiamiento por Rangos")
    print("=" * 80)
    print()

    # 1. Total de préstamos aprobados
    total_aprobados = db.query(Prestamo).filter(Prestamo.estado == "APROBADO").count()
    print(f"📊 Total de préstamos APROBADOS: {total_aprobados:,}")
    print()

    # 2. Préstamos con total_financiamiento válido
    prestamos_validos = db.query(Prestamo).filter(
        and_(
            Prestamo.estado == "APROBADO",
            Prestamo.total_financiamiento.isnot(None),
            Prestamo.total_financiamiento > 0
        )
    ).count()
    print(f"✅ Préstamos con total_financiamiento > 0: {prestamos_validos:,}")
    print()

    # 3. Análisis de fechas
    print("📅 ANÁLISIS DE FECHAS:")
    print("-" * 80)

    # Préstamos con fecha_registro
    con_fecha_registro = db.query(Prestamo).filter(
        and_(
            Prestamo.estado == "APROBADO",
            Prestamo.fecha_registro.isnot(None)
        )
    ).count()
    print(f"  • Con fecha_registro: {con_fecha_registro:,} ({con_fecha_registro/total_aprobados*100:.1f}%)")

    # Préstamos con fecha_aprobacion
    con_fecha_aprobacion = db.query(Prestamo).filter(
        and_(
            Prestamo.estado == "APROBADO",
            Prestamo.fecha_aprobacion.isnot(None)
        )
    ).count()
    print(f"  • Con fecha_aprobacion: {con_fecha_aprobacion:,} ({con_fecha_aprobacion/total_aprobados*100:.1f}%)")

    # Préstamos con fecha_base_calculo
    con_fecha_base = db.query(Prestamo).filter(
        and_(
            Prestamo.estado == "APROBADO",
            Prestamo.fecha_base_calculo.isnot(None)
        )
    ).count()
    print(f"  • Con fecha_base_calculo: {con_fecha_base:,} ({con_fecha_base/total_aprobados*100:.1f}%)")

    # Préstamos con al menos una fecha
    con_al_menos_una_fecha = db.query(Prestamo).filter(
        and_(
            Prestamo.estado == "APROBADO",
            or_(
                Prestamo.fecha_registro.isnot(None),
                Prestamo.fecha_aprobacion.isnot(None),
                Prestamo.fecha_base_calculo.isnot(None)
            )
        )
    ).count()
    print(f"  • Con al menos una fecha: {con_al_menos_una_fecha:,} ({con_al_menos_una_fecha/total_aprobados*100:.1f}%)")

    # Préstamos sin ninguna fecha
    sin_fechas = total_aprobados - con_al_menos_una_fecha
    print(f"  ⚠️  Sin ninguna fecha: {sin_fechas:,} ({sin_fechas/total_aprobados*100:.1f}%)")
    print()

    # 4. Análisis por período (año actual)
    hoy = date.today()
    fecha_inicio_ano = date(hoy.year, 1, 1)
    fecha_fin_ano = date(hoy.year, 12, 31)

    print(f"📆 ANÁLISIS POR PERÍODO (Año {hoy.year}):")
    print("-" * 80)
    print(f"  Rango: {fecha_inicio_ano} a {fecha_fin_ano}")
    print()

    # Préstamos con al menos una fecha en el rango del año
    prestamos_en_rango = db.query(Prestamo).filter(
        and_(
            Prestamo.estado == "APROBADO",
            or_(
                and_(
                    Prestamo.fecha_registro.isnot(None),
                    Prestamo.fecha_registro >= fecha_inicio_ano,
                    Prestamo.fecha_registro <= fecha_fin_ano
                ),
                and_(
                    Prestamo.fecha_aprobacion.isnot(None),
                    Prestamo.fecha_aprobacion >= fecha_inicio_ano,
                    Prestamo.fecha_aprobacion <= fecha_fin_ano
                ),
                and_(
                    Prestamo.fecha_base_calculo.isnot(None),
                    Prestamo.fecha_base_calculo >= fecha_inicio_ano,
                    Prestamo.fecha_base_calculo <= fecha_fin_ano
                )
            )
        )
    ).count()
    print(f"  • Préstamos con fecha en rango del año: {prestamos_en_rango:,}")

    # Préstamos válidos (con monto > 0) y en rango
    prestamos_validos_en_rango = db.query(Prestamo).filter(
        and_(
            Prestamo.estado == "APROBADO",
            Prestamo.total_financiamiento.isnot(None),
            Prestamo.total_financiamiento > 0,
            or_(
                and_(
                    Prestamo.fecha_registro.isnot(None),
                    Prestamo.fecha_registro >= fecha_inicio_ano,
                    Prestamo.fecha_registro <= fecha_fin_ano
                ),
                and_(
                    Prestamo.fecha_aprobacion.isnot(None),
                    Prestamo.fecha_aprobacion >= fecha_inicio_ano,
                    Prestamo.fecha_aprobacion <= fecha_fin_ano
                ),
                and_(
                    Prestamo.fecha_base_calculo.isnot(None),
                    Prestamo.fecha_base_calculo >= fecha_inicio_ano,
                    Prestamo.fecha_base_calculo <= fecha_fin_ano
                )
            )
        )
    ).count()
    print(f"  • Préstamos válidos (monto > 0) y en rango: {prestamos_validos_en_rango:,}")
    print()

    # 5. Distribución de montos
    print("💰 DISTRIBUCIÓN DE MONTOS:")
    print("-" * 80)

    # Montos por rango
    rangos_monto = [
        (0, 300, "$0 - $300"),
        (300, 600, "$300 - $600"),
        (600, 1000, "$600 - $1,000"),
        (1000, 5000, "$1,000 - $5,000"),
        (5000, 10000, "$5,000 - $10,000"),
        (10000, 20000, "$10,000 - $20,000"),
        (20000, 50000, "$20,000 - $50,000"),
        (50000, None, "$50,000+"),
    ]

    for min_val, max_val, etiqueta in rangos_monto:
        if max_val is None:
            count = db.query(Prestamo).filter(
                and_(
                    Prestamo.estado == "APROBADO",
                    Prestamo.total_financiamiento.isnot(None),
                    Prestamo.total_financiamiento > min_val
                )
            ).count()
        else:
            count = db.query(Prestamo).filter(
                and_(
                    Prestamo.estado == "APROBADO",
                    Prestamo.total_financiamiento.isnot(None),
                    Prestamo.total_financiamiento > min_val,
                    Prestamo.total_financiamiento <= max_val
                )
            ).count()
        print(f"  {etiqueta:20s}: {count:6,} préstamos")
    print()

    # 6. Resumen y recomendaciones
    print("=" * 80)
    print("📋 RESUMEN Y RECOMENDACIONES:")
    print("=" * 80)
    print()

    if total_aprobados == 0:
        print("❌ PROBLEMA CRÍTICO: No hay préstamos aprobados en la base de datos")
        print("   Acción: Verificar que los datos se hayan migrado correctamente")
    elif prestamos_validos == 0:
        print("❌ PROBLEMA CRÍTICO: No hay préstamos con total_financiamiento > 0")
        print("   Acción: Verificar que el campo total_financiamiento esté correctamente poblado")
    elif prestamos_validos_en_rango == 0:
        print("⚠️  PROBLEMA: No hay préstamos válidos en el rango del año actual")
        print(f"   • Total aprobados: {total_aprobados:,}")
        print(f"   • Con monto > 0: {prestamos_validos:,}")
        print(f"   • En rango del año: {prestamos_en_rango:,}")
        print(f"   • Válidos y en rango: {prestamos_validos_en_rango:,}")
        print()
        print("   Posibles causas:")
        if sin_fechas > 0:
            print(f"   • {sin_fechas:,} préstamos no tienen ninguna fecha (se excluyen del filtro)")
        if prestamos_en_rango == 0:
            print(f"   • Ningún préstamo tiene fecha en el rango del año {hoy.year}")
            print("   • Los préstamos pueden ser de años anteriores")
        print()
        print("   Soluciones sugeridas:")
        print("   1. Cambiar el período en el dashboard a 'mes' o 'semana'")
        print("   2. Verificar que las fechas de los préstamos estén correctamente pobladas")
        print("   3. Considerar incluir préstamos sin fecha si es apropiado para el negocio")
    else:
        print(f"✅ Todo parece estar bien. Hay {prestamos_validos_en_rango:,} préstamos válidos en el rango.")
        print()
        print("   Si el dashboard aún muestra 'No hay datos disponibles', verificar:")
        print("   1. Que el endpoint /api/v1/dashboard/financiamiento-por-rangos esté funcionando")
        print("   2. Que los filtros en el frontend estén correctamente configurados")
        print("   3. Los logs del backend para ver si hay errores")

    print()
    print("=" * 80)


def verificar_fechas_problema(db: Session):
    """Verifica préstamos que pueden tener problemas con fechas"""
    print()
    print("=" * 80)
    print("🔍 VERIFICACIÓN DE PRÉSTAMOS CON PROBLEMAS DE FECHAS")
    print("=" * 80)
    print()

    # Préstamos aprobados sin ninguna fecha
    prestamos_sin_fecha = db.query(Prestamo).filter(
        and_(
            Prestamo.estado == "APROBADO",
            Prestamo.fecha_registro.is_(None),
            Prestamo.fecha_aprobacion.is_(None),
            Prestamo.fecha_base_calculo.is_(None)
        )
    ).limit(10).all()

    if prestamos_sin_fecha:
        print("⚠️  Encontrados préstamos sin ninguna fecha (mostrando primeros 10):")
        for p in prestamos_sin_fecha:
            print(f"  • ID: {p.id}, Cliente: {p.cedula}, Monto: ${p.total_financiamiento or 0:,.2f}")
        print()

    # Préstamos con monto válido pero fuera del rango del año
    hoy = date.today()
    fecha_inicio_ano = date(hoy.year, 1, 1)
    fecha_fin_ano = date(hoy.year, 12, 31)

    prestamos_fuera_rango = db.query(Prestamo).filter(
        and_(
            Prestamo.estado == "APROBADO",
            Prestamo.total_financiamiento.isnot(None),
            Prestamo.total_financiamiento > 0,
            or_(
                and_(
                    Prestamo.fecha_registro.isnot(None),
                    or_(
                        Prestamo.fecha_registro < fecha_inicio_ano,
                        Prestamo.fecha_registro > fecha_fin_ano
                    )
                ),
                and_(
                    Prestamo.fecha_aprobacion.isnot(None),
                    or_(
                        Prestamo.fecha_aprobacion < fecha_inicio_ano,
                        Prestamo.fecha_aprobacion > fecha_fin_ano
                    )
                ),
                and_(
                    Prestamo.fecha_base_calculo.isnot(None),
                    or_(
                        Prestamo.fecha_base_calculo < fecha_inicio_ano,
                        Prestamo.fecha_base_calculo > fecha_fin_ano
                    )
                )
            )
        )
    ).limit(10).all()

    if prestamos_fuera_rango:
        print(f"📅 Préstamos válidos pero fuera del rango del año {hoy.year} (mostrando primeros 10):")
        for p in prestamos_fuera_rango:
            fechas = []
            if p.fecha_registro:
                fechas.append(f"registro: {p.fecha_registro}")
            if p.fecha_aprobacion:
                fechas.append(f"aprobación: {p.fecha_aprobacion}")
            if p.fecha_base_calculo:
                fechas.append(f"base_calculo: {p.fecha_base_calculo}")
            fechas_str = ", ".join(fechas) if fechas else "sin fechas"
            print(f"  • ID: {p.id}, Monto: ${p.total_financiamiento or 0:,.2f}, Fechas: {fechas_str}")
        print()


def main():
    """Función principal"""
    db: Session = SessionLocal()
    try:
        diagnosticar_prestamos(db)
        verificar_fechas_problema(db)
    except Exception as e:
        print(f"❌ Error durante el diagnóstico: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
