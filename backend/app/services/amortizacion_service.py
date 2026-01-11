"""
Servicio de Amortización
Lógica de negocio para generación y gestión de tablas de amortización
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import List, Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.amortizacion import Cuota
from app.schemas.amortizacion import (
    CuotaResponse,
    TablaAmortizacionRequest,
    TablaAmortizacionResponse,
)
from app.utils.date_helpers import calculate_payment_dates


class AmortizacionService:
    """Servicio para gestión de amortización"""

    @staticmethod
    def generar_tabla_amortizacion(
        request: TablaAmortizacionRequest,
    ) -> TablaAmortizacionResponse:
        """
        Genera una tabla de amortización completa

        Args:
            request: Parámetros para generar la tabla

        Returns:
            TablaAmortizacionResponse: Tabla de amortización completa
        """
        if request.tipo_amortizacion == "FRANCESA":
            return AmortizacionService._generar_frances(request)
        elif request.tipo_amortizacion == "ALEMANA":
            return AmortizacionService._generar_aleman(request)
        elif request.tipo_amortizacion == "AMERICANA":
            return AmortizacionService._generar_americano(request)
        else:
            raise ValueError(f"Sistema de amortización no soportado: {request.tipo_amortizacion}")

    @staticmethod
    def _generar_frances(
        request: TablaAmortizacionRequest,
    ) -> TablaAmortizacionResponse:
        """
        Sistema Francés: Cuota fija
        Fórmula: C = P * [i(1+i)^n] / [(1+i)^n - 1]
        """
        monto = request.monto_financiado
        tasa_anual = request.tasa_interes / Decimal("100")
        n_cuotas = request.numero_cuotas

        # Calcular tasa por período (asumiendo mensual por defecto)
        tasa_periodo = tasa_anual / Decimal("12")

        # Calcular cuota fija (si tasa > 0)
        if tasa_periodo > 0:
            factor = (tasa_periodo * (1 + tasa_periodo) ** n_cuotas) / ((1 + tasa_periodo) ** n_cuotas - 1)
            cuota_fija = monto * factor
        else:
            # Sin interés, solo dividir el monto
            cuota_fija = monto / Decimal(n_cuotas)

        cuota_fija = cuota_fija.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Generar fechas de vencimiento
        fechas = calculate_payment_dates(request.fecha_inicio, n_cuotas, "MENSUAL")

        # Generar cuotas
        cuotas = []
        saldo = monto
        total_capital = Decimal("0.00")
        total_interes = Decimal("0.00")

        for i in range(n_cuotas):
            # Calcular interés del período
            interes = (saldo * tasa_periodo).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            # Calcular capital (cuota - interés)
            capital = cuota_fija - interes

            # Ajuste en la última cuota
            if i == n_cuotas - 1:
                capital = saldo
                interes = cuota_fija - capital

            # Nuevo saldo
            nuevo_saldo = saldo - capital

            cuota = CuotaResponse(
                id=0,  # Temporal para respuesta
                prestamo_id=0,  # Temporal para respuesta
                numero_cuota=i + 1,
                fecha_vencimiento=fechas[i],
                monto_cuota=cuota_fija,
                monto_capital=capital,
                monto_interes=interes,
                saldo_capital_inicial=saldo,
                saldo_capital_final=nuevo_saldo,
                capital_pagado=Decimal("0.00"),
                interes_pagado=Decimal("0.00"),
                mora_pagada=Decimal("0.00"),
                total_pagado=Decimal("0.00"),
                capital_pendiente=capital,
                interes_pendiente=interes,
                dias_mora=0,
                monto_mora=Decimal("0.00"),
                tasa_mora=Decimal("0.00"),
                estado="PENDIENTE",
                observaciones=None,
                esta_vencida=False,
                monto_pendiente_total=cuota_fija,
                porcentaje_pagado=Decimal("0.00"),
            )
            cuotas.append(cuota)

            # Actualizar para siguiente iteración
            saldo = nuevo_saldo
            total_capital += capital
            total_interes += interes

        # Preparar resumen
        resumen = {
            "monto_financiado": monto,
            "tasa_interes": request.tasa_interes,
            "numero_cuotas": n_cuotas,
            "sistema": "FRANCESA",
            "total_capital": total_capital,
            "total_interes": total_interes,
            "total_cuota": total_capital + total_interes,
        }

        return TablaAmortizacionResponse(
            cuotas=cuotas,
            resumen=resumen,
        )

    @staticmethod
    def _generar_aleman(
        request: TablaAmortizacionRequest,
    ) -> TablaAmortizacionResponse:
        """
        Sistema Alemán: Capital fijo
        Fórmula: Interés = Saldo * Tasa
        """
        monto = request.monto_financiado
        tasa_anual = request.tasa_interes / Decimal("100")
        n_cuotas = request.numero_cuotas

        # Calcular tasa por período (asumiendo mensual)
        tasa_periodo = tasa_anual / Decimal("12")

        # Capital fijo por cuota
        capital_fijo = (monto / Decimal(n_cuotas)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Generar fechas
        fechas = calculate_payment_dates(request.fecha_inicio, n_cuotas, "MENSUAL")

        # Generar cuotas
        cuotas = []
        saldo = monto
        total_capital = Decimal("0.00")
        total_interes = Decimal("0.00")

        for i in range(n_cuotas):
            # Interés sobre saldo
            interes = (saldo * tasa_periodo).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            # Capital fijo (ajuste en última cuota)
            if i == n_cuotas - 1:
                capital = saldo
            else:
                capital = capital_fijo

            # Cuota total
            cuota_total = capital + interes

            # Nuevo saldo
            nuevo_saldo = saldo - capital

            cuota = CuotaResponse(
                id=0,
                prestamo_id=0,
                numero_cuota=i + 1,
                fecha_vencimiento=fechas[i],
                monto_cuota=cuota_total,
                monto_capital=capital,
                monto_interes=interes,
                saldo_capital_inicial=saldo,
                saldo_capital_final=nuevo_saldo,
                capital_pagado=Decimal("0.00"),
                interes_pagado=Decimal("0.00"),
                mora_pagada=Decimal("0.00"),
                total_pagado=Decimal("0.00"),
                capital_pendiente=capital,
                interes_pendiente=interes,
                dias_mora=0,
                monto_mora=Decimal("0.00"),
                tasa_mora=Decimal("0.00"),
                estado="PENDIENTE",
                observaciones=None,
                esta_vencida=False,
                monto_pendiente_total=cuota_total,
                porcentaje_pagado=Decimal("0.00"),
            )
            cuotas.append(cuota)

            saldo = nuevo_saldo
            total_capital += capital
            total_interes += interes

        resumen = {
            "monto_financiado": monto,
            "tasa_interes": request.tasa_interes,
            "numero_cuotas": n_cuotas,
            "sistema": "ALEMANA",
        }

        return TablaAmortizacionResponse(
            cuotas=cuotas,
            resumen=resumen,
        )

    @staticmethod
    def _generar_americano(
        request: TablaAmortizacionRequest,
    ) -> TablaAmortizacionResponse:
        """
        Sistema Americano: Solo interés en cuotas, capital al final
        """
        monto = request.monto_financiado
        tasa_anual = request.tasa_interes / Decimal("100")
        n_cuotas = request.numero_cuotas

        # Tasa por período
        tasa_periodo = tasa_anual / Decimal("12")

        # Interés fijo por período
        interes_fijo = (monto * tasa_periodo).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Generar fechas
        fechas = calculate_payment_dates(request.fecha_inicio, n_cuotas, "MENSUAL")

        # Generar cuotas
        cuotas = []
        total_capital = Decimal("0.00")
        total_interes = Decimal("0.00")

        for i in range(n_cuotas):
            if i == n_cuotas - 1:
                # Última cuota: capital + interés
                capital = monto
                interes = interes_fijo
                cuota_total = capital + interes
                saldo_final = Decimal("0.00")
            else:
                # Cuotas intermedias: solo interés
                capital = Decimal("0.00")
                interes = interes_fijo
                cuota_total = interes
                saldo_final = monto

            cuota = CuotaResponse(
                id=0,
                prestamo_id=0,
                numero_cuota=i + 1,
                fecha_vencimiento=fechas[i],
                monto_cuota=cuota_total,
                monto_capital=capital,
                monto_interes=interes,
                saldo_capital_inicial=monto,
                saldo_capital_final=saldo_final,
                capital_pagado=Decimal("0.00"),
                interes_pagado=Decimal("0.00"),
                mora_pagada=Decimal("0.00"),
                total_pagado=Decimal("0.00"),
                capital_pendiente=capital,
                interes_pendiente=interes,
                dias_mora=0,
                monto_mora=Decimal("0.00"),
                tasa_mora=Decimal("0.00"),
                estado="PENDIENTE",
                observaciones=None,
                esta_vencida=False,
                monto_pendiente_total=cuota_total,
                porcentaje_pagado=Decimal("0.00"),
            )
            cuotas.append(cuota)

            total_capital += capital
            total_interes += interes

        resumen = {
            "monto_financiado": monto,
            "tasa_interes": request.tasa_interes,
            "numero_cuotas": n_cuotas,
            "sistema": "AMERICANA",
        }

        return TablaAmortizacionResponse(
            cuotas=cuotas,
            resumen=resumen,
        )

    @staticmethod
    def crear_cuotas_prestamo(db: Session, prestamo_id: int, tabla: TablaAmortizacionResponse) -> List[Cuota]:
        """
        Crea las cuotas en la BD para un préstamo

        Args:
            db: Sesión de base de datos
            prestamo_id: ID del préstamo
            tabla: Tabla de amortización generada

        Returns:
            List[Cuota]: Lista de cuotas creadas
        """
        cuotas_creadas = []

        for cuota_detalle in tabla.cuotas:
            cuota = Cuota(
                prestamo_id=prestamo_id,
                numero_cuota=cuota_detalle.numero_cuota,
                fecha_vencimiento=cuota_detalle.fecha_vencimiento,
                monto_cuota=cuota_detalle.monto_cuota,
                monto_capital=cuota_detalle.monto_capital,
                monto_interes=cuota_detalle.monto_interes,
                saldo_capital_inicial=cuota_detalle.saldo_capital_inicial,
                saldo_capital_final=cuota_detalle.saldo_capital_final,
                capital_pendiente=cuota_detalle.capital_pendiente,
                interes_pendiente=cuota_detalle.interes_pendiente,
                estado="PENDIENTE",
            )
            db.add(cuota)
            cuotas_creadas.append(cuota)

        db.commit()
        return cuotas_creadas

    @staticmethod
    def obtener_cuotas_prestamo(db: Session, prestamo_id: int, estado: Optional[str] = None) -> List[Cuota]:
        """
        Obtiene las cuotas de un préstamo.
        Ordena primero las cuotas NO PAGADAS (más antigua primero), luego las pagadas.
        """
        from sqlalchemy import case

        query = db.query(Cuota).filter(Cuota.prestamo_id == prestamo_id)

        if estado:
            query = query.filter(Cuota.estado == estado)

        return query.order_by(
            # Primero: NO PAGADAS (estado != 'PAGADO'), luego PAGADAS
            case((Cuota.estado != "PAGADO", 0), else_=1),
            # Dentro de NO PAGADAS: ordenar por fecha_vencimiento (más antigua primero)
            Cuota.fecha_vencimiento,
            # Como desempate: numero_cuota
            Cuota.numero_cuota,
        ).all()

    @staticmethod
    def recalcular_mora(
        db: Session,
        prestamo_id: int,
        tasa_mora_diaria: Decimal,
        fecha_calculo: Optional[date] = None,
    ) -> dict:
        """
        Recalcula la mora de todas las cuotas vencidas

        Args:
            db: Sesión de base de datos
            prestamo_id: ID del préstamo
            tasa_mora_diaria: Tasa de mora diaria (%)
            fecha_calculo: Fecha para el cálculo

        Returns:
            dict: Resumen del recálculo
        """
        if fecha_calculo is None:
            fecha_calculo = date.today()

        # Obtener cuotas vencidas
        cuotas = (
            db.query(Cuota)
            .filter(
                and_(
                    Cuota.prestamo_id == prestamo_id,
                    Cuota.estado.in_(["VENCIDA", "PARCIAL"]),
                    Cuota.fecha_vencimiento < fecha_calculo,
                )
            )
            .all()
        )

        total_mora_anterior = Decimal("0.00")
        total_mora_nueva = Decimal("0.00")
        cuotas_actualizadas = 0

        for cuota in cuotas:
            total_mora_anterior += cuota.monto_mora

            # ✅ REGLA: Mora siempre debe ser 0% - DESACTIVADO
            # Calcular nueva mora (SIEMPRE 0)
            # dias_mora = (fecha_calculo - cuota.fecha_vencimiento).days
            # nueva_mora = (cuota.monto_cuota * tasa_mora_diaria * Decimal(dias_mora) / Decimal("100")).quantize(
            #     Decimal("0.01"), rounding=ROUND_HALF_UP
            # )
            
            # Actualizar (SIEMPRE EN 0)
            cuota.monto_mora = Decimal("0.00")
            cuota.dias_mora = 0
            cuota.tasa_mora = Decimal("0.00")

            total_mora_nueva += nueva_mora
            cuotas_actualizadas += 1

        db.commit()

        return {
            "cuotas_actualizadas": cuotas_actualizadas,
            "mora_anterior": total_mora_anterior,
            "mora_nueva": total_mora_nueva,
            "diferencia": total_mora_nueva - total_mora_anterior,
        }
