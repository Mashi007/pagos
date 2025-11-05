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

# ⚠️ PagoStaging eliminado - usar Pago
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
        """Detecta si la query usa Pago (siempre retorna Pago ahora)"""
        try:
            compiled_sql = str(query.statement.compile(compile_kwargs={"literal_binds": False})).lower()
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
                                if entity.__tablename__ == "pagos":
                                    return Pago
            except (AttributeError, Exception):
                pass
        return Pago  # Default: siempre usar tabla pagos

    @staticmethod
    def _verificar_join_prestamo(query: Query) -> bool:
        """Verifica si ya existe un JOIN con Prestamo"""
        try:
            # Verificar en column_descriptions
            if hasattr(query, "column_descriptions"):
                desc = query.column_descriptions
                for col in desc:
                    if "entity" in col and col["entity"]:
                        entity = col["entity"]
                        if hasattr(entity, "__tablename__"):
                            if entity.__tablename__ == Prestamo.__tablename__:
                                return True

            # Verificar en el statement compilado
            compiled_sql = str(query.statement.compile(compile_kwargs={"literal_binds": False})).lower()
            prestamo_table_name = Prestamo.__tablename__.lower()
            if prestamo_table_name in compiled_sql:
                # Verificar que haya un JOIN explícito (no solo FROM)
                if "join" in compiled_sql or "inner join" in compiled_sql or "left join" in compiled_sql:
                    return True
        except (AttributeError, Exception):
            pass
        return False

    @staticmethod
    def _aplicar_filtros_prestamo(
        query: Query, analista: Optional[str], concesionario: Optional[str], modelo: Optional[str]
    ) -> Query:
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
            query = db.query(func.count(Cuota.id)).select_from(Cuota).join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            query = FiltrosDashboard.aplicar_filtros_cuota(
                query, analista, concesionario, modelo, fecha_inicio, fecha_fin
            )
        """
        # Verificar si ya existe un JOIN con Prestamo
        necesita_join = not FiltrosDashboard._verificar_join_prestamo(query)

        # Si necesita filtros de Prestamo y no hay JOIN, hacerlo explícitamente
        if (analista or concesionario or modelo or fecha_inicio or fecha_fin) and necesita_join:
            # Intentar hacer el JOIN directamente
            # Si la query ya tiene select_from, el JOIN funcionará
            # Si no, SQLAlchemy puede inferir la tabla base desde las columnas
            try:
                query = query.join(Prestamo, Cuota.prestamo_id == Prestamo.id)
            except Exception:
                # Si falla, intentar con select_from explícito
                try:
                    query = query.select_from(Cuota).join(Prestamo, Cuota.prestamo_id == Prestamo.id)
                except Exception as e:
                    # Si aún falla, loggear pero continuar sin JOIN
                    # Los filtros fallarán después pero al menos no romperá la query
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.warning(f"No se pudo hacer JOIN con Prestamo en aplicar_filtros_cuota: {e}")
                    # Retornar query sin filtros de Prestamo
                    return query

        # Aplicar filtros
        if analista:
            query = query.filter(
                or_(
                    Prestamo.analista == analista,
                    Prestamo.producto_financiero == analista,
                    Prestamo.usuario_proponente == analista,  # También por usuario_proponente
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
