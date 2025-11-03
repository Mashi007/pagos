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
        # Si hay filtros de préstamo, hacer JOIN solo si no existe ya
        if analista or concesionario or modelo:
            # Verificar si ya existe un JOIN con Prestamo compilando el SQL
            necesita_join = True
            try:
                # Compilar el statement a SQL para verificar si ya tiene la tabla prestamos
                compiled_sql = str(query.statement.compile(compile_kwargs={"literal_binds": False})).lower()
                # Buscar referencias a la tabla prestamos (puede estar como "prestamos" o con esquema)
                prestamo_table_name = Prestamo.__tablename__
                # Verificar si la tabla ya aparece en el SQL (puede estar en FROM o JOIN)
                if prestamo_table_name.lower() in compiled_sql:
                    # Contar cuántas veces aparece "JOIN prestamos" o "FROM prestamos"
                    count_joins = compiled_sql.count("join") + compiled_sql.count("from")
                    # Si ya aparece al menos una vez, probablemente ya hay un JOIN
                    if count_joins > 0 and prestamo_table_name.lower() in compiled_sql:
                        necesita_join = False
            except (AttributeError, Exception):
                # Si hay error al compilar, asumir que necesita JOIN (seguro fallar que fallar silenciosamente)
                necesita_join = True

            # Hacer JOIN solo si es necesario
            if necesita_join:
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
                query = query.filter(or_(Prestamo.producto == modelo, Prestamo.modelo_vehiculo == modelo))

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
