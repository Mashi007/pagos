"""
Script para ajustar fechas de préstamos que pueden estar causando problemas
en el dashboard de "Distribución de Financiamiento por Rangos"
"""

import sys
import os
from pathlib import Path

# Agregar el directorio raíz del proyecto al path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from datetime import date

from app.database import SessionLocal
from app.models.prestamo import Prestamo


def ajustar_fechas_faltantes(db: Session, dry_run: bool = True):
    """
    Ajusta préstamos que no tienen ninguna fecha asignando fecha_aprobacion
    basándose en otras fechas disponibles o usando una fecha por defecto
    """
    print("=" * 80)
    print("🔧 AJUSTE DE FECHAS FALTANTES EN PRÉSTAMOS")
    print("=" * 80)
    print()

    if dry_run:
        print("⚠️  MODO DRY RUN - No se realizarán cambios en la base de datos")
        print()

    # Encontrar préstamos sin ninguna fecha
    prestamos_sin_fecha = db.query(Prestamo).filter(
        and_(
            Prestamo.estado == "APROBADO",
            Prestamo.fecha_registro.is_(None),
            Prestamo.fecha_aprobacion.is_(None),
            Prestamo.fecha_base_calculo.is_(None)
        )
    ).all()

    print(f"📊 Préstamos sin ninguna fecha: {len(prestamos_sin_fecha):,}")
    print()

    if not prestamos_sin_fecha:
        print("✅ No hay préstamos sin fecha que ajustar")
        return

    # Estrategia: usar fecha_aprobacion = fecha_registro si existe, o fecha actual si no
    # Pero primero intentar usar fecha_base_calculo si existe
    ajustados = 0
    fecha_por_defecto = date.today()

    for prestamo in prestamos_sin_fecha:
        fecha_a_asignar = None

        # Prioridad 1: fecha_base_calculo (si existe)
        if prestamo.fecha_base_calculo:
            fecha_a_asignar = prestamo.fecha_base_calculo
        # Prioridad 2: fecha_registro (si existe)
        elif prestamo.fecha_registro:
            fecha_a_asignar = prestamo.fecha_registro
        # Prioridad 3: fecha_aprobacion (si existe)
        elif prestamo.fecha_aprobacion:
            fecha_a_asignar = prestamo.fecha_aprobacion
        # Prioridad 4: fecha por defecto (hoy)
        else:
            fecha_a_asignar = fecha_por_defecto

        if not dry_run:
            # Asignar fecha_aprobacion si no tiene ninguna
            if not prestamo.fecha_aprobacion:
                prestamo.fecha_aprobacion = fecha_a_asignar
            # Asignar fecha_registro si no tiene ninguna
            if not prestamo.fecha_registro:
                prestamo.fecha_registro = fecha_a_asignar
            # Asignar fecha_base_calculo si no tiene ninguna
            if not prestamo.fecha_base_calculo:
                prestamo.fecha_base_calculo = fecha_a_asignar

            db.commit()
            ajustados += 1
        else:
            print(f"  [DRY RUN] Préstamo ID {prestamo.id}: asignaría fecha_aprobacion = {fecha_a_asignar}")
            ajustados += 1

    if not dry_run:
        print(f"✅ Ajustados {ajustados:,} préstamos")
    else:
        print(f"📝 Se ajustarían {ajustados:,} préstamos en modo real")
    print()


def normalizar_fechas_inconsistentes(db: Session, dry_run: bool = True):
    """
    Normaliza fechas inconsistentes (ej: fecha_aprobacion anterior a fecha_registro)
    """
    print("=" * 80)
    print("🔧 NORMALIZACIÓN DE FECHAS INCONSISTENTES")
    print("=" * 80)
    print()

    if dry_run:
        print("⚠️  MODO DRY RUN - No se realizarán cambios en la base de datos")
        print()

    # Encontrar préstamos con fechas inconsistentes
    prestamos = db.query(Prestamo).filter(
        Prestamo.estado == "APROBADO"
    ).all()

    inconsistentes = []
    for prestamo in prestamos:
        fechas = []
        if prestamo.fecha_registro:
            fechas.append(("registro", prestamo.fecha_registro))
        if prestamo.fecha_aprobacion:
            fechas.append(("aprobacion", prestamo.fecha_aprobacion))
        if prestamo.fecha_base_calculo:
            fechas.append(("base_calculo", prestamo.fecha_base_calculo))

        if len(fechas) >= 2:
            # Verificar si hay inconsistencias (fecha_aprobacion antes de fecha_registro)
            fechas_ordenadas = sorted(fechas, key=lambda x: x[1])
            if fechas_ordenadas[0][0] == "aprobacion" and fechas_ordenadas[-1][0] == "registro":
                inconsistentes.append(prestamo)

    print(f"📊 Préstamos con fechas inconsistentes: {len(inconsistentes):,}")
    print()

    if not inconsistentes:
        print("✅ No hay préstamos con fechas inconsistentes")
        return

    ajustados = 0
    for prestamo in inconsistentes[:10]:  # Limitar a 10 para no sobrecargar
        if not dry_run:
            # Usar la fecha más reciente como fecha_aprobacion
            fechas = []
            if prestamo.fecha_registro:
                fechas.append(prestamo.fecha_registro)
            if prestamo.fecha_aprobacion:
                fechas.append(prestamo.fecha_aprobacion)
            if prestamo.fecha_base_calculo:
                fechas.append(prestamo.fecha_base_calculo)

            if fechas:
                fecha_mas_reciente = max(fechas)
                prestamo.fecha_aprobacion = fecha_mas_reciente
                db.commit()
                ajustados += 1
        else:
            print(f"  [DRY RUN] Préstamo ID {prestamo.id}: normalizaría fechas")
            ajustados += 1

    if not dry_run:
        print(f"✅ Normalizados {ajustados:,} préstamos")
    else:
        print(f"📝 Se normalizarían {ajustados:,} préstamos en modo real")
    print()


def main():
    """Función principal"""
    import argparse

    parser = argparse.ArgumentParser(description="Ajustar fechas de préstamos para el dashboard")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Ejecutar cambios (por defecto es modo dry-run)"
    )
    parser.add_argument(
        "--solo-fechas-faltantes",
        action="store_true",
        help="Solo ajustar préstamos sin fecha"
    )
    parser.add_argument(
        "--solo-inconsistentes",
        action="store_true",
        help="Solo normalizar fechas inconsistentes"
    )

    args = parser.parse_args()

    dry_run = not args.execute

    db: Session = SessionLocal()
    try:
        if not args.solo_inconsistentes:
            ajustar_fechas_faltantes(db, dry_run=dry_run)

        if not args.solo_fechas_faltantes:
            normalizar_fechas_inconsistentes(db, dry_run=dry_run)

        if dry_run:
            print()
            print("=" * 80)
            print("💡 Para ejecutar los cambios, usa: python ajustar_fechas_prestamos.py --execute")
            print("=" * 80)
    except Exception as e:
        print(f"❌ Error durante el ajuste: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    main()
