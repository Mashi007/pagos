"""
Servicio de Notificaciones Automáticas
Monitorea cuotas pendientes y envía notificaciones según fechas
OPTIMIZADO: Usa JOINs, cache de plantillas y procesamiento en batch
"""

import logging
import time
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional, Tuple

from pytz import timezone  # type: ignore[import-untyped]
from sqlalchemy.orm import Session

from app.models.amortizacion import Cuota
from app.models.cliente import Cliente
from app.models.notificacion import Notificacion
from app.models.notificacion_plantilla import NotificacionPlantilla
from app.models.prestamo import Prestamo
from app.services.email_service import EmailService
from app.services.variables_notificacion_service import VariablesNotificacionService

logger = logging.getLogger(__name__)

# Zona horaria de Caracas
CARACAS_TZ = timezone("America/Caracas")

# Días relevantes para notificaciones
DIAS_NOTIFICACION = [-5, -3, -1, 0, 1, 3, 5]


class NotificacionAutomaticaService:
    """Servicio para enviar notificaciones automáticas por fechas de cuotas"""

    def __init__(self, db: Session):
        self.db = db
        self.email_service = EmailService(db=db)
        self.variables_service = VariablesNotificacionService(db=db)
        self._plantillas_cache: Dict[str, Optional[NotificacionPlantilla]] = {}

    def obtener_cuotas_pendientes_optimizado(self) -> List[Tuple[Cuota, Prestamo, Cliente]]:
        """
        Obtener cuotas pendientes que necesitan notificación HOY usando JOINs optimizados
        Solo procesa cuotas que vencen en días relevantes (-5, -3, -1, 0, 1, 3, 5 días)

        Returns:
            Lista de tuplas (Cuota, Prestamo, Cliente) ya cargadas
        """
        try:
            hoy = datetime.now(CARACAS_TZ).date()

            # Calcular fechas relevantes para filtrar
            fechas_relevantes = [hoy + timedelta(days=d) for d in DIAS_NOTIFICACION]

            # Query optimizada con JOINs para evitar N+1
            # Usar cliente_id primero (más confiable), luego cédula como fallback
            cuotas_con_relaciones = (
                self.db.query(Cuota, Prestamo, Cliente)
                .join(Prestamo, Prestamo.id == Cuota.prestamo_id)
                .join(Cliente, Cliente.id == Prestamo.cliente_id)  # Usar relación directa por cliente_id
                .filter(
                    Cuota.estado.in_(["PENDIENTE", "ATRASADO", "PARCIAL"]),
                    Cuota.fecha_vencimiento.in_(fechas_relevantes),  # Solo fechas relevantes
                    Prestamo.estado == "APROBADO",  # Solo préstamos aprobados
                )
                .all()
            )

            logger.info(f"Encontradas {len(cuotas_con_relaciones)} cuotas pendientes que necesitan notificación hoy")
            return cuotas_con_relaciones

        except Exception as e:
            logger.error(f"Error obteniendo cuotas pendientes: {e}")
            return []

    def obtener_cuotas_pendientes(self) -> List[Cuota]:
        """
        Obtener todas las cuotas pendientes (método legacy - mantener para compatibilidad)
        DEPRECATED: Usar obtener_cuotas_pendientes_optimizado() en su lugar
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
        Obtener plantilla por tipo de notificación (con cache)

        Args:
            tipo: Tipo de notificación (PAGO_5_DIAS_ANTES, etc.)

        Returns:
            Plantilla encontrada o None
        """
        # Usar cache para evitar queries repetidas
        if tipo in self._plantillas_cache:
            return self._plantillas_cache[tipo]

        try:
            plantilla = (
                self.db.query(NotificacionPlantilla)
                .filter(
                    NotificacionPlantilla.tipo == tipo,
                    NotificacionPlantilla.activa.is_(True),
                )
                .first()
            )

            # Guardar en cache
            self._plantillas_cache[tipo] = plantilla
            return plantilla

        except Exception as e:
            logger.error(f"Error obteniendo plantilla {tipo}: {e}")
            self._plantillas_cache[tipo] = None
            return None

    def _cargar_todas_plantillas(self) -> Dict[str, NotificacionPlantilla]:
        """Cargar todas las plantillas activas en memoria para evitar queries repetidas"""
        try:
            plantillas = self.db.query(NotificacionPlantilla).filter(NotificacionPlantilla.activa.is_(True)).all()

            cache = {p.tipo: p for p in plantillas}
            self._plantillas_cache.update(cache)
            logger.info(f"Cargadas {len(cache)} plantillas activas en cache")
            return cache
        except Exception as e:
            logger.error(f"Error cargando plantillas: {e}")
            return {}

    def enviar_notificacion_optimizada(
        self, cuota: Cuota, prestamo: Prestamo, plantilla: NotificacionPlantilla, cliente: Cliente
    ) -> bool:
        """
        Enviar notificación al cliente (versión optimizada con préstamo ya cargado)

        Args:
            cuota: Cuota a notificar
            prestamo: Prestamo ya cargado
            plantilla: Plantilla a usar
            cliente: Cliente destinatario

        Returns:
            True si se envió exitosamente, False si hubo error
        """
        try:

            # Construir variables desde la BD usando las variables configuradas
            dias_diferencia = None
            if cuota.fecha_vencimiento:
                dias_diferencia = self.calcular_dias_para_vencimiento(cuota.fecha_vencimiento)
            
            # Usar el servicio de variables para construir variables dinámicamente desde la BD
            variables = self.variables_service.construir_variables_desde_bd(
                cliente=cliente,
                prestamo=prestamo,
                cuota=cuota,
                dias_atraso=abs(dias_diferencia) if dias_diferencia and dias_diferencia < 0 else None,
            )

            # Reemplazar variables en el asunto y cuerpo usando el servicio
            asunto = self.variables_service.reemplazar_variables_en_texto(plantilla.asunto, variables)
            cuerpo = self.variables_service.reemplazar_variables_en_texto(plantilla.cuerpo, variables)

            # NOTA: La verificación de notificaciones existentes ya se hace en batch
            # en procesar_notificaciones_automaticas() para evitar queries N+1

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

    def enviar_notificacion(self, cuota: Cuota, plantilla: NotificacionPlantilla, cliente: Cliente) -> bool:
        """
        Enviar notificación al cliente (método legacy - mantener para compatibilidad)

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

            # Usar método optimizado
            return self.enviar_notificacion_optimizada(cuota, prestamo, plantilla, cliente)

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

    def _procesar_cuota_optimizada(
        self,
        cuota: Cuota,
        prestamo: Prestamo,
        cliente: Cliente,
        plantillas: Dict[str, NotificacionPlantilla],
        notificaciones_existentes: Dict[Tuple[int, str], bool],
        stats: Dict[str, int],
    ) -> bool:
        """
        Procesa una cuota individual con datos ya cargados (optimizado)

        Args:
            cuota: Cuota ya cargada
            prestamo: Prestamo ya cargado
            cliente: Cliente ya cargado
            plantillas: Diccionario de plantillas en cache
            notificaciones_existentes: Set de (cliente_id, tipo) ya procesadas hoy
            stats: Estadísticas a actualizar

        Returns:
            True si se procesó exitosamente
        """
        try:
            if not cuota.fecha_vencimiento:
                return False

            dias = self.calcular_dias_para_vencimiento(cuota.fecha_vencimiento)
            tipo_plantilla = self._determinar_tipo_plantilla(dias)

            if not tipo_plantilla:
                return False

            # Usar plantilla del cache
            plantilla = plantillas.get(tipo_plantilla)
            if not plantilla:
                stats["sin_plantilla"] += 1
                return False

            # Verificar si ya se procesó esta notificación hoy (usar cache)
            clave_notif = (cliente.id, tipo_plantilla)
            if notificaciones_existentes.get(clave_notif, False):
                return False  # Ya procesada, no hacer nada

            # Procesar notificación
            if self.enviar_notificacion_optimizada(cuota, prestamo, plantilla, cliente):
                stats["enviadas"] += 1
                notificaciones_existentes[clave_notif] = True
            else:
                stats["errores"] += 1

            return True

        except Exception as e:
            stats["errores"] += 1
            logger.error(f"Error procesando cuota {cuota.id}: {e}")
            return False

    def _procesar_cuota(self, cuota: Cuota, stats: Dict[str, int]) -> bool:
        """Procesa una cuota individual (método legacy - mantener para compatibilidad)"""
        try:
            # Obtener cliente a través del préstamo (Cuota -> Prestamo -> Cliente)
            prestamo = self.db.query(Prestamo).filter(Prestamo.id == cuota.prestamo_id).first()
            if not prestamo:
                logger.warning(f"Préstamo {cuota.prestamo_id} no encontrado para cuota {cuota.id}")
                return False

            # Obtener cliente por cédula o por cliente_id
            if prestamo.cliente_id:
                cliente = self.db.query(Cliente).filter(Cliente.id == prestamo.cliente_id).first()
            else:
                cliente = self.db.query(Cliente).filter(Cliente.cedula == prestamo.cedula).first()

            if not cliente:
                logger.warning(f"Cliente no encontrado para préstamo {prestamo.id} (cédula: {prestamo.cedula})")
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
        Procesar todas las notificaciones automáticas necesarias (OPTIMIZADO)

        Optimizaciones aplicadas:
        - JOINs para cargar cuotas, préstamos y clientes en una query
        - Cache de plantillas para evitar queries repetidas
        - Filtro por fechas relevantes (solo procesa cuotas que necesitan notificación hoy)
        - Verificación batch de notificaciones existentes
        - Procesamiento más eficiente

        Returns:
            Diccionario con estadísticas de envío
        """
        start_total = time.time()
        stats = {
            "procesadas": 0,
            "enviadas": 0,
            "errores": 0,
            "sin_plantilla": 0,
            "sin_email": 0,
        }

        try:
            # Cargar todas las plantillas en cache (una sola query)
            start_cache = time.time()
            plantillas = self._cargar_todas_plantillas()
            tiempo_cache = int((time.time() - start_cache) * 1000)
            logger.info(f"📚 Plantillas cargadas en cache: {tiempo_cache}ms")

            # Obtener cuotas con relaciones ya cargadas (JOIN optimizado)
            start_query = time.time()
            cuotas_con_relaciones = self.obtener_cuotas_pendientes_optimizado()
            tiempo_query = int((time.time() - start_query) * 1000)
            logger.info(f"📊 Cuotas obtenidas con JOINs: {len(cuotas_con_relaciones)} en {tiempo_query}ms")

            if not cuotas_con_relaciones:
                logger.info("No hay cuotas que necesiten notificación hoy")
                return stats

            # Verificar notificaciones existentes hoy en batch (una sola query)
            start_check = time.time()
            hoy_inicio = datetime.now(CARACAS_TZ).replace(hour=0, minute=0, second=0, microsecond=0)
            clientes_ids = [cliente.id for _, _, cliente in cuotas_con_relaciones]
            tipos_plantillas = set()
            for _, _, _ in cuotas_con_relaciones:
                # Los tipos se determinarán después, pero podemos pre-cargar todas las posibles
                for dias in DIAS_NOTIFICACION:
                    tipo = self._determinar_tipo_plantilla(dias)
                    if tipo:
                        tipos_plantillas.add(tipo)

            notificaciones_existentes_raw = (
                self.db.query(Notificacion.cliente_id, Notificacion.tipo)
                .filter(
                    Notificacion.cliente_id.in_(clientes_ids),
                    Notificacion.tipo.in_(tipos_plantillas),
                    Notificacion.enviada_en >= hoy_inicio,
                )
                .all()
            )

            # Crear diccionario de notificaciones existentes
            notificaciones_existentes = {(cliente_id, tipo): True for cliente_id, tipo in notificaciones_existentes_raw}
            tiempo_check = int((time.time() - start_check) * 1000)
            logger.info(f"✅ Verificadas notificaciones existentes: {tiempo_check}ms")

            # Procesar cada cuota (ya tiene préstamo y cliente cargados)
            start_proceso = time.time()
            for cuota, prestamo, cliente in cuotas_con_relaciones:
                if self._procesar_cuota_optimizada(cuota, prestamo, cliente, plantillas, notificaciones_existentes, stats):
                    stats["procesadas"] += 1
            tiempo_proceso = int((time.time() - start_proceso) * 1000)
            logger.info(f"⚙️ Procesamiento de cuotas: {tiempo_proceso}ms")

            tiempo_total = int((time.time() - start_total) * 1000)
            logger.info(
                f"⏱️ Procesamiento completado en {tiempo_total}ms: "
                f"{stats['procesadas']} procesadas, {stats['enviadas']} enviadas, "
                f"{stats['errores']} errores (cache: {tiempo_cache}ms, query: {tiempo_query}ms, "
                f"check: {tiempo_check}ms, proceso: {tiempo_proceso}ms)"
            )

            return stats

        except Exception as e:
            logger.error(f"Error en procesamiento automático: {e}", exc_info=True)
            stats["errores"] += 1
            return stats
