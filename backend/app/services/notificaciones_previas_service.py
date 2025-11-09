"""
Servicio para calcular notificaciones previas
Clientes con cuotas próximas a vencer (5, 3, 1 días antes)
Solo clientes SIN cuotas atrasadas
"""

import logging
from datetime import date, timedelta
from typing import List, Optional

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.models.amortizacion import Cuota
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo

logger = logging.getLogger(__name__)


class NotificacionesPreviasService:
    """Servicio para gestionar notificaciones previas de vencimiento"""

    def __init__(self, db: Session):
        self.db = db

    def calcular_notificaciones_previas(self) -> List[dict]:
        """
        Calcula clientes con cuotas próximas a vencer (5, 3, 1 días antes)

        Condiciones:
        - Cliente NO tiene cuotas atrasadas (todas las cuotas pasadas están pagadas)
        - Tiene una cuota próxima que vence en 5, 3 o 1 día

        Returns:
            Lista de diccionarios con información de clientes y préstamos
        """
        hoy = date.today()

        # Fechas objetivo: 5, 3 y 1 día antes de vencimiento
        fecha_5_dias = hoy + timedelta(days=5)
        fecha_3_dias = hoy + timedelta(days=3)
        fecha_1_dia = hoy + timedelta(days=1)

        try:
            # Obtener préstamos aprobados con sus cuotas
            prestamos_aprobados = self.db.query(Prestamo).filter(Prestamo.estado == "APROBADO").all()

            resultados = []

            for prestamo in prestamos_aprobados:
                # Verificar que NO tenga cuotas atrasadas
                # Cuotas atrasadas: vencidas y no pagadas (estado != "PAGADO")
                cuotas_atrasadas = (
                    self.db.query(Cuota)
                    .filter(
                        and_(
                            Cuota.prestamo_id == prestamo.id,
                            Cuota.fecha_vencimiento < hoy,
                            Cuota.estado != "PAGADO",  # Excluir cuotas pagadas
                        )
                    )
                    .count()
                )

                # Si tiene cuotas atrasadas, saltar este préstamo
                if cuotas_atrasadas > 0:
                    continue

                # Buscar cuota próxima que vence en 5, 3 o 1 día
                # Solo cuotas que aún no están pagadas y están pendientes o adelantadas
                cuota_proxima = (
                    self.db.query(Cuota)
                    .filter(
                        and_(
                            Cuota.prestamo_id == prestamo.id,
                            Cuota.fecha_vencimiento.in_([fecha_5_dias, fecha_3_dias, fecha_1_dia]),
                            Cuota.estado.in_(["PENDIENTE", "ADELANTADO"]),  # Cuotas pendientes o adelantadas
                        )
                    )
                    .order_by(Cuota.fecha_vencimiento.asc())
                    .first()
                )

                if cuota_proxima:
                    # Calcular días antes de vencimiento
                    dias_antes = (cuota_proxima.fecha_vencimiento - hoy).days

                    # Obtener datos del cliente
                    cliente = self.db.query(Cliente).filter(Cliente.id == prestamo.cliente_id).first()

                    if cliente:
                        resultado = {
                            "prestamo_id": prestamo.id,
                            "cliente_id": cliente.id,
                            "nombre": cliente.nombres,  # nombres ya incluye nombres + apellidos
                            "cedula": prestamo.cedula,
                            "modelo_vehiculo": prestamo.modelo_vehiculo or prestamo.producto or "N/A",
                            "correo": cliente.email,
                            "telefono": cliente.telefono,
                            "dias_antes_vencimiento": dias_antes,
                            "fecha_vencimiento": cuota_proxima.fecha_vencimiento.isoformat(),
                            "numero_cuota": cuota_proxima.numero_cuota,
                            "monto_cuota": float(cuota_proxima.monto_cuota),
                        }
                        resultados.append(resultado)

            # Ordenar por días antes de vencimiento (1, 3, 5) y luego por fecha
            resultados.sort(key=lambda x: (x["dias_antes_vencimiento"], x["fecha_vencimiento"]))

            logger.info(f"✅ Calculadas {len(resultados)} notificaciones previas")
            return resultados

        except Exception as e:
            logger.error(f"❌ Error calculando notificaciones previas: {e}", exc_info=True)
            return []

    def obtener_notificaciones_previas_cached(self) -> List[dict]:
        """
        Obtiene notificaciones previas (calculadas a las 2 AM)
        Por ahora, calcula en tiempo real. En el futuro se puede cachear.
        """
        return self.calcular_notificaciones_previas()
