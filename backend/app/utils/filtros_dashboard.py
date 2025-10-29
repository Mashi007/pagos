"""
Utilidades centralizadas para aplicar filtros de dashboard a queries
Cualquier KPI nuevo debe usar estas funciones para aplicar filtros automáticamente
"""

from datetime import date
from typing import Optional

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Query

from app.models.amortizacion import Cuota
from app.models.pago import Pago
from app.models.prestamo import Prestamo


class FiltrosDashboard:
    """
    Clase helper para aplicar filtros de dashboard a queries SQLAlchemy
    TODOS los KPIs deben usar esta clase para aplicar filtros automáticamente
    """

    @staticmethod
    def aplicar_filtros_prestamo(
        query: Query,
        analista: Optional[str] = None,
        concesionario: Optional[str] = None,
        modelo: Optional[str] = None,
        fecha_inicio: Optional[date] = None,
        fecha_fin: Optional[date] = None,
    ) -> Query:
        """
        Aplica filtros comunes a queries de préstamos

        Uso:
            query = db.query(Prestamo).filter(Prestamo.activo.is_(True))
            query = FiltrosDashboard.aplicar_filtros_prestamo(
                query, analista, concesionario, modelo, fecha_inicio, fecha_fin
            )
        """
        if analista:
            query = query.filter(
                or_(
                    Prestamo.analista == analista,
                    Prestamo.producto_financiero == analista,
                )
            )
        if concesionario:
            query = query.filter(Prestamo.concesionario == concesionario)
        if modelo:
            query = query.filter(
                or_(Prestamo.producto == modelo, Prestamo.modelo_vehiculo == modelo)
            )
        if fecha_inicio:
            query = query.filter(Prestamo.fecha_registro >= fecha_inicio)
        if fecha_fin:
            query = query.filter(Prestamo.fecha_registro <= fecha_fin)
        return query

    @staticmethod
    def aplicar_filtros_pago(
        query: Query,
        analista: Optional[str] = None,
        concesionario: Optional[str] = None,
        modelo: Optional[str] = None,
        fecha_inicio: Optional[date] = None,
        fecha_fin: Optional[date] = None,
    ) -> Query:
        """
        Aplica filtros comunes a queries de pagos (requiere join con Prestamo)

        Uso:
            query = db.query(func.sum(Pago.monto_pagado))
            if analista or concesionario or modelo:
                query = query.join(Prestamo, Pago.prestamo_id == Prestamo.id)
            query = FiltrosDashboard.aplicar_filtros_pago(
                query, analista, concesionario, modelo, fecha_inicio, fecha_fin
            )
        """
        # Si hay filtros de préstamo, ya debe tener el join
        if analista or concesionario or modelo:
            if not any(str(Prestamo) in str(query) for _ in [None]):
                query = query.join(Prestamo, Pago.prestamo_id == Prestamo.id)

            if analista:
                query = query.filter(
                    or_(
                        Prestamo.analista == analista,
                        Prestamo.producto_financiero == analista,
                    )
                )
            if concesionario:
                query = query.filter(Prestamo.concesionario == concesionario)
            if modelo:
                query = query.filter(
                    or_(Prestamo.producto == modelo, Prestamo.modelo_vehiculo == modelo)
                )

        if fecha_inicio:
            query = query.filter(func.date(Pago.fecha_pago) >= fecha_inicio)
        if fecha_fin:
            query = query.filter(func.date(Pago.fecha_pago) <= fecha_fin)

        return query

    @staticmethod
    def aplicar_filtros_cuota(
        query: Query,
        analista: Optional[str] = None,
        concesionario: Optional[str] = None,
        modelo: Optional[str] = None,
        fecha_inicio: Optional[date] = None,
        fecha_fin: Optional[date] = None,
    ) -> Query:
        """
        Aplica filtros comunes a queries de cuotas (requiere join con Prestamo)

        Uso:
            query = db.query(func.count(Cuota.id)).join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            query = FiltrosDashboard.aplicar_filtros_cuota(
                query, analista, concesionario, modelo, fecha_inicio, fecha_fin
            )
        """
        # Las cuotas siempre requieren join con Prestamo
        if analista:
            query = query.filter(
                or_(
                    Prestamo.analista == analista,
                    Prestamo.producto_financiero == analista,
                )
            )
        if concesionario:
            query = query.filter(Prestamo.concesionario == concesionario)
        if modelo:
            query = query.filter(
                or_(Prestamo.producto == modelo, Prestamo.modelo_vehiculo == modelo)
            )
        if fecha_inicio:
            query = query.filter(Prestamo.fecha_registro >= fecha_inicio)
        if fecha_fin:
            query = query.filter(Prestamo.fecha_registro <= fecha_fin)

        return query

    @staticmethod
    def obtener_parametros_filtros(
        analista: Optional[str] = None,
        concesionario: Optional[str] = None,
        modelo: Optional[str] = None,
        fecha_inicio: Optional[date] = None,
        fecha_fin: Optional[date] = None,
        consolidado: Optional[bool] = None,
    ) -> dict:
        """
        Convierte parámetros de filtros en diccionario para pasar a funciones
        """
        params = {}
        if analista:
            params["analista"] = analista
        if concesionario:
            params["concesionario"] = concesionario
        if modelo:
            params["modelo"] = modelo
        if fecha_inicio:
            params["fecha_inicio"] = fecha_inicio
        if fecha_fin:
            params["fecha_fin"] = fecha_fin
        if consolidado:
            params["consolidado"] = consolidado
        return params
