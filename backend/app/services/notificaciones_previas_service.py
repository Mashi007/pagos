"""
Servicio para calcular notificaciones previas
Clientes con cuotas próximas a vencer (5, 3, 1 días antes)
Solo clientes SIN cuotas atrasadas
"""

import logging
from datetime import date, timedelta
from typing import List, Optional

from sqlalchemy import and_, func, or_, text
from sqlalchemy.orm import Session

from app.models.amortizacion import Cuota
from app.models.cliente import Cliente
from app.models.notificacion import Notificacion

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
            # Verificar conexión a BD
            logger.info("🔍 [NotificacionesPrevias] Iniciando cálculo de notificaciones previas...")
            
            # Obtener solo las columnas necesarias de préstamos aprobados usando SQL directo
            # Esto evita que SQLAlchemy intente acceder a columnas que no existen en BD
            query_sql = text("""
                SELECT id, cliente_id, cedula, modelo_vehiculo, producto
                FROM prestamos
                WHERE estado = :estado
            """)
            
            result = self.db.execute(query_sql, {"estado": "APROBADO"})
            prestamos_data = result.fetchall()
            logger.info(f"📊 [NotificacionesPrevias] Encontrados {len(prestamos_data)} préstamos aprobados")

            resultados = []

            for prestamo_row in prestamos_data:
                # Acceder a las columnas por índice (0: id, 1: cliente_id, 2: cedula, 3: modelo_vehiculo, 4: producto)
                # Esto es necesario porque usamos SQL directo en lugar del ORM
                prestamo_id = prestamo_row[0]
                cliente_id = prestamo_row[1]
                cedula = prestamo_row[2]
                modelo_vehiculo = prestamo_row[3]
                producto = prestamo_row[4]
                
                # Verificar que NO tenga cuotas atrasadas
                # Cuotas atrasadas: vencidas y no pagadas (estado != "PAGADO")
                cuotas_atrasadas = (
                    self.db.query(Cuota)
                    .filter(
                        and_(
                            Cuota.prestamo_id == prestamo_id,
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
                            Cuota.prestamo_id == prestamo_id,
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

                    # Determinar tipo de notificación según días
                    tipo_notificacion = None
                    if dias_antes == 5:
                        tipo_notificacion = "PAGO_5_DIAS_ANTES"
                    elif dias_antes == 3:
                        tipo_notificacion = "PAGO_3_DIAS_ANTES"
                    elif dias_antes == 1:
                        tipo_notificacion = "PAGO_1_DIA_ANTES"

                    # Obtener datos del cliente usando SQL directo
                    query_cliente = text("""
                        SELECT id, nombres, email, telefono
                        FROM clientes
                        WHERE id = :cliente_id
                    """)
                    
                    result_cliente = self.db.execute(query_cliente, {"cliente_id": cliente_id})
                    cliente_row = result_cliente.fetchone()

                    if cliente_row:
                        # Acceder a las columnas por índice (0: id, 1: nombres, 2: email, 3: telefono)
                        cliente_id_val = cliente_row[0]
                        cliente_nombres = cliente_row[1]
                        cliente_email = cliente_row[2]
                        cliente_telefono = cliente_row[3]
                        # Buscar notificación relacionada si existe
                        estado_notificacion = "PENDIENTE"  # Por defecto pendiente (aún no enviada)
                        notificacion_existente = None

                        if tipo_notificacion:
                            # Buscar la notificación más reciente de este tipo para este cliente
                            # Ordenar por ID descendente (más reciente primero) ya que created_at puede no existir
                            try:
                                query_notif = text("""
                                    SELECT id, estado
                                    FROM notificaciones
                                    WHERE cliente_id = :cliente_id
                                      AND tipo = :tipo
                                    ORDER BY id DESC
                                    LIMIT 1
                                """)
                                
                                result_notif = self.db.execute(
                                    query_notif, 
                                    {"cliente_id": cliente_id_val, "tipo": tipo_notificacion}
                                )
                                notif_row = result_notif.fetchone()
                                
                                if notif_row:
                                    estado_notificacion = notif_row[1]  # estado está en índice 1
                                    logger.debug(
                                        f"📧 [NotificacionesPrevias] Cliente {cliente_id_val} tiene notificación {tipo_notificacion} "
                                        f"con estado {estado_notificacion}"
                                    )
                            except Exception as e:
                                logger.warning(
                                    f"⚠️ [NotificacionesPrevias] Error buscando notificación para cliente {cliente_id_val}: {e}"
                                )
                                # Continuar con estado PENDIENTE por defecto

                        resultado = {
                            "prestamo_id": prestamo_id,
                            "cliente_id": cliente_id_val,
                            "nombre": cliente_nombres,  # nombres ya incluye nombres + apellidos
                            "cedula": cedula,
                            "modelo_vehiculo": modelo_vehiculo or producto or "N/A",
                            "correo": cliente_email,
                            "telefono": cliente_telefono,
                            "dias_antes_vencimiento": dias_antes,
                            "fecha_vencimiento": cuota_proxima.fecha_vencimiento.isoformat(),
                            "numero_cuota": cuota_proxima.numero_cuota,
                            "monto_cuota": float(cuota_proxima.monto_cuota),
                            "estado": estado_notificacion,  # ENVIADA, PENDIENTE, FALLIDA
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
