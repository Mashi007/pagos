"""Servicios de cálculos para pagos."""

from decimal import Decimal
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc

from app.models.tasa_cambio_diaria import TasaCambioDiaria
from .pagos_excepciones import PagoValidationError


class PagosCalculo:
    """Servicio de cálculos financieros para pagos."""

    def __init__(self, db: Session):
        self.db = db

    def obtener_tasa_cambio_actual(self) -> Optional[float]:
        """
        Obtiene la tasa de cambio actual (más reciente).
        Retorna None si no hay tasas disponibles.
        """
        try:
            tasa = self.db.query(TasaCambioDiaria)\
                .order_by(desc(TasaCambioDiaria.fecha))\
                .first()
            
            if tasa:
                return float(tasa.valor)
            return None
        except Exception as e:
            # En caso de error, retornar None para no bloquear el sistema
            return None

    def convertir_pesos_a_dolares(self, monto_pesos: float, tasa: Optional[float] = None) -> float:
        """
        Convierte monto de pesos a dólares usando la tasa proporcionada.
        Si no se proporciona tasa, obtiene la actual. Si no hay tasa, retorna el monto original.
        """
        if not monto_pesos or monto_pesos <= 0:
            return 0.0

        # Si no se proporciona tasa, obtener la actual
        if tasa is None:
            tasa = self.obtener_tasa_cambio_actual()

        # Si no hay tasa disponible, retornar el monto original
        if tasa is None or tasa <= 0:
            return float(monto_pesos)

        try:
            resultado = float(monto_pesos) / float(tasa)
            return round(resultado, 2)
        except (ValueError, ZeroDivisionError):
            return float(monto_pesos)

    def convertir_dolares_a_pesos(self, monto_dolares: float, tasa: Optional[float] = None) -> float:
        """
        Convierte monto de dólares a pesos usando la tasa proporcionada.
        Si no se proporciona tasa, obtiene la actual. Si no hay tasa, retorna el monto original.
        """
        if not monto_dolares or monto_dolares <= 0:
            return 0.0

        # Si no se proporciona tasa, obtener la actual
        if tasa is None:
            tasa = self.obtener_tasa_cambio_actual()

        # Si no hay tasa disponible, retornar el monto original
        if tasa is None or tasa <= 0:
            return float(monto_dolares)

        try:
            resultado = float(monto_dolares) * float(tasa)
            return round(resultado, 2)
        except (ValueError, TypeError):
            return float(monto_dolares)

    def calcular_interes(
        self, 
        monto_principal: float, 
        dias_atraso: int, 
        tasa_interes_diaria: float = 0.001
    ) -> float:
        """
        Calcula intereses por atraso.
        
        Args:
            monto_principal: Monto sobre el cual calcular intereses
            dias_atraso: Número de días de atraso
            tasa_interes_diaria: Tasa de interés diaria (default: 0.1% diario)
        
        Returns:
            Monto de intereses calculado
        """
        if dias_atraso <= 0 or tasa_interes_diaria <= 0:
            return 0.0

        try:
            interes = float(monto_principal) * float(tasa_interes_diaria) * int(dias_atraso)
            return round(interes, 2)
        except (ValueError, TypeError):
            return 0.0

    def calcular_multa(
        self,
        monto_principal: float,
        porcentaje_multa: float = 5.0
    ) -> float:
        """
        Calcula multa por atraso como porcentaje del monto principal.
        
        Args:
            monto_principal: Monto sobre el cual calcular la multa
            porcentaje_multa: Porcentaje de multa (default: 5%)
        
        Returns:
            Monto de multa calculado
        """
        if porcentaje_multa < 0 or porcentaje_multa > 100:
            raise PagoValidationError("porcentaje_multa", "Porcentaje debe estar entre 0 y 100")

        try:
            multa = (float(monto_principal) * float(porcentaje_multa)) / 100
            return round(multa, 2)
        except (ValueError, TypeError):
            return 0.0

    def calcular_total_con_intereses_multa(
        self,
        monto_principal: float,
        dias_atraso: int = 0,
        porcentaje_multa: float = 5.0,
        tasa_interes_diaria: float = 0.001
    ) -> dict:
        """
        Calcula el total del pago incluyendo intereses y multa por atraso.
        
        Returns:
            Dict con desglose: {
                'principal': float,
                'interes': float,
                'multa': float,
                'total': float
            }
        """
        interes = self.calcular_interes(monto_principal, dias_atraso, tasa_interes_diaria)
        multa = self.calcular_multa(monto_principal, porcentaje_multa) if dias_atraso > 0 else 0.0
        total = float(monto_principal) + interes + multa

        return {
            'principal': round(float(monto_principal), 2),
            'interes': interes,
            'multa': multa,
            'total': round(total, 2),
        }

    def redondear_monto(self, monto: float, decimales: int = 2) -> float:
        """Redondea un monto a N decimales."""
        try:
            return round(float(monto), decimales)
        except (ValueError, TypeError):
            return 0.0
