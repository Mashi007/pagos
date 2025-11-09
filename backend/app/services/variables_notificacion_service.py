"""
Servicio para construir variables de notificaciones desde la base de datos
Usa las variables configuradas en notificacion_variables para obtener datos reales
"""

import logging
from datetime import date, datetime
from typing import Dict, Optional

from sqlalchemy import inspect
from sqlalchemy.orm import Session

from app.models.amortizacion import Cuota
from app.models.cliente import Cliente
from app.models.notificacion_variable import NotificacionVariable
from app.models.pago import Pago
from app.models.prestamo import Prestamo

logger = logging.getLogger(__name__)


class VariablesNotificacionService:
    """Servicio para construir variables dinámicas desde la BD"""

    def __init__(self, db: Session):
        self.db = db
        self._variables_cache: Optional[list[NotificacionVariable]] = None

    def obtener_variables_configuradas(self, solo_activas: bool = True) -> list[NotificacionVariable]:
        """Obtener todas las variables configuradas desde la BD"""
        try:
            if self._variables_cache is None:
                query = self.db.query(NotificacionVariable)
                if solo_activas:
                    query = query.filter(NotificacionVariable.activa == True)
                self._variables_cache = query.all()
            return self._variables_cache
        except Exception as e:
            logger.error(f"Error obteniendo variables configuradas: {e}")
            return []

    def obtener_valor_campo_bd(
        self,
        tabla: str,
        campo: str,
        cliente: Cliente,
        prestamo: Optional[Prestamo] = None,
        cuota: Optional[Cuota] = None,
        pago: Optional[Pago] = None,
    ) -> str:
        """
        Obtener el valor de un campo de la BD según la tabla especificada

        Args:
            tabla: Nombre de la tabla (clientes, prestamos, cuotas, pagos)
            campo: Nombre del campo en la tabla
            cliente: Objeto Cliente
            prestamo: Objeto Prestamo (opcional)
            cuota: Objeto Cuota (opcional)
            pago: Objeto Pago (opcional)

        Returns:
            Valor del campo como string, o string vacío si no se encuentra
        """
        try:
            objeto = None

            if tabla == "clientes":
                objeto = cliente
            elif tabla == "prestamos" and prestamo:
                objeto = prestamo
            elif tabla == "cuotas" and cuota:
                objeto = cuota
            elif tabla == "pagos" and pago:
                objeto = pago

            if not objeto:
                return ""

            # Usar inspect para obtener el valor del atributo
            inspector = inspect(objeto.__class__)
            if campo in [col.key for col in inspector.columns]:
                valor = getattr(objeto, campo, None)

                if valor is None:
                    return ""

                # Formatear según el tipo
                if isinstance(valor, (date, datetime)):
                    return valor.strftime("%d/%m/%Y")
                elif isinstance(valor, bool):
                    return "Sí" if valor else "No"
                elif isinstance(valor, (int, float)):
                    if campo in [
                        "monto_cuota",
                        "monto_capital",
                        "monto_interes",
                        "monto_mora",
                        "monto_morosidad",
                        "total_financiamiento",
                        "cuota_periodo",
                        "monto_pagado",
                        "capital_pagado",
                        "interes_pagado",
                        "mora_pagada",
                    ]:
                        return f"{valor:.2f}"
                    return str(valor)
                else:
                    return str(valor)

            return ""

        except Exception as e:
            logger.error(f"Error obteniendo valor de {tabla}.{campo}: {e}")
            return ""

    def construir_variables_desde_dict(
        self,
        datos_query: Dict,
        cliente: Optional[Cliente] = None,
        prestamo: Optional[Prestamo] = None,
        cuota: Optional[Cuota] = None,
    ) -> Dict[str, str]:
        """
        Construir variables desde un diccionario de resultados de query SQL
        Útil para schedulers y servicios que usan queries SQL directas

        Args:
            datos_query: Diccionario con datos de la query (ej: resultado de SQL)
            cliente: Cliente (opcional, se intenta obtener desde datos_query si no se proporciona)
            prestamo: Préstamo (opcional)
            cuota: Cuota (opcional)

        Returns:
            Diccionario con nombre_variable -> valor_real
        """
        variables = {}

        try:
            # Obtener todas las variables configuradas y activas
            variables_configuradas = self.obtener_variables_configuradas(solo_activas=True)

            # Construir variables desde la BD usando objetos si están disponibles
            if cliente:
                return self.construir_variables_desde_bd(
                    cliente=cliente,
                    prestamo=prestamo,
                    cuota=cuota,
                )

            # Si no hay objetos, usar el diccionario de la query
            for var_config in variables_configuradas:
                # Mapear campos comunes de queries SQL
                valor = ""

                if var_config.tabla == "clientes":
                    # Mapear campos comunes de clientes en queries
                    campo_map = {
                        "nombres": "nombre_cliente",
                        "cedula": "cedula",
                        "email": "correo",
                        "telefono": "telefono",
                    }
                    campo_query = campo_map.get(var_config.campo_bd, var_config.campo_bd)
                    valor = str(datos_query.get(campo_query, datos_query.get(var_config.campo_bd, "")))

                elif var_config.tabla == "prestamos":
                    campo_query = var_config.campo_bd
                    valor = str(datos_query.get(campo_query, ""))

                elif var_config.tabla == "cuotas":
                    campo_map = {
                        "monto_cuota": "monto_cuota",
                        "fecha_vencimiento": "fecha_vencimiento",
                        "numero_cuota": "numero_cuota",
                    }
                    campo_query = campo_map.get(var_config.campo_bd, var_config.campo_bd)
                    valor_raw = datos_query.get(campo_query, "")

                    # Formatear según tipo
                    if campo_query == "fecha_vencimiento" and valor_raw:
                        if isinstance(valor_raw, (date, datetime)):
                            valor = valor_raw.strftime("%d/%m/%Y")
                        else:
                            valor = str(valor_raw)
                    elif campo_query in ["monto_cuota", "monto_capital", "monto_interes"]:
                        try:
                            valor = f"{float(valor_raw):.2f}" if valor_raw else "0.00"
                        except:
                            valor = str(valor_raw) if valor_raw else "0.00"
                    else:
                        valor = str(valor_raw) if valor_raw else ""

                variables[var_config.nombre_variable] = valor

            # Agregar variables comunes desde el diccionario
            if "nombre" not in variables:
                variables["nombre"] = datos_query.get("nombre_cliente", datos_query.get("nombres", ""))

            if "monto" not in variables:
                monto = datos_query.get("monto_cuota", 0)
                try:
                    variables["monto"] = f"{float(monto):.2f}"
                except:
                    variables["monto"] = str(monto)

            if "fecha_vencimiento" not in variables:
                fecha = datos_query.get("fecha_vencimiento", "")
                if fecha:
                    if isinstance(fecha, (date, datetime)):
                        variables["fecha_vencimiento"] = fecha.strftime("%d/%m/%Y")
                    else:
                        variables["fecha_vencimiento"] = str(fecha)
                else:
                    variables["fecha_vencimiento"] = ""

            if "numero_cuota" not in variables:
                variables["numero_cuota"] = str(datos_query.get("numero_cuota", ""))

            if "credito_id" not in variables:
                variables["credito_id"] = str(datos_query.get("prestamo_id", ""))

            if "cedula" not in variables:
                variables["cedula"] = datos_query.get("cedula", "")

            if "dias_atraso" in datos_query:
                variables["dias_atraso"] = str(datos_query.get("dias_atraso", "0"))

            if "dias_antes_vencimiento" in datos_query:
                variables["dias_antes"] = str(datos_query.get("dias_antes_vencimiento", ""))

            return variables

        except Exception as e:
            logger.error(f"Error construyendo variables desde dict: {e}")
            # Retornar variables básicas en caso de error
            return {
                "nombre": datos_query.get("nombre_cliente", ""),
                "cedula": datos_query.get("cedula", ""),
            }

    def construir_variables_desde_bd(
        self,
        cliente: Cliente,
        prestamo: Optional[Prestamo] = None,
        cuota: Optional[Cuota] = None,
        pago: Optional[Pago] = None,
        dias_atraso: Optional[int] = None,
    ) -> Dict[str, str]:
        """
        Construir diccionario de variables desde la BD usando las variables configuradas

        Args:
            cliente: Cliente
            prestamo: Préstamo (opcional)
            cuota: Cuota (opcional)
            pago: Pago (opcional)
            dias_atraso: Días de atraso (opcional, para variables calculadas)

        Returns:
            Diccionario con nombre_variable -> valor_real
        """
        variables = {}

        try:
            # Obtener todas las variables configuradas y activas
            variables_configuradas = self.obtener_variables_configuradas(solo_activas=True)

            # Construir variables desde la BD
            for var_config in variables_configuradas:
                valor = self.obtener_valor_campo_bd(
                    tabla=var_config.tabla,
                    campo=var_config.campo_bd,
                    cliente=cliente,
                    prestamo=prestamo,
                    cuota=cuota,
                    pago=pago,
                )
                variables[var_config.nombre_variable] = valor

            # Agregar variables calculadas comunes (si no están configuradas)
            if "dias_atraso" not in variables and dias_atraso is not None:
                variables["dias_atraso"] = str(abs(dias_atraso))

            # Variables legacy para compatibilidad (si no están configuradas)
            if "nombre" not in variables:
                variables["nombre"] = cliente.nombres or ""

            if cuota:
                if "monto" not in variables:
                    variables["monto"] = f"{cuota.monto_cuota:.2f}" if cuota.monto_cuota else "0.00"
                if "fecha_vencimiento" not in variables:
                    if cuota.fecha_vencimiento:
                        variables["fecha_vencimiento"] = cuota.fecha_vencimiento.strftime("%d/%m/%Y")
                    else:
                        variables["fecha_vencimiento"] = ""
                if "numero_cuota" not in variables:
                    variables["numero_cuota"] = str(cuota.numero_cuota) if cuota.numero_cuota else ""

            if prestamo:
                if "credito_id" not in variables:
                    variables["credito_id"] = str(prestamo.id) if prestamo.id else ""

            if "cedula" not in variables:
                variables["cedula"] = cliente.cedula or ""

            return variables

        except Exception as e:
            logger.error(f"Error construyendo variables desde BD: {e}")
            # Retornar variables básicas en caso de error
            return {
                "nombre": cliente.nombres or "",
                "cedula": cliente.cedula or "",
            }

    def reemplazar_variables_en_texto(self, texto: str, variables: Dict[str, str]) -> str:
        """
        Reemplazar variables {{variable}} en un texto con valores reales

        Args:
            texto: Texto con variables {{variable}}
            variables: Diccionario nombre_variable -> valor

        Returns:
            Texto con variables reemplazadas
        """
        resultado = texto

        for nombre_var, valor in variables.items():
            # Reemplazar {{nombre_var}} con el valor
            resultado = resultado.replace(f"{{{{{nombre_var}}}}}", str(valor))

        return resultado
