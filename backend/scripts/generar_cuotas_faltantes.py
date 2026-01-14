"""
Script para generar cuotas faltantes en préstamos APROBADOS

Problemas identificados:
1. Préstamo crítico (ID 3708): Sin cuotas (0 de 12 esperadas)
2. ~200+ préstamos: Con cuotas incompletas (tienen menos de las esperadas)

Este script:
- Genera cuotas para préstamos sin cuotas (crítico)
- Completa cuotas faltantes para préstamos con cuotas incompletas
"""

import logging
import sys
from datetime import date
from decimal import Decimal
from typing import List, Tuple

from sqlalchemy.orm import Session
from dateutil.relativedelta import relativedelta  # type: ignore[import-untyped]

# Agregar el directorio raíz del proyecto al path
sys.path.insert(0, str(__file__).replace("scripts/generar_cuotas_faltantes.py", ""))

from app.db.session import SessionLocal
from app.models.amortizacion import Cuota
from app.models.prestamo import Prestamo

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def _calcular_intervalo_dias(modalidad_pago: str) -> int:
    """Calcula días entre cuotas según modalidad"""
    intervalos = {
        "MENSUAL": 30,
        "QUINCENAL": 15,
        "SEMANAL": 7,
    }
    return intervalos.get(modalidad_pago, 30)


def generar_cuota_faltante(
    prestamo: Prestamo,
    numero_cuota: int,
    fecha_base: date,
    saldo_capital: Decimal,
    db: Session,
) -> Cuota:
    """
    Genera una cuota específica para un préstamo

    Args:
        prestamo: Préstamo
        numero_cuota: Número de cuota a generar
        fecha_base: Fecha base de cálculo
        saldo_capital: Saldo de capital pendiente
        db: Sesión de base de datos

    Returns:
        Cuota generada
    """
    from datetime import timedelta

    # Calcular fecha de vencimiento
    if prestamo.modalidad_pago == "MENSUAL":
        fecha_vencimiento = fecha_base + relativedelta(months=numero_cuota)
    else:
        intervalo_dias = _calcular_intervalo_dias(prestamo.modalidad_pago)
        fecha_vencimiento = fecha_base + timedelta(days=intervalo_dias * numero_cuota)

    # Método Francés (cuota fija)
    monto_cuota = prestamo.cuota_periodo

    # Calcular interés
    if prestamo.tasa_interes == Decimal("0.00"):
        tasa_mensual = Decimal("0.00")
    else:
        tasa_mensual = Decimal(prestamo.tasa_interes) / Decimal(100) / Decimal(12)

    if tasa_mensual == Decimal("0.00"):
        monto_interes = Decimal("0.00")
        monto_capital = monto_cuota
    else:
        monto_interes = saldo_capital * tasa_mensual
        monto_capital = monto_cuota - monto_interes

    # Actualizar saldo
    saldo_capital_inicial = saldo_capital
    saldo_capital_final = saldo_capital - monto_capital

    # Crear cuota
    # ✅ ACTUALIZADO: Solo usa monto_cuota y total_pagado (sin desglose capital/interés)
    cuota = Cuota(
        prestamo_id=prestamo.id,
        numero_cuota=numero_cuota,
        fecha_vencimiento=fecha_vencimiento,
        monto_cuota=monto_cuota,
        saldo_capital_inicial=saldo_capital_inicial,
        saldo_capital_final=saldo_capital_final,
        total_pagado=Decimal("0.00"),
        dias_mora=0,
        estado="PENDIENTE",
    )

    return cuota


def calcular_saldo_capital_actual(prestamo: Prestamo, db: Session) -> Decimal:
    """
    Calcula el saldo de capital actual basado en las cuotas existentes
    """
    cuotas_existentes = (
        db.query(Cuota)
        .filter(Cuota.prestamo_id == prestamo.id)
        .order_by(Cuota.numero_cuota)
        .all()
    )

    if not cuotas_existentes:
        return prestamo.total_financiamiento

    # Usar el saldo_capital_final de la última cuota
    ultima_cuota = cuotas_existentes[-1]
    return ultima_cuota.saldo_capital_final


