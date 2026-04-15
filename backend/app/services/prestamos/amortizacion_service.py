"""Servicio de amortización de préstamos."""

from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Optional, Tuple
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.prestamo import Prestamo
from app.models.cuota import Cuota
from app.services.prestamos.fechas_prestamo_coherencia import fecha_para_amortizacion
from app.services.cuota_estado import (
    clasificar_estado_cuota,
    dias_retraso_desde_vencimiento,
    hoy_negocio,
)
from .prestamos_calculo import PrestamosCalculo
from .prestamos_excepciones import (
    AmortizacionCalculoError,
    PrestamoNotFoundError,
    CuotaNotFoundError,
)


class AmortizacionService:
    """
    Servicio integral para gestión de calendarios de amortización de préstamos.
    Maneja creación, actualización y consultas de tablas de amortización.
    """

    def __init__(self, db: Session):
        self.db = db
        self.calculo = PrestamosCalculo(db)

    @staticmethod
    def _float_cuota_monto(cuota) -> float:
        v = getattr(cuota, "monto", None)
        if v is None:
            v = getattr(cuota, "monto_cuota", None)
        return float(v or 0)

    @staticmethod
    def _float_total_pagado(cuota) -> float:
        return float(getattr(cuota, "total_pagado", None) or 0)

    def _cuota_esta_pagada_completa(self, cuota) -> bool:
        return self._float_total_pagado(cuota) >= self._float_cuota_monto(cuota) - 0.01

    def generar_tabla_amortizacion(
        self,
        prestamo_id: int,
        fecha_inicio: Optional[date] = None,
        regenerar: bool = False
    ) -> List[Dict]:
        """
        Genera o regenera la tabla de amortización completa para un préstamo.

        Args:
            prestamo_id: ID del préstamo
            fecha_inicio: Fecha de inicio del primer período (default: hoy)
            regenerar: Si True, borra cuotas existentes antes de generar

        Returns:
            Lista de diccionarios con información de cada cuota
        """
        # Obtener préstamo
        prestamo = self.db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
        if not prestamo:
            raise PrestamoNotFoundError(prestamo_id)

        if fecha_inicio is None:
            fecha_inicio = fecha_para_amortizacion(prestamo) or hoy_negocio()

        # Si regenerar es True, eliminar cuotas existentes
        if regenerar:
            self.db.query(Cuota).filter(Cuota.prestamo_id == prestamo_id).delete()
            self.db.commit()

        # Calcular cuota fija
        cuota_fija = self.calculo.calcular_cuota_fija(
            float(prestamo.total_financiamiento),
            float(prestamo.tasa_interes),
            prestamo.numero_cuotas,
            prestamo.modalidad_pago
        )

        # Generar tabla de amortización
        tabla = []
        saldo_actual = float(prestamo.total_financiamiento)
        fecha_vencimiento = fecha_inicio
        dias_periodo = self.calculo._calcular_dias_periodo(prestamo.modalidad_pago)

        for numero_cuota in range(1, prestamo.numero_cuotas + 1):
            # Calcular interés del período
            interes = self.calculo.calcular_interes_periodo(
                saldo_actual,
                float(prestamo.tasa_interes),
                prestamo.modalidad_pago
            )

            # Calcular amortización (capital)
            amortizacion = self.calculo.calcular_amortizacion_periodo(
                cuota_fija,
                interes
            )

            # Actualizar saldo (puede quedar negativo por redondeo en última cuota)
            saldo_nuevo = max(saldo_actual - amortizacion, 0.0)

            # Si es la última cuota, ajustar para que saldo quede en 0
            if numero_cuota == prestamo.numero_cuotas:
                amortizacion = saldo_actual
                saldo_nuevo = 0.0

            # Crear registro de cuota
            cuota_data = {
                'prestamo_id': prestamo_id,
                'numero_cuota': numero_cuota,
                'fecha_vencimiento': fecha_vencimiento,
                'monto_cuota': cuota_fija,
                'interes_cuota': interes,
                'amortizacion_cuota': amortizacion,
                'saldo_vigente': saldo_nuevo,
                'estado': 'PENDIENTE',
                'pagado': False,
                'monto_pagado': 0.0,
            }

            tabla.append(cuota_data)

            # Crear objeto Cuota en BD si no existe
            cuota_existente = self.db.query(Cuota).filter(
                and_(
                    Cuota.prestamo_id == prestamo_id,
                    Cuota.numero_cuota == numero_cuota
                )
            ).first()

            if not cuota_existente:
                cuota_obj = Cuota(**cuota_data)
                self.db.add(cuota_obj)

            # Siguiente período
            fecha_vencimiento = self.calcular_siguiente_fecha_cuota(
                fecha_vencimiento,
                prestamo.modalidad_pago
            )
            saldo_actual = saldo_nuevo

        self.db.commit()
        return tabla

    def obtener_tabla_amortizacion(self, prestamo_id: int) -> List[Dict]:
        """
        Obtiene la tabla de amortización existente de un préstamo.

        Returns:
            Lista de diccionarios con información de cada cuota
        """
        cuotas = self.db.query(Cuota).filter(
            Cuota.prestamo_id == prestamo_id
        ).order_by(Cuota.numero_cuota).all()

        tabla = []
        for cuota in cuotas:
            item = {
                'id': cuota.id,
                'numero_cuota': cuota.numero_cuota,
                'fecha_vencimiento': cuota.fecha_vencimiento.isoformat() if hasattr(cuota.fecha_vencimiento, 'isoformat') else str(cuota.fecha_vencimiento),
                'monto_cuota': AmortizacionService._float_cuota_monto(cuota),
                'interes_cuota': float(cuota.interes_cuota) if hasattr(cuota, 'interes_cuota') else 0.0,
                'amortizacion_cuota': float(cuota.amortizacion_cuota) if hasattr(cuota, 'amortizacion_cuota') else 0.0,
                'saldo_vigente': float(cuota.saldo_vigente) if hasattr(cuota, 'saldo_vigente') else 0.0,
                'estado': getattr(cuota, 'estado', 'PENDIENTE'),
                'pagado': getattr(cuota, 'pagado', False),
                'monto_pagado': AmortizacionService._float_total_pagado(cuota),
                'total_pagado': AmortizacionService._float_total_pagado(cuota),
            }
            tabla.append(item)

        return tabla

    def calcular_siguiente_fecha_cuota(self, fecha_actual: date, modalidad: str) -> date:
        """
        Calcula la siguiente fecha de vencimiento basada en la modalidad de pago.

        Args:
            fecha_actual: Fecha base
            modalidad: MENSUAL, QUINCENAL, SEMANAL, DIARIA

        Returns:
            Nueva fecha de vencimiento
        """
        try:
            if isinstance(fecha_actual, datetime):
                fecha_actual = fecha_actual.date()

            if modalidad == 'MENSUAL':
                # Sumar un mes
                if fecha_actual.month == 12:
                    return date(fecha_actual.year + 1, 1, fecha_actual.day)
                else:
                    return date(fecha_actual.year, fecha_actual.month + 1, fecha_actual.day)
            elif modalidad == 'QUINCENAL':
                return fecha_actual + timedelta(days=15)
            elif modalidad == 'SEMANAL':
                return fecha_actual + timedelta(days=7)
            elif modalidad == 'DIARIA':
                return fecha_actual + timedelta(days=1)
            else:
                return fecha_actual + timedelta(days=30)
        except Exception:
            return fecha_actual + timedelta(days=30)

    def obtener_cuota(self, cuota_id: int) -> Optional[Dict]:
        """Obtiene una cuota específica."""
        cuota = self.db.query(Cuota).filter(Cuota.id == cuota_id).first()
        if not cuota:
            raise CuotaNotFoundError(cuota_id)

        return {
            'id': cuota.id,
            'prestamo_id': getattr(cuota, 'prestamo_id', None),
            'numero_cuota': getattr(cuota, 'numero_cuota', 0),
            'fecha_vencimiento': getattr(cuota, 'fecha_vencimiento', None),
            'monto_cuota': self._float_cuota_monto(cuota),
            'interes_cuota': float(getattr(cuota, 'interes_cuota', 0.0)),
            'amortizacion_cuota': float(getattr(cuota, 'amortizacion_cuota', 0.0)),
            'saldo_vigente': float(getattr(cuota, 'saldo_vigente', 0.0)),
            'estado': getattr(cuota, 'estado', 'PENDIENTE'),
            'pagado': getattr(cuota, 'pagado', False),
            'monto_pagado': self._float_total_pagado(cuota),
            'total_pagado': self._float_total_pagado(cuota),
        }

    def registrar_pago_cuota(
        self,
        cuota_id: int,
        monto_pagado: float,
        fecha_pago: Optional[date] = None
    ) -> Dict:
        """
        Registra un pago de cuota.

        Args:
            cuota_id: ID de la cuota
            monto_pagado: Monto pagado
            fecha_pago: Fecha del pago (default: hoy negocio Caracas)

        Returns:
            Información actualizada de la cuota
        """
        if fecha_pago is None:
            fecha_pago = hoy_negocio()

        cuota = self.db.query(Cuota).filter(Cuota.id == cuota_id).first()
        if not cuota:
            raise CuotaNotFoundError(cuota_id)

        monto_cuota = self._float_cuota_monto(cuota)
        monto_actual = self._float_total_pagado(cuota)
        nuevo_total = monto_actual + float(monto_pagado or 0)

        estado = clasificar_estado_cuota(
            nuevo_total,
            monto_cuota,
            getattr(cuota, "fecha_vencimiento", None),
            fecha_pago,
        )

        if hasattr(cuota, "total_pagado"):
            cuota.total_pagado = Decimal(str(round(nuevo_total, 2)))
        if hasattr(cuota, "estado"):
            cuota.estado = estado

        self.db.add(cuota)
        self.db.commit()
        self.db.refresh(cuota)

        return self.obtener_cuota(cuota_id)

    def calcular_estado_amortizacion(self, prestamo_id: int) -> Dict:
        """
        Calcula el estado general de amortización de un préstamo.

        Returns:
            Dict con: {
                'total_cuotas': int,
                'cuotas_pagadas': int,
                'cuotas_pendientes': int,
                'cuotas_parciales': int,
                'saldo_total_pendiente': float,
                'monto_pagado': float,
                'proxima_cuota_vencimiento': date,
                'cuotas_en_atraso': int,
            }
        """
        cuotas = self.db.query(Cuota).filter(
            Cuota.prestamo_id == prestamo_id
        ).all()

        if not cuotas:
            raise PrestamoNotFoundError(prestamo_id)

        total_cuotas = len(cuotas)
        cuotas_pagadas = 0
        cuotas_pendientes = 0
        cuotas_parciales = 0
        cuotas_en_atraso = 0
        saldo_total = 0.0
        monto_pagado_total = 0.0
        proxima_cuota_vencimiento = None

        hoy = hoy_negocio()

        for cuota in cuotas:
            fecha_vencimiento = getattr(cuota, "fecha_vencimiento", None)
            monto_cuota = self._float_cuota_monto(cuota)
            paid = self._float_total_pagado(cuota)
            estado = clasificar_estado_cuota(
                paid, monto_cuota, fecha_vencimiento, hoy
            )

            if estado in ("PAGADO", "PAGO_ADELANTADO"):
                cuotas_pagadas += 1
            elif estado == "PARCIAL":
                cuotas_parciales += 1
                saldo_total += max(monto_cuota - paid, 0.0)
            else:
                cuotas_pendientes += 1
                saldo_total += max(monto_cuota - paid, 0.0)
                if dias_retraso_desde_vencimiento(fecha_vencimiento, hoy) >= 1:
                    cuotas_en_atraso += 1

            monto_pagado_total += paid

            if proxima_cuota_vencimiento is None and estado not in (
                "PAGADO",
                "PAGO_ADELANTADO",
            ):
                proxima_cuota_vencimiento = fecha_vencimiento

        return {
            'total_cuotas': total_cuotas,
            'cuotas_pagadas': cuotas_pagadas,
            'cuotas_pendientes': cuotas_pendientes,
            'cuotas_parciales': cuotas_parciales,
            'saldo_total_pendiente': self.calculo._redondear_monto(saldo_total, 2),
            'monto_pagado_total': self.calculo._redondear_monto(monto_pagado_total, 2),
            'proxima_cuota_vencimiento': (
                proxima_cuota_vencimiento.isoformat()
                if proxima_cuota_vencimiento else None
            ),
            'cuotas_en_atraso': cuotas_en_atraso,
            'porcentaje_pagado': (
                (cuotas_pagadas / total_cuotas * 100)
                if total_cuotas > 0 else 0.0
            ),
        }

    def obtener_cuotas_vencidas(self, prestamo_id: int) -> List[Dict]:
        """Cuotas no cubiertas al 100% con al menos 1 dia de retraso (Caracas)."""
        hoy = hoy_negocio()
        cuotas = (
            self.db.query(Cuota)
            .filter(Cuota.prestamo_id == prestamo_id)
            .order_by(Cuota.numero_cuota)
            .all()
        )
        out = []
        for c in cuotas:
            if self._cuota_esta_pagada_completa(c):
                continue
            if dias_retraso_desde_vencimiento(c.fecha_vencimiento, hoy) >= 1:
                out.append(c)
        return [self._serializar_cuota(c) for c in out]

    def obtener_cuotas_proximas(
        self,
        prestamo_id: int,
        dias_adelante: int = 30
    ) -> List[Dict]:
        """Obtiene cuotas que vencen en los próximos N días."""
        hoy = hoy_negocio()
        fecha_limite = hoy + timedelta(days=dias_adelante)

        cuotas = self.db.query(Cuota).filter(
            and_(
                Cuota.prestamo_id == prestamo_id,
                Cuota.fecha_vencimiento >= hoy,
                Cuota.fecha_vencimiento <= fecha_limite,
            )
        ).order_by(Cuota.numero_cuota).all()

        return [
            self._serializar_cuota(c)
            for c in cuotas
            if not self._cuota_esta_pagada_completa(c)
        ]

    def calcular_interes_penalizacion_atraso(
        self,
        cuota_id: int,
        tasa_penalizacion_diaria: float = 1.0
    ) -> float:
        """
        Calcula intereses por penalización por atraso en una cuota.

        Args:
            cuota_id: ID de la cuota
            tasa_penalizacion_diaria: Tasa diaria de penalización (%)

        Returns:
            Monto de penalización
        """
        cuota = self.db.query(Cuota).filter(Cuota.id == cuota_id).first()
        if not cuota:
            raise CuotaNotFoundError(cuota_id)

        fecha_vencimiento = getattr(cuota, 'fecha_vencimiento', None)
        if not fecha_vencimiento:
            return 0.0

        hoy = hoy_negocio()
        fv = fecha_vencimiento
        if isinstance(fv, datetime):
            fv = fv.date()
        if fv is None or fv >= hoy:
            return 0.0

        dias_atraso = dias_retraso_desde_vencimiento(fv, hoy)
        monto_cuota = self._float_cuota_monto(cuota)

        # Penalización = monto * tasa_diaria * días
        penalizacion = monto_cuota * (tasa_penalizacion_diaria / 100) * dias_atraso

        return self.calculo._redondear_monto(penalizacion, 2)

    def _serializar_cuota(self, cuota) -> Dict:
        """Convierte objeto Cuota a diccionario."""
        return {
            'id': cuota.id,
            'prestamo_id': getattr(cuota, 'prestamo_id', None),
            'numero_cuota': getattr(cuota, 'numero_cuota', 0),
            'fecha_vencimiento': (
                getattr(cuota, 'fecha_vencimiento', None).isoformat()
                if hasattr(getattr(cuota, 'fecha_vencimiento', None), 'isoformat') else
                str(getattr(cuota, 'fecha_vencimiento', None))
            ),
            'monto_cuota': self._float_cuota_monto(cuota),
            'interes_cuota': float(getattr(cuota, 'interes_cuota', 0.0)),
            'amortizacion_cuota': float(getattr(cuota, 'amortizacion_cuota', 0.0)),
            'saldo_vigente': float(getattr(cuota, 'saldo_vigente', 0.0)),
            'estado': getattr(cuota, 'estado', 'PENDIENTE'),
            'pagado': getattr(cuota, 'pagado', False),
            'monto_pagado': self._float_total_pagado(cuota),
            'total_pagado': self._float_total_pagado(cuota),
        }

    def regenerar_amortizacion_desde(
        self,
        prestamo_id: int,
        numero_cuota: int,
        tasa_actualizada: Optional[float] = None
    ) -> List[Dict]:
        """
        Regenera la tabla de amortización a partir de una cuota específica.
        Útil para ajustar tasas o montos.

        Args:
            prestamo_id: ID del préstamo
            numero_cuota: Número de cuota desde donde regenerar
            tasa_actualizada: Nueva tasa de interés (opcional)

        Returns:
            Nueva tabla de amortización
        """
        prestamo = self.db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
        if not prestamo:
            raise PrestamoNotFoundError(prestamo_id)

        # Obtener cuota anterior para usar su saldo vigente
        cuota_anterior = self.db.query(Cuota).filter(
            and_(
                Cuota.prestamo_id == prestamo_id,
                Cuota.numero_cuota == numero_cuota - 1
            )
        ).first()

        if cuota_anterior:
            saldo_inicial = float(getattr(cuota_anterior, 'saldo_vigente', 0.0)) or 0.0
            fecha_inicio = getattr(cuota_anterior, 'fecha_vencimiento', hoy_negocio())
        else:
            saldo_inicial = float(prestamo.total_financiamiento)
            fecha_inicio = fecha_para_amortizacion(prestamo) or hoy_negocio()

        # Usar tasa actualizada si se proporciona
        tasa_a_usar = tasa_actualizada or float(prestamo.tasa_interes)

        # Eliminar cuotas desde numero_cuota en adelante
        self.db.query(Cuota).filter(
            and_(
                Cuota.prestamo_id == prestamo_id,
                Cuota.numero_cuota >= numero_cuota
            )
        ).delete()
        self.db.commit()

        # Recalcular cuota fija con el nuevo saldo
        cuotas_restantes = prestamo.numero_cuotas - numero_cuota + 1

        cuota_fija = self.calculo.calcular_cuota_fija(
            saldo_inicial,
            tasa_a_usar,
            cuotas_restantes,
            prestamo.modalidad_pago
        )

        # Generar nuevas cuotas
        tabla = []
        saldo_actual = saldo_inicial
        fecha_vencimiento = self.calcular_siguiente_fecha_cuota(
            fecha_inicio,
            prestamo.modalidad_pago
        )

        for numero in range(numero_cuota, prestamo.numero_cuotas + 1):
            interes = self.calculo.calcular_interes_periodo(
                saldo_actual,
                tasa_a_usar,
                prestamo.modalidad_pago
            )

            amortizacion = self.calculo.calcular_amortizacion_periodo(
                cuota_fija,
                interes
            )

            saldo_nuevo = max(saldo_actual - amortizacion, 0.0)

            if numero == prestamo.numero_cuotas:
                amortizacion = saldo_actual
                saldo_nuevo = 0.0

            cuota_data = {
                'prestamo_id': prestamo_id,
                'numero_cuota': numero,
                'fecha_vencimiento': fecha_vencimiento,
                'monto_cuota': cuota_fija,
                'interes_cuota': interes,
                'amortizacion_cuota': amortizacion,
                'saldo_vigente': saldo_nuevo,
                'estado': 'PENDIENTE',
                'pagado': False,
                'monto_pagado': 0.0,
            }

            tabla.append(cuota_data)

            cuota_obj = Cuota(**cuota_data)
            self.db.add(cuota_obj)

            fecha_vencimiento = self.calcular_siguiente_fecha_cuota(
                fecha_vencimiento,
                prestamo.modalidad_pago
            )
            saldo_actual = saldo_nuevo

        self.db.commit()
        return tabla
