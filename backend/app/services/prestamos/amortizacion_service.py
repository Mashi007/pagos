"""Servicio de amortización de préstamos."""

from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Optional, Tuple
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from app.models.prestamo import Prestamo
from app.models.cuota import Cuota
from app.models.cuota_pago import CuotaPago
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
            fecha_inicio = prestamo.fecha_base_calculo or date.today()

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
                'monto_cuota': float(cuota.monto_cuota) if hasattr(cuota, 'monto_cuota') else 0.0,
                'interes_cuota': float(cuota.interes_cuota) if hasattr(cuota, 'interes_cuota') else 0.0,
                'amortizacion_cuota': float(cuota.amortizacion_cuota) if hasattr(cuota, 'amortizacion_cuota') else 0.0,
                'saldo_vigente': float(cuota.saldo_vigente) if hasattr(cuota, 'saldo_vigente') else 0.0,
                'estado': getattr(cuota, 'estado', 'PENDIENTE'),
                'pagado': getattr(cuota, 'pagado', False),
                'monto_pagado': float(getattr(cuota, 'monto_pagado', 0.0)) or 0.0,
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
            'monto_cuota': float(getattr(cuota, 'monto_cuota', 0.0)),
            'interes_cuota': float(getattr(cuota, 'interes_cuota', 0.0)),
            'amortizacion_cuota': float(getattr(cuota, 'amortizacion_cuota', 0.0)),
            'saldo_vigente': float(getattr(cuota, 'saldo_vigente', 0.0)),
            'estado': getattr(cuota, 'estado', 'PENDIENTE'),
            'pagado': getattr(cuota, 'pagado', False),
            'monto_pagado': float(getattr(cuota, 'monto_pagado', 0.0)),
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
            fecha_pago: Fecha del pago (default: hoy)

        Returns:
            Información actualizada de la cuota
        """
        if fecha_pago is None:
            fecha_pago = date.today()

        cuota = self.db.query(Cuota).filter(Cuota.id == cuota_id).first()
        if not cuota:
            raise CuotaNotFoundError(cuota_id)

        monto_cuota = float(getattr(cuota, 'monto_cuota', 0.0))
        monto_actual = float(getattr(cuota, 'monto_pagado', 0.0)) or 0.0

        # Actualizar monto pagado
        nuevo_total = monto_actual + monto_pagado
        monto_restante = max(monto_cuota - nuevo_total, 0.0)

        # Determinar estado
        if monto_restante <= 0:
            estado = 'PAGADO'
            pagado = True
        elif nuevo_total > 0:
            estado = 'PARCIAL'
            pagado = False
        else:
            estado = 'PENDIENTE'
            pagado = False

        # Actualizar cuota
        if hasattr(cuota, 'monto_pagado'):
            cuota.monto_pagado = Decimal(str(nuevo_total))
        if hasattr(cuota, 'estado'):
            cuota.estado = estado
        if hasattr(cuota, 'pagado'):
            cuota.pagado = pagado

        self.db.add(cuota)
        self.db.commit()
        self.db.refresh(cuota)

        # Registrar movimiento de pago si existe tabla CuotaPago
        try:
            pago = CuotaPago(
                cuota_id=cuota_id,
                monto=Decimal(str(monto_pagado)),
                fecha_pago=fecha_pago,
            )
            self.db.add(pago)
            self.db.commit()
        except Exception:
            # Si la tabla CuotaPago no existe, continuar
            pass

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

        hoy = date.today()

        for cuota in cuotas:
            estado = getattr(cuota, 'estado', 'PENDIENTE')
            fecha_vencimiento = getattr(cuota, 'fecha_vencimiento', None)
            monto_cuota = float(getattr(cuota, 'monto_cuota', 0.0)) or 0.0
            monto_pagado = float(getattr(cuota, 'monto_pagado', 0.0)) or 0.0

            if estado == 'PAGADO':
                cuotas_pagadas += 1
            elif estado == 'PARCIAL':
                cuotas_parciales += 1
                saldo_total += monto_cuota - monto_pagado
            else:
                cuotas_pendientes += 1
                saldo_total += monto_cuota - monto_pagado

                # Verificar atraso
                if fecha_vencimiento and fecha_vencimiento < hoy:
                    cuotas_en_atraso += 1

            monto_pagado_total += monto_pagado

            # Próxima cuota sin pagar
            if proxima_cuota_vencimiento is None and estado != 'PAGADO':
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
        """Obtiene todas las cuotas vencidas de un préstamo."""
        hoy = date.today()

        cuotas = self.db.query(Cuota).filter(
            and_(
                Cuota.prestamo_id == prestamo_id,
                Cuota.fecha_vencimiento < hoy,
                Cuota.estado != 'PAGADO'
            )
        ).order_by(Cuota.numero_cuota).all()

        return [self._serializar_cuota(c) for c in cuotas]

    def obtener_cuotas_proximas(
        self,
        prestamo_id: int,
        dias_adelante: int = 30
    ) -> List[Dict]:
        """Obtiene cuotas que vencen en los próximos N días."""
        hoy = date.today()
        fecha_limite = hoy + timedelta(days=dias_adelante)

        cuotas = self.db.query(Cuota).filter(
            and_(
                Cuota.prestamo_id == prestamo_id,
                Cuota.fecha_vencimiento >= hoy,
                Cuota.fecha_vencimiento <= fecha_limite,
                Cuota.estado != 'PAGADO'
            )
        ).order_by(Cuota.numero_cuota).all()

        return [self._serializar_cuota(c) for c in cuotas]

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

        hoy = date.today()
        if fecha_vencimiento >= hoy:
            return 0.0

        dias_atraso = (hoy - fecha_vencimiento).days
        monto_cuota = float(getattr(cuota, 'monto_cuota', 0.0)) or 0.0

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
            'monto_cuota': float(getattr(cuota, 'monto_cuota', 0.0)),
            'interes_cuota': float(getattr(cuota, 'interes_cuota', 0.0)),
            'amortizacion_cuota': float(getattr(cuota, 'amortizacion_cuota', 0.0)),
            'saldo_vigente': float(getattr(cuota, 'saldo_vigente', 0.0)),
            'estado': getattr(cuota, 'estado', 'PENDIENTE'),
            'pagado': getattr(cuota, 'pagado', False),
            'monto_pagado': float(getattr(cuota, 'monto_pagado', 0.0)) or 0.0,
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
            fecha_inicio = getattr(cuota_anterior, 'fecha_vencimiento', date.today())
        else:
            saldo_inicial = float(prestamo.total_financiamiento)
            fecha_inicio = prestamo.fecha_base_calculo or date.today()

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