def generar_cuotas_faltantes_prestamo(
    prestamo: Prestamo,
    db: Session,
    dry_run: bool = False,
) -> Tuple[bool, int, str]:
    """
    Genera cuotas faltantes para un préstamo

    Args:
        prestamo: Préstamo a procesar
        db: Sesión de base de datos
        dry_run: Si es True, solo simula sin hacer cambios

    Returns:
        (exito, cuotas_generadas, mensaje)
    """
    try:
        # Validar préstamo
        if prestamo.estado != "APROBADO":
            return False, 0, f"Préstamo {prestamo.id} no está APROBADO (estado: {prestamo.estado})"

        if not prestamo.fecha_base_calculo:
            return False, 0, f"Préstamo {prestamo.id} no tiene fecha_base_calculo"

        if prestamo.numero_cuotas <= 0:
            return False, 0, f"Préstamo {prestamo.id} tiene número de cuotas inválido: {prestamo.numero_cuotas}"

        # Obtener cuotas existentes
        cuotas_existentes = (
            db.query(Cuota)
            .filter(Cuota.prestamo_id == prestamo.id)
            .order_by(Cuota.numero_cuota)
            .all()
        )

        numeros_cuotas_existentes = {c.numero_cuota for c in cuotas_existentes}
        numeros_cuotas_esperadas = set(range(1, prestamo.numero_cuotas + 1))
        numeros_cuotas_faltantes = numeros_cuotas_esperadas - numeros_cuotas_existentes

        if not numeros_cuotas_faltantes:
            return True, 0, f"Préstamo {prestamo.id} ya tiene todas las cuotas ({prestamo.numero_cuotas})"

        # Calcular saldo de capital actual
        if cuotas_existentes:
            # Recalcular saldo basado en cuotas existentes
            saldo_actual = calcular_saldo_capital_actual(prestamo, db)
        else:
            # Sin cuotas existentes, usar total_financiamiento
            saldo_actual = prestamo.total_financiamiento

        # Generar cuotas faltantes
        fecha_base = prestamo.fecha_base_calculo
        cuotas_generadas = []

        for numero_cuota in sorted(numeros_cuotas_faltantes):
            # Calcular saldo para esta cuota
            # Necesitamos recalcular el saldo considerando todas las cuotas anteriores (existentes + generadas)
            # Por simplicidad, usamos el método de recálculo completo
            # Esto requiere regenerar todas las cuotas desde el inicio

            # Mejor enfoque: Si hay cuotas existentes, regenerar todas para mantener consistencia
            if cuotas_existentes:
                logger.warning(
                    f"Préstamo {prestamo.id} tiene cuotas existentes. "
                    f"Se recomienda regenerar todas las cuotas para mantener consistencia."
                )
                return False, 0, (
                    f"Préstamo {prestamo.id} tiene cuotas existentes. "
                    f"Use 'regenerar_todas_cuotas' en lugar de 'completar_cuotas_faltantes'"
                )

            # Generar cuota
            cuota = generar_cuota_faltante(
                prestamo,
                numero_cuota,
                fecha_base,
                saldo_actual,
                db,
            )

            # Actualizar saldo para la siguiente cuota
            saldo_actual = cuota.saldo_capital_final

            cuotas_generadas.append(cuota)

            if not dry_run:
                db.add(cuota)

        if not dry_run:
            db.commit()

        mensaje = (
            f"Préstamo {prestamo.id}: "
            f"{len(cuotas_generadas)} cuotas generadas "
            f"(faltantes: {sorted(numeros_cuotas_faltantes)})"
        )

        return True, len(cuotas_generadas), mensaje

    except Exception as e:
        if not dry_run:
            db.rollback()
        logger.error(f"Error procesando préstamo {prestamo.id}: {str(e)}", exc_info=True)
        return False, 0, f"Error: {str(e)}"


def regenerar_todas_cuotas_prestamo(
    prestamo: Prestamo,
    db: Session,
    dry_run: bool = False,
) -> Tuple[bool, int, str]:
    """
    Regenera TODAS las cuotas de un préstamo (elimina existentes y crea nuevas)

    Args:
        prestamo: Préstamo a procesar
        db: Sesión de base de datos
        dry_run: Si es True, solo simula sin hacer cambios

    Returns:
        (exito, cuotas_generadas, mensaje)
    """
    from app.services.prestamo_amortizacion_service import generar_tabla_amortizacion

    try:
        # Validar préstamo
        if prestamo.estado != "APROBADO":
            return False, 0, f"Préstamo {prestamo.id} no está APROBADO (estado: {prestamo.estado})"

        if not prestamo.fecha_base_calculo:
            return False, 0, f"Préstamo {prestamo.id} no tiene fecha_base_calculo"

        if prestamo.numero_cuotas <= 0:
            return False, 0, f"Préstamo {prestamo.id} tiene número de cuotas inválido: {prestamo.numero_cuotas}"

        # Contar cuotas existentes
        cuotas_existentes = (
            db.query(Cuota)
            .filter(Cuota.prestamo_id == prestamo.id)
            .count()
        )

        if dry_run:
            return True, prestamo.numero_cuotas, (
                f"DRY RUN: Préstamo {prestamo.id} regeneraría {prestamo.numero_cuotas} cuotas "
                f"(actualmente tiene {cuotas_existentes})"
            )

        # Regenerar todas las cuotas
        fecha_base = prestamo.fecha_base_calculo
        cuotas_generadas = generar_tabla_amortizacion(prestamo, fecha_base, db)

        mensaje = (
            f"Préstamo {prestamo.id}: "
            f"{len(cuotas_generadas)} cuotas regeneradas "
            f"(tenía {cuotas_existentes}, ahora tiene {len(cuotas_generadas)})"
        )

        return True, len(cuotas_generadas), mensaje

    except Exception as e:
        if not dry_run:
            db.rollback()
        logger.error(f"Error regenerando cuotas para préstamo {prestamo.id}: {str(e)}", exc_info=True)
        return False, 0, f"Error: {str(e)}"


