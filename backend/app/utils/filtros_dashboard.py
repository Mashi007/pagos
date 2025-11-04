"""
Utilidades centralizadas para aplicar filtros de dashboard a queries
Cualquier KPI nuevo debe usar estas funciones para aplicar filtros automáticamente
"""

from datetime import date
from typing import Any, Optional

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Query

from app.models.amortizacion import Cuota
from app.models.pago import Pago
from app.models.pago_staging import PagoStaging
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
            query = db.query(Prestamo).filter(Prestamo.estado == "APROBADO")
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
            query = query.filter(or_(Prestamo.producto == modelo, Prestamo.modelo_vehiculo == modelo))
        if fecha_inicio:
            query = query.filter(Prestamo.fecha_registro >= fecha_inicio)
        if fecha_fin:
            query = query.filter(Prestamo.fecha_registro <= fecha_fin)
        return query

    @staticmethod
    def _detectar_tabla_pago(query: Query) -> Any:
        """Detecta si la query usa Pago o PagoStaging"""
        try:
            compiled_sql = str(query.statement.compile(compile_kwargs={"literal_binds": False})).lower()
            if "pagos_staging" in compiled_sql or "pagostaging" in compiled_sql:
                return PagoStaging
            if "pagos" in compiled_sql and "staging" not in compiled_sql:
                return Pago
        except (AttributeError, Exception):
            try:
                if hasattr(query, "column_descriptions"):
                    desc = query.column_descriptions
                    for col in desc:
                        if "entity" in col and col["entity"]:
                            entity = col["entity"]
                            if hasattr(entity, "__tablename__"):
                                if entity.__tablename__ == "pagos_staging":
                                    return PagoStaging
                                if entity.__tablename__ == "pagos":
                                    return Pago
            except (AttributeError, Exception):
                pass
        return PagoStaging  # Default

    @staticmethod
    def _verificar_join_prestamo(query: Query) -> bool:
        """Verifica si ya existe un JOIN con Prestamo"""
        try:
            compiled_sql = str(query.statement.compile(compile_kwargs={"literal_binds": False})).lower()
            prestamo_table_name = Prestamo.__tablename__.lower()
            if prestamo_table_name in compiled_sql:
                count_joins = compiled_sql.count("join") + compiled_sql.count("from")
                return count_joins > 0 and prestamo_table_name in compiled_sql
        except (AttributeError, Exception):
            pass
        return False

    @staticmethod
    def _aplicar_filtros_prestamo(query: Query, analista: Optional[str], concesionario: Optional[str], modelo: Optional[str]) -> Query:
        """Aplica filtros de préstamo a la query"""
        if analista:
            query = query.filter(or_(Prestamo.analista == analista, Prestamo.producto_financiero == analista))
        if concesionario:
            query = query.filter(Prestamo.concesionario == concesionario)
        if modelo:
            query = query.filter(or_(Prestamo.producto == modelo, Prestamo.modelo_vehiculo == modelo))
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
            query = FiltrosDashboard.aplicar_filtros_pago(
                query, analista, concesionario, modelo, fecha_inicio, fecha_fin
            )
            # NOTA: El método detecta automáticamente si necesita hacer el JOIN
        """
        tabla_pago = FiltrosDashboard._detectar_tabla_pago(query)

        if analista or concesionario or modelo:
            necesita_join = not FiltrosDashboard._verificar_join_prestamo(query)
            if necesita_join:
                query = query.join(Prestamo, tabla_pago.prestamo_id == Prestamo.id)
            query = FiltrosDashboard._aplicar_filtros_prestamo(query, analista, concesionario, modelo)

        if fecha_inicio:
            query = query.filter(func.date(tabla_pago.fecha_pago) >= fecha_inicio)
        if fecha_fin:
            query = query.filter(func.date(tabla_pago.fecha_pago) <= fecha_fin)

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
            query = query.filter(or_(Prestamo.producto == modelo, Prestamo.modelo_vehiculo == modelo))
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
    ) -> dict[str, Any]:
        """
        Convierte parámetros de filtros en diccionario para pasar a funciones
        """
        params: dict[str, Any] = {}
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
        if consolidado is not None:
            params["consolidado"] = consolidado
        return params
