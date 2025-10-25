# backend/app/services/amortizacion_service.py
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
    CuotaDetalle,
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
        Genera tabla de amortización según sistema especificado

        Args:
            request: Parámetros para generación

        Returns:
            TablaAmortizacionResponse: Tabla de amortización completa
        """
        if request.sistema_amortizacion == "FRANCES":
            return AmortizacionService._generar_frances(request)
        elif request.sistema_amortizacion == "ALEMAN":
            return AmortizacionService._generar_aleman(request)
        elif request.sistema_amortizacion == "AMERICANO":
            return AmortizacionService._generar_americano(request)
        else:
            raise ValueError(
                f"Sistema de amortización no soportado: {request.sistema_amortizacion}"
            )

    @staticmethod
    def _generar_frances(
        request: TablaAmortizacionRequest,
    ) -> TablaAmortizacionResponse:
        """
        Sistema Francés: Cuota fija
        Fórmula: C = P * [i(1+i)^n] / [(1+i)^n - 1]
        """
        monto = request.monto_financiado
        tasa_anual = request.tasa_interes_anual / Decimal("100")
        n_cuotas = request.numero_cuotas

        # Calcular tasa por período según modalidad
        if request.modalidad == "SEMANAL":
            tasa_periodo = tasa_anual / Decimal("52")
        elif request.modalidad == "QUINCENAL":
            tasa_periodo = tasa_anual / Decimal("24")
        elif request.modalidad == "MENSUAL":
            tasa_periodo = tasa_anual / Decimal("12")
        elif request.modalidad == "BIMENSUAL":
            tasa_periodo = tasa_anual / Decimal("6")
        elif request.modalidad == "TRIMESTRAL":
            tasa_periodo = tasa_anual / Decimal("4")
        else:
            tasa_periodo = tasa_anual / Decimal("12")

        # Calcular cuota fija (si tasa > 0)
        if tasa_periodo > 0:
            factor = (tasa_periodo * (1 + tasa_periodo) ** n_cuotas) / (
                (1 + tasa_periodo) ** n_cuotas - 1
            )
            cuota_fija = monto * factor
        else:
            # Sin interés, solo dividir el monto
            cuota_fija = monto / Decimal(n_cuotas)

        cuota_fija = cuota_fija.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

        # Generar fechas de vencimiento
        fechas = calculate_payment_dates(
            request.fecha_primer_vencimiento, n_cuotas, request.modalidad
        )

        # Generar cuotas
        cuotas = []
        saldo = monto
        total_capital = Decimal("0.00")
        total_interes = Decimal("0.00")

        for i in range(n_cuotas):
            # Calcular interés del período
            interes = (saldo * tasa_periodo).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

            # Calcular capital (cuota - interés)
            capital = cuota_fija - interes

            # Ajuste en última cuota por redondeos
            if i == n_cuotas - 1:
                capital = saldo
                cuota_fija = capital + interes

            # Nuevo saldo
            nuevo_saldo = saldo - capital

            cuota = CuotaDetalle(
                numero_cuota=i + 1,
                fecha_vencimiento=fechas[i],
                saldo_inicial=saldo,
                capital=capital,
                interes=interes,
                cuota=cuota_fija,
                saldo_final=nuevo_saldo,
            )

            cuotas.append(cuota)

            # Actualizar para siguiente iteración
            saldo = nuevo_saldo
            total_capital += capital
            total_interes += interes

        # Preparar resumen
        resumen = {
            "total_capital": total_capital,
            "total_interes": total_interes,
            "total_pagar": total_capital + total_interes,
            "cuota_promedio": cuota_fija,
            "tasa_efectiva": tasa_periodo * Decimal("100"),
        }

        # Preparar parámetros
        parametros = {
            "monto_financiado": monto,
            "tasa_interes_anual": request.tasa_interes_anual,
            "numero_cuotas": n_cuotas,
            "modalidad": request.modalidad,
            "sistema": "FRANCES",
        }

        return TablaAmortizacionResponse(
            cuotas=cuotas, resumen=resumen, parametros=parametros
        )

    @staticmethod
    def _generar_aleman(request: TablaAmortizacionRequest) -> TablaAmortizacionResponse:
        """
        Sistema Alemán: Capital fijo, cuota decreciente
        Capital por cuota = Monto / N
        Interés = Saldo * Tasa
        """
        monto = request.monto_financiado
        tasa_anual = request.tasa_interes_anual / Decimal("100")
        n_cuotas = request.numero_cuotas

        # Calcular tasa por período
        if request.modalidad == "MENSUAL":
            tasa_periodo = tasa_anual / Decimal("12")
        else:
            tasa_periodo = tasa_anual / Decimal("12")

        # Capital fijo por cuota
        capital_fijo = (monto / Decimal(n_cuotas)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        # Generar fechas
        fechas = calculate_payment_dates(
            request.fecha_primer_vencimiento, n_cuotas, request.modalidad
        )

        # Generar cuotas
        cuotas = []
        saldo = monto
        total_capital = Decimal("0.00")
        total_interes = Decimal("0.00")

        for i in range(n_cuotas):
            # Interés sobre saldo
            interes = (saldo * tasa_periodo).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )

            # Capital fijo (ajuste en última cuota)
            if i == n_cuotas - 1:
                capital = saldo
            else:
                capital = capital_fijo

            # Cuota total
            cuota_total = capital + interes

            # Nuevo saldo
            nuevo_saldo = saldo - capital

            cuota = CuotaDetalle(
                numero_cuota=i + 1,
                fecha_vencimiento=fechas[i],
                saldo_inicial=saldo,
                capital=capital,
                interes=interes,
                cuota=cuota_total,
                saldo_final=nuevo_saldo,
            )

            cuotas.append(cuota)

            saldo = nuevo_saldo
            total_capital += capital
            total_interes += interes

        resumen = {
            "total_capital": total_capital,
            "total_interes": total_interes,
            "total_pagar": total_capital + total_interes,
            "capital_por_cuota": capital_fijo,
            "primera_cuota": cuotas[0].cuota,
            "ultima_cuota": cuotas[-1].cuota,
        }

        parametros = {
            "monto_financiado": monto,
            "tasa_interes_anual": request.tasa_interes_anual,
            "numero_cuotas": n_cuotas,
            "modalidad": request.modalidad,
            "sistema": "ALEMAN",
        }

        return TablaAmortizacionResponse(
            cuotas=cuotas, resumen=resumen, parametros=parametros
        )

    @staticmethod
    def _generar_americano(
        request: TablaAmortizacionRequest,
    ) -> TablaAmortizacionResponse:
        """
        Sistema Americano: Solo interés en cuotas, capital al final
        """
        monto = request.monto_financiado
        tasa_anual = request.tasa_interes_anual / Decimal("100")
        n_cuotas = request.numero_cuotas

        # Tasa por período
        tasa_periodo = tasa_anual / Decimal("12")

        # Interés fijo por período
        interes_fijo = (monto * tasa_periodo).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        # Generar fechas
        fechas = calculate_payment_dates(
            request.fecha_primer_vencimiento, n_cuotas, request.modalidad
        )

        # Generar cuotas
        cuotas = []
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

            cuota = CuotaDetalle(
                numero_cuota=i + 1,
                fecha_vencimiento=fechas[i],
                saldo_inicial=monto,
                capital=capital,
                interes=interes,
                cuota=cuota_total,
                saldo_final=saldo_final,
            )

            cuotas.append(cuota)
            total_interes += interes

        resumen = {
            "total_capital": monto,
            "total_interes": total_interes,
            "total_pagar": monto + total_interes,
            "cuota_periodica": interes_fijo,
            "cuota_final": cuotas[-1].cuota,
        }

        parametros = {
            "monto_financiado": monto,
            "tasa_interes_anual": request.tasa_interes_anual,
            "numero_cuotas": n_cuotas,
            "modalidad": request.modalidad,
            "sistema": "AMERICANO",
        }

        return TablaAmortizacionResponse(
            cuotas=cuotas, resumen=resumen, parametros=parametros
        )

    @staticmethod
    def crear_cuotas_prestamo(
        db: Session, prestamo_id: int, tabla: TablaAmortizacionResponse
    ) -> List[Cuota]:
        """
        Crea las cuotas en la BD para un préstamo

        Args:
            db: Sesión de base de datos
            prestamo_id: ID del préstamo
            tabla: Tabla de amortización generada

        Returns:
            List[Cuota]: Cuotas creadas
        """
        cuotas_creadas = []

        for cuota_detalle in tabla.cuotas:
            cuota = Cuota(
                prestamo_id=prestamo_id,
                numero_cuota=cuota_detalle.numero_cuota,
                fecha_vencimiento=cuota_detalle.fecha_vencimiento,
                monto_cuota=cuota_detalle.cuota,
                monto_capital=cuota_detalle.capital,
                monto_interes=cuota_detalle.interes,
                saldo_capital_inicial=cuota_detalle.saldo_inicial,
                saldo_capital_final=cuota_detalle.saldo_final,
                capital_pendiente=cuota_detalle.capital,
                interes_pendiente=cuota_detalle.interes,
                estado="PENDIENTE",
            )

            db.add(cuota)
            cuotas_creadas.append(cuota)

        db.commit()

        return cuotas_creadas

    @staticmethod
    def obtener_cuotas_prestamo(
        db: Session, prestamo_id: int, estado: Optional[str] = None
    ) -> List[Cuota]:
        """Obtiene las cuotas de un préstamo"""
        query = db.query(Cuota).filter(Cuota.prestamo_id == prestamo_id)

        if estado:
            query = query.filter(Cuota.estado == estado)

        return query.order_by(Cuota.numero_cuota).all()

    @staticmethod
    def recalcular_mora(
        db: Session,
        prestamo_id: int,
        tasa_mora_diaria: Decimal,
        fecha_calculo: Optional[date] = None,
    ) -> dict:
        """
        Recalcula la mora de todas las cuotas vencidas de un préstamo

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

            # Calcular nueva mora
            nueva_mora = cuota.calcular_mora(tasa_mora_diaria)

            # Actualizar
            cuota.monto_mora = nueva_mora
            cuota.dias_mora = (fecha_calculo - cuota.fecha_vencimiento).days
            cuota.tasa_mora = tasa_mora_diaria

            total_mora_nueva += nueva_mora
            cuotas_actualizadas += 1

        db.commit()

        return {
            "cuotas_actualizadas": cuotas_actualizadas,
            "total_mora_anterior": total_mora_anterior,
            "total_mora_nueva": total_mora_nueva,
            "diferencia": total_mora_nueva - total_mora_anterior,
        }