def identificar_prestamos_problema(db: Session) -> Tuple[List[int], List[int]]:
    """
    Identifica préstamos con problemas de cuotas

    Returns:
        (prestamos_sin_cuotas, prestamos_cuotas_incompletas)
    """
    from sqlalchemy import func

    # Préstamos APROBADOS sin cuotas
    prestamos_sin_cuotas = (
        db.query(Prestamo.id)
        .outerjoin(Cuota, Cuota.prestamo_id == Prestamo.id)
        .filter(
            Prestamo.estado == "APROBADO",
            Prestamo.fecha_base_calculo.isnot(None),
        )
        .group_by(Prestamo.id)
        .having(func.count(Cuota.id) == 0)
        .all()
    )
    prestamos_sin_cuotas_ids = [row[0] for row in prestamos_sin_cuotas]

    # Préstamos APROBADOS con cuotas incompletas
    prestamos_cuotas_incompletas = (
        db.query(Prestamo.id)
        .join(Cuota, Cuota.prestamo_id == Prestamo.id)
        .filter(
            Prestamo.estado == "APROBADO",
            Prestamo.fecha_base_calculo.isnot(None),
        )
        .group_by(Prestamo.id, Prestamo.numero_cuotas)
        .having(func.count(Cuota.id) < Prestamo.numero_cuotas)
        .all()
    )
    prestamos_cuotas_incompletas_ids = [row[0] for row in prestamos_cuotas_incompletas]

    return prestamos_sin_cuotas_ids, prestamos_cuotas_incompletas_ids


def main():
    """Función principal"""
    import argparse

    parser = argparse.ArgumentParser(description="Generar cuotas faltantes en préstamos")
    parser.add_argument(
        "--prestamo-id",
        type=int,
        help="ID del préstamo específico a procesar (si no se especifica, procesa todos los problemáticos)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simular sin hacer cambios en la base de datos"
    )
    parser.add_argument(
        "--regenerar",
        action="store_true",
        help="Regenerar TODAS las cuotas (elimina existentes y crea nuevas)"
    )

    args = parser.parse_args()

    db = SessionLocal()

    try:
        if args.prestamo_id:
            # Procesar préstamo específico
            prestamo = db.query(Prestamo).filter(Prestamo.id == args.prestamo_id).first()

            if not prestamo:
                logger.error(f"Préstamo {args.prestamo_id} no encontrado")
                return

            logger.info(f"Procesando préstamo {args.prestamo_id}...")

            if args.regenerar:
                exito, cuotas, mensaje = regenerar_todas_cuotas_prestamo(prestamo, db, args.dry_run)
            else:
                exito, cuotas, mensaje = generar_cuotas_faltantes_prestamo(prestamo, db, args.dry_run)

            if exito:
                logger.info(f"✅ {mensaje}")
            else:
                logger.error(f"❌ {mensaje}")
        else:
            # Procesar todos los préstamos problemáticos
            logger.info("Identificando préstamos con problemas...")
            prestamos_sin_cuotas_ids, prestamos_cuotas_incompletas_ids = identificar_prestamos_problema(db)

            logger.info(f"Préstamos sin cuotas: {len(prestamos_sin_cuotas_ids)}")
            logger.info(f"Préstamos con cuotas incompletas: {len(prestamos_cuotas_incompletas_ids)}")

            total_procesados = 0
            total_exitosos = 0
            total_cuotas_generadas = 0

            # Procesar préstamos sin cuotas
            for prestamo_id in prestamos_sin_cuotas_ids:
                prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
                if not prestamo:
                    continue

                total_procesados += 1
                logger.info(f"Procesando préstamo {prestamo_id} (sin cuotas)...")

                if args.regenerar:
                    exito, cuotas, mensaje = regenerar_todas_cuotas_prestamo(prestamo, db, args.dry_run)
                else:
                    exito, cuotas, mensaje = generar_cuotas_faltantes_prestamo(prestamo, db, args.dry_run)

                if exito:
                    total_exitosos += 1
                    total_cuotas_generadas += cuotas
                    logger.info(f"✅ {mensaje}")
                else:
                    logger.error(f"❌ {mensaje}")

            # Procesar préstamos con cuotas incompletas
            for prestamo_id in prestamos_cuotas_incompletas_ids:
                prestamo = db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
                if not prestamo:
                    continue

                total_procesados += 1
                logger.info(f"Procesando préstamo {prestamo_id} (cuotas incompletas)...")

                # Para cuotas incompletas, siempre regenerar todas
                exito, cuotas, mensaje = regenerar_todas_cuotas_prestamo(prestamo, db, args.dry_run)

                if exito:
                    total_exitosos += 1
                    total_cuotas_generadas += cuotas
                    logger.info(f"✅ {mensaje}")
                else:
                    logger.error(f"❌ {mensaje}")

            logger.info("=" * 70)
            logger.info("RESUMEN:")
            logger.info(f"  Total procesados: {total_procesados}")
            logger.info(f"  Exitosos: {total_exitosos}")
            logger.info(f"  Fallidos: {total_procesados - total_exitosos}")
            logger.info(f"  Total cuotas generadas: {total_cuotas_generadas}")
            logger.info("=" * 70)

    finally:
        db.close()


if __name__ == "__main__":
    main()
