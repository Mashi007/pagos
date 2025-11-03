"""
Servicio de Notificaciones Automáticas
Monitorea cuotas pendientes y envía notificaciones según fechas
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from pytz import timezone
from sqlalchemy.orm import Session

from app.models.amortizacion import Cuota
from app.models.cliente import Cliente
from app.models.notificacion import Notificacion
from app.models.notificacion_plantilla import NotificacionPlantilla
from app.models.prestamo import Prestamo
from app.services.email_service import EmailService

logger = logging.getLogger(__name__)

# Zona horaria de Caracas
CARACAS_TZ = timezone("America/Caracas")


class NotificacionAutomaticaService:
    """Servicio para enviar notificaciones automáticas por fechas de cuotas"""

    def __init__(self, db: Session):
        self.db = db
        self.email_service = EmailService()

    def obtener_cuotas_pendientes(self) -> List[Cuota]:
        """
        Obtener todas las cuotas pendientes

        Returns:
            Lista de cuotas pendientes
        """
        try:
            cuotas_pendientes = self.db.query(Cuota).filter(Cuota.estado.in_(["PENDIENTE", "ATRASADO", "PARCIAL"])).all()

            logger.info(f"Encontradas {len(cuotas_pendientes)} cuotas pendientes")
            return cuotas_pendientes

        except Exception as e:
            logger.error(f"Error obteniendo cuotas pendientes: {e}")
            return []

    def calcular_dias_para_vencimiento(self, fecha_vencimiento: datetime) -> int:
        """
        Calcular días hasta la fecha de vencimiento

        Args:
            fecha_vencimiento: Fecha de vencimiento de la cuota

        Returns:
            Días hasta vencimiento (negativo si ya venció)
        """
        try:
            hoy = datetime.now(CARACAS_TZ).date()
            fecha_venc = fecha_vencimiento.date() if isinstance(fecha_vencimiento, datetime) else fecha_vencimiento

            dias = (fecha_venc - hoy).days
            return dias

        except Exception as e:
            logger.error(f"Error calculando días: {e}")
            return 0

    def obtener_plantilla_por_tipo(self, tipo: str) -> Optional[NotificacionPlantilla]:
        """
        Obtener plantilla por tipo de notificación

        Args:
            tipo: Tipo de notificación (PAGO_5_DIAS_ANTES, etc.)

        Returns:
            Plantilla encontrada o None
        """
        try:
            plantilla = (
                self.db.query(NotificacionPlantilla)
                .filter(
                    NotificacionPlantilla.tipo == tipo,
                    NotificacionPlantilla.activa.is_(True),
                )
                .first()
            )

            return plantilla

        except Exception as e:
            logger.error(f"Error obteniendo plantilla {tipo}: {e}")
            return None

    def enviar_notificacion(self, cuota: Cuota, plantilla: NotificacionPlantilla, cliente: Cliente) -> bool:
        """
        Enviar notificación al cliente

        Args:
            cuota: Cuota a notificar
            plantilla: Plantilla a usar
            cliente: Cliente destinatario

        Returns:
            True si se envió exitosamente, False si hubo error
        """
        try:
            # Obtener información del préstamo
            prestamo = self.db.query(Prestamo).filter(Prestamo.id == cuota.prestamo_id).first()

            if not prestamo:
                logger.error(f"Préstamo {cuota.prestamo_id} no encontrado")
                return False

            # Preparar variables para la plantilla
            variables = {
                "nombre": cliente.nombres or "Cliente",
                "monto": f"{cuota.monto_cuota:.2f}",
                "fecha_vencimiento": (cuota.fecha_vencimiento.strftime("%d/%m/%Y") if cuota.fecha_vencimiento else "N/A"),
                "numero_cuota": str(cuota.numero_cuota),
                "credito_id": str(prestamo.id),
                "cedula": cliente.cedula or "N/A",
            }

            # Calcular días de atraso si aplica
            if cuota.fecha_vencimiento:
                dias_diferencia = self.calcular_dias_para_vencimiento(cuota.fecha_vencimiento)
                if dias_diferencia < 0:
                    variables["dias_atraso"] = str(abs(dias_diferencia))
                else:
                    variables["dias_atraso"] = "0"

            # Reemplazar variables en el asunto y cuerpo
            asunto = plantilla.asunto
            cuerpo = plantilla.cuerpo

            for key, value in variables.items():
                asunto = asunto.replace(f"{{{{{key}}}}}", str(value))
                cuerpo = cuerpo.replace(f"{{{{{key}}}}}", str(value))

            # Verificar si ya existe una notificación similar hoy
            notificacion_existente = (
                self.db.query(Notificacion)
                .filter(
                    Notificacion.cliente_id == cliente.id,
                    Notificacion.tipo == plantilla.tipo,
                )
                .first()
            )

            if notificacion_existente:
                logger.info(f"Notificación {plantilla.tipo} ya fue enviada a cliente {cliente.id}")
                return False

            # Crear registro de notificación
            nueva_notif = Notificacion(
                cliente_id=cliente.id,
                tipo=plantilla.tipo,
                canal="EMAIL",
                asunto=asunto,
                mensaje=cuerpo,
                estado="PENDIENTE",
            )
            self.db.add(nueva_notif)
            self.db.commit()

            # Enviar email si el cliente tiene email
            if cliente.email:
                resultado = self.email_service.send_email(
                    to_emails=[cliente.email],
                    subject=asunto,
                    body=cuerpo,
                    is_html=True,
                )

                if resultado.get("success"):
                    # Marcar como enviada
                    nueva_notif.estado = "ENVIADA"
                    nueva_notif.enviada_en = datetime.now(CARACAS_TZ)
                    self.db.commit()
                    logger.info(f"Notificación enviada a {cliente.email}")
                    return True
                else:
                    nueva_notif.estado = "FALLIDA"
                    nueva_notif.error_mensaje = resultado.get("message", "Error desconocido")
                    self.db.commit()
                    logger.error(f"Error enviando email: {resultado.get('message')}")
                    return False

            logger.warning(f"Cliente {cliente.id} no tiene email configurado")
            return False

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error enviando notificación: {e}")
            return False

    def _determinar_tipo_plantilla(self, dias: int) -> Optional[str]:
        """Determina el tipo de plantilla según los días hasta vencimiento"""
        mapeo_dias = {
            5: "PAGO_5_DIAS_ANTES",
            3: "PAGO_3_DIAS_ANTES",
            1: "PAGO_1_DIA_ANTES",
            0: "PAGO_DIA_0",
            -1: "PAGO_1_DIA_ATRASADO",
            -3: "PAGO_3_DIAS_ATRASADO",
            -5: "PAGO_5_DIAS_ATRASADO",
        }
        return mapeo_dias.get(dias)

    def _procesar_cuota(self, cuota: Cuota, stats: Dict[str, int]) -> bool:
        """Procesa una cuota individual. Returns: True si se procesó exitosamente"""
        try:
            cliente = self.db.query(Cliente).filter(Cliente.id == cuota.cliente_id).first()

            if not cliente:
                logger.warning(f"Cliente {cuota.cliente_id} no encontrado")
                return False

            if not cuota.fecha_vencimiento:
                return False

            dias = self.calcular_dias_para_vencimiento(cuota.fecha_vencimiento)
            tipo_plantilla = self._determinar_tipo_plantilla(dias)

            if not tipo_plantilla:
                return False

            plantilla = self.obtener_plantilla_por_tipo(tipo_plantilla)

            if not plantilla:
                stats["sin_plantilla"] += 1
                logger.warning(f"No hay plantilla para tipo {tipo_plantilla}")
                return False

            if self.enviar_notificacion(cuota, plantilla, cliente):
                stats["enviadas"] += 1
            else:
                stats["errores"] += 1

            return True

        except Exception as e:
            stats["errores"] += 1
            logger.error(f"Error procesando cuota {cuota.id}: {e}")
            return False

    def procesar_notificaciones_automaticas(self) -> Dict[str, int]:
        """
        Procesar todas las notificaciones automáticas necesarias

        Returns:
            Diccionario con estadísticas de envío
        """
        stats = {
            "procesadas": 0,
            "enviadas": 0,
            "errores": 0,
            "sin_plantilla": 0,
            "sin_email": 0,
        }

        try:
            cuotas_pendientes = self.obtener_cuotas_pendientes()

            for cuota in cuotas_pendientes:
                if self._procesar_cuota(cuota, stats):
                    stats["procesadas"] += 1

            logger.info(f"Procesamiento completado: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Error en procesamiento automático: {e}")
            stats["errores"] += 1
            return stats
