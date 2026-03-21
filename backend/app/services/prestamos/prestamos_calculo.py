"""Servicios de cálculos financieros para préstamos."""

from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, List, Tuple
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session

from app.models.tasa_cambio_diaria import TasaCambioDiaria
from .prestamos_excepciones import (
    PrestamoValidationError,
    AmortizacionCalculoError,
    TasaCambioNotFoundError,
)


class PrestamosCalculo:
    """Servicio de cálculos financieros para préstamos."""

    def __init__(self, db: Session):
        self.db = db

    def obtener_tasa_cambio_actual(self) -> Optional[float]:
        """
        Obtiene la tasa de cambio actual (más reciente).
        Retorna None si no hay tasas disponibles.
        """
        try:
            from sqlalchemy import desc
            tasa = self.db.query(TasaCambioDiaria)\
                .order_by(desc(TasaCambioDiaria.fecha))\
                .first()

            if tasa:
                return float(tasa.valor)
            return None
        except Exception as e:
            # En caso de error, retornar None para no bloquear el sistema
            return None

    def obtener_tasa_cambio_fecha(self, fecha: date) -> Optional[float]:
        """
        Obtiene la tasa de cambio para una fecha específica.
        Si no existe para esa fecha, retorna la más cercana anterior.
        """
        try:
            from sqlalchemy import desc
            tasa = self.db.query(TasaCambioDiaria)\
                .filter(TasaCambioDiaria.fecha <= fecha)\
                .order_by(desc(TasaCambioDiaria.fecha))\
                .first()

            if tasa:
                return float(tasa.valor)
            return None
        except Exception:
            return None

    def convertir_pesos_a_dolares(
        self,
        monto_pesos: float,
        tasa: Optional[float] = None
    ) -> float:
        """
        Convierte monto de pesos a dólares usando la tasa proporcionada.
        Si no se proporciona tasa, obtiene la actual.
        """
        if not monto_pesos or monto_pesos <= 0:
            return 0.0

        if tasa is None:
            tasa = self.obtener_tasa_cambio_actual()

        if tasa is None or tasa <= 0:
            return float(monto_pesos)

        try:
            resultado = float(monto_pesos) / float(tasa)
            return self._redondear_monto(resultado, 2)
        except (ValueError, ZeroDivisionError):
            return float(monto_pesos)

    def convertir_dolares_a_pesos(
        self,
        monto_dolares: float,
        tasa: Optional[float] = None
    ) -> float:
        """
        Convierte monto de dólares a pesos usando la tasa proporcionada.
        """
        if not monto_dolares or monto_dolares <= 0:
            return 0.0

        if tasa is None:
            tasa = self.obtener_tasa_cambio_actual()

        if tasa is None or tasa <= 0:
            return float(monto_dolares)

        try:
            resultado = float(monto_dolares) * float(tasa)
            return self._redondear_monto(resultado, 2)
        except (ValueError, TypeError):
            return float(monto_dolares)

    def calcular_interes_simple(
        self,
        principal: float,
        tasa_anual: float,
        dias: int
    ) -> float:
        """
        Calcula interés simple.

        Args:
            principal: Monto principal
            tasa_anual: Tasa de interés anual (ej: 12 para 12%)
            dias: Número de días

        Returns:
            Monto de interés calculado
        """
        try:
            principal_d = Decimal(str(principal))
            tasa_d = Decimal(str(tasa_anual)) / Decimal('100')
            dias_d = Decimal(str(dias))

            interes = (principal_d * tasa_d * dias_d) / Decimal('365')
            return float(interes.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        except (ValueError, TypeError):
            return 0.0

    def calcular_interes_compuesto(
        self,
        principal: float,
        tasa_anual: float,
        periodos: int,
        dias_entre_periodos: int = 30
    ) -> float:
        """
        Calcula interés compuesto.

        Args:
            principal: Monto principal
            tasa_anual: Tasa de interés anual (ej: 12 para 12%)
            periodos: Número de períodos
            dias_entre_periodos: Días entre cada período (default: 30)

        Returns:
            Monto total de intereses
        """
        try:
            principal_d = Decimal(str(principal))
            tasa_d = Decimal(str(tasa_anual)) / Decimal('100')
            periodos_d = Decimal(str(periodos))
            dias_entre_d = Decimal(str(dias_entre_periodos))

            # Tasa por período
            tasa_periodo = (tasa_d * dias_entre_d) / Decimal('365')

            # Monto final con interés compuesto
            monto_final = principal_d * (Decimal('1') + tasa_periodo) ** periodos_d

            # Interés es el diferencial
            interes = monto_final - principal_d
            return float(interes.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        except (ValueError, TypeError):
            return 0.0

    def calcular_cuota_fija(
        self,
        principal: float,
        tasa_anual: float,
        numero_cuotas: int,
        modalidad: str = 'MENSUAL'
    ) -> float:
        """
        Calcula cuota fija usando sistema de amortización francés (cuota constante).

        Args:
            principal: Monto del préstamo
            tasa_anual: Tasa de interés anual
            numero_cuotas: Número de cuotas
            modalidad: Modalidad de pago (MENSUAL, QUINCENAL, etc)

        Returns:
            Valor de la cuota fija
        """
        try:
            if numero_cuotas <= 0:
                raise AmortizacionCalculoError("Número de cuotas debe ser mayor a 0")

            # Calcular días entre cuotas según modalidad
            dias_periodo = self._calcular_dias_periodo(modalidad)

            # Tasa por período
            tasa_annual_decimal = Decimal(str(tasa_anual)) / Decimal('100')
            tasa_periodo = tasa_annual_decimal * Decimal(str(dias_periodo)) / Decimal('365')

            principal_d = Decimal(str(principal))
            cuotas_d = Decimal(str(numero_cuotas))

            # Si tasa es 0, retornar cuota simple
            if tasa_periodo == 0:
                cuota = principal_d / cuotas_d
                return float(cuota.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

            # Fórmula: C = P * [i(1+i)^n] / [(1+i)^n - 1]
            factor = (Decimal('1') + tasa_periodo) ** cuotas_d
            numerador = tasa_periodo * factor
            denominador = factor - Decimal('1')

            cuota = principal_d * (numerador / denominador)
            return float(cuota.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

        except (ValueError, TypeError) as e:
            raise AmortizacionCalculoError(f"Error calculando cuota fija: {str(e)}")

    def calcular_interes_periodo(
        self,
        saldo_actual: float,
        tasa_anual: float,
        modalidad: str = 'MENSUAL'
    ) -> float:
        """
        Calcula el interés para un período específico.

        Args:
            saldo_actual: Saldo vigente
            tasa_anual: Tasa de interés anual
            modalidad: Modalidad de pago

        Returns:
            Interés del período
        """
        try:
            dias_periodo = self._calcular_dias_periodo(modalidad)
            tasa_annual_decimal = Decimal(str(tasa_anual)) / Decimal('100')
            saldo_d = Decimal(str(saldo_actual))

            interes = saldo_d * tasa_annual_decimal * Decimal(str(dias_periodo)) / Decimal('365')
            return float(interes.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        except (ValueError, TypeError):
            return 0.0

    def calcular_amortizacion_periodo(
        self,
        cuota: float,
        interes_periodo: float
    ) -> float:
        """
        Calcula la amortización (capital) de una cuota.
        amortización = cuota - interés
        """
        try:
            amortizacion = Decimal(str(cuota)) - Decimal(str(interes_periodo))
            return max(
                float(amortizacion.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)),
                0.0
            )
        except (ValueError, TypeError):
            return 0.0

    def _calcular_dias_periodo(self, modalidad: str) -> int:
        """
        Calcula el número de días en un período según la modalidad.

        Args:
            modalidad: MENSUAL, QUINCENAL, SEMANAL, DIARIA

        Returns:
            Número de días en el período
        """
        modalidad_dias = {
            'MENSUAL': 30,
            'QUINCENAL': 15,
            'SEMANAL': 7,
            'DIARIA': 1,
        }
        return modalidad_dias.get(modalidad.upper(), 30)

    def _redondear_monto(self, monto: float, decimales: int = 2) -> float:
        """Redondea un monto a N decimales."""
        try:
            d = Decimal(str(monto))
            return float(d.quantize(Decimal(10) ** -decimales, rounding=ROUND_HALF_UP))
        except (ValueError, TypeError):
            return 0.0

    def calcular_dias_entre_fechas(
        self,
        fecha_inicio: date,
        fecha_fin: date
    ) -> int:
        """Calcula días entre dos fechas."""
        try:
            if isinstance(fecha_inicio, datetime):
                fecha_inicio = fecha_inicio.date()
            if isinstance(fecha_fin, datetime):
                fecha_fin = fecha_fin.date()

            delta = fecha_fin - fecha_inicio
            return max(0, delta.days)
        except Exception:
            return 0

    def calcular_tasa_efectiva(
        self,
        tasa_nominal: float,
        periodos_por_anio: int
    ) -> float:
        """
        Calcula tasa efectiva anual a partir de tasa nominal.
        Fórmula: TEA = (1 + i/n)^n - 1
        """
        try:
            tasa_d = Decimal(str(tasa_nominal)) / Decimal('100')
            n_d = Decimal(str(periodos_por_anio))

            tasa_efectiva = (
                (Decimal('1') + tasa_d / n_d) ** n_d - Decimal('1')
            ) * Decimal('100')

            return float(tasa_efectiva.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP))
        except (ValueError, TypeError):
            return float(tasa_nominal)

    def calcular_vat(
        self,
        monto: float,
        tasa_vat: float = 13.0
    ) -> float:
        """
        Calcula el IVA/VAT sobre un monto.

        Args:
            monto: Monto base
            tasa_vat: Tasa de VAT (default: 13%)

        Returns:
            Monto de VAT/IVA
        """
        try:
            monto_d = Decimal(str(monto))
            tasa_d = Decimal(str(tasa_vat)) / Decimal('100')
            vat = monto_d * tasa_d
            return float(vat.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))
        except (ValueError, TypeError):
            return 0.0

    def redondear_monto(self, monto: float, decimales: int = 2) -> float:
        """Redondea un monto a N decimales."""
        return self._redondear_monto(monto, decimales)
