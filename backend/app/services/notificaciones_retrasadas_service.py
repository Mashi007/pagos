"""
Servicio para calcular notificaciones de pagos retrasados
Clientes con cuotas atrasadas (1, 3, 5 días atrasado)
"""

import logging
from datetime import date, timedelta
from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class NotificacionesRetrasadasService:
    """Servicio para gestionar notificaciones de pagos retrasados"""

    def __init__(self, db: Session):
        self.db = db

    def calcular_notificaciones_retrasadas(self) -> List[dict]:
        """
        Calcula clientes con cuotas atrasadas (1, 3, 5 días atrasado)

        Condiciones:
        - Préstamos con estado = 'APROBADO'
        - Cuotas que vencieron hace 1, 3 o 5 días
        - Cuotas con estado ATRASADO o PENDIENTE (cuando ya pasó la fecha)
        - Clientes activos (estado != 'INACTIVO')

        Returns:
            Lista de diccionarios con información de clientes y préstamos
        """
        hoy = date.today()

        # Fechas objetivo: 1, 3 y 5 días atrasado (vencieron hace X días)
        fecha_1_dia_atrasado = hoy - timedelta(days=1)
        fecha_3_dias_atrasado = hoy - timedelta(days=3)
        fecha_5_dias_atrasado = hoy - timedelta(days=5)

        try:
            logger.info("🔍 [NotificacionesRetrasadas] Iniciando cálculo de notificaciones retrasadas...")

            # Query optimizada para cuotas atrasadas
            query_optimizada = text(
                """
                SELECT
                    p.id as prestamo_id,
                    p.cliente_id,
                    cl.nombres as nombre_cliente,
                    p.cedula,
                    COALESCE(p.modelo_vehiculo, p.producto, 'N/A') as modelo_vehiculo,
                    cl.email as correo,
                    cl.telefono,
                    CASE
                        WHEN c.fecha_vencimiento = :fecha_1_dia_atrasado THEN 1
                        WHEN c.fecha_vencimiento = :fecha_3_dias_atrasado THEN 3
                        WHEN c.fecha_vencimiento = :fecha_5_dias_atrasado THEN 5
                    END as dias_atrasado,
                    c.fecha_vencimiento,
                    c.numero_cuota,
                    c.monto_cuota,
                    CASE
                        WHEN c.fecha_vencimiento = :fecha_1_dia_atrasado THEN 'PAGO_1_DIA_ATRASADO'
                        WHEN c.fecha_vencimiento = :fecha_3_dias_atrasado THEN 'PAGO_3_DIAS_ATRASADO'
                        WHEN c.fecha_vencimiento = :fecha_5_dias_atrasado THEN 'PAGO_5_DIAS_ATRASADO'
                    END as tipo_notificacion
                FROM prestamos p
                INNER JOIN cuotas c ON c.prestamo_id = p.id
                INNER JOIN clientes cl ON cl.id = p.cliente_id
                WHERE p.estado = 'APROBADO'
                  AND (c.fecha_vencimiento = :fecha_1_dia_atrasado
                       OR c.fecha_vencimiento = :fecha_3_dias_atrasado
                       OR c.fecha_vencimiento = :fecha_5_dias_atrasado)
                  AND c.estado IN ('ATRASADO', 'PENDIENTE')
                  AND cl.estado != 'INACTIVO'
                  AND c.fecha_vencimiento < :hoy
                ORDER BY dias_atrasado, c.fecha_vencimiento
            """
            )

            import time

            start_time = time.time()

            try:
                result = self.db.execute(
                    query_optimizada,
                    {
                        "fecha_1_dia_atrasado": fecha_1_dia_atrasado,
                        "fecha_3_dias_atrasado": fecha_3_dias_atrasado,
                        "fecha_5_dias_atrasado": fecha_5_dias_atrasado,
                        "hoy": hoy,
                    },
                )
                rows = result.fetchall()
                elapsed_time = time.time() - start_time
                logger.info(
                    f"📊 [NotificacionesRetrasadas] Query completada en {elapsed_time:.2f}s - Encontrados {len(rows)} registros"
                )

                if elapsed_time > 30:
                    logger.warning(f"⚠️ [NotificacionesRetrasadas] Query tardó {elapsed_time:.2f}s - considerar optimización")

            except Exception as query_error:
                elapsed_time = time.time() - start_time
                logger.error(
                    f"❌ [NotificacionesRetrasadas] Error ejecutando query después de {elapsed_time:.2f}s: {query_error}",
                    exc_info=True,
                )
                return []

            resultados = []

            # Obtener estados de notificaciones en batch
            cliente_ids = list(set(row[1] for row in rows))
            tipos_notificacion = list(set(row[11] for row in rows if row[11]))

            estados_notificaciones = {}
            if cliente_ids and tipos_notificacion:
                try:
                    query_estados = text(
                        """
                        SELECT cliente_id, tipo::text, estado
                        FROM notificaciones
                        WHERE cliente_id = ANY(:cliente_ids)
                          AND tipo::text = ANY(:tipos)
                        ORDER BY id DESC
                    """
                    )
                    result_estados = self.db.execute(
                        query_estados,
                        {
                            "cliente_ids": cliente_ids,
                            "tipos": tipos_notificacion,
                        },
                    )
                    estados_rows = result_estados.fetchall()

                    for estado_row in estados_rows:
                        cliente_id_estado = estado_row[0]
                        tipo_estado = estado_row[1]
                        estado_valor = estado_row[2]
                        if (cliente_id_estado, tipo_estado) not in estados_notificaciones:
                            estados_notificaciones[(cliente_id_estado, tipo_estado)] = estado_valor
                except Exception as e:
                    logger.warning(f"⚠️ [NotificacionesRetrasadas] Error obteniendo estados: {e}")

            # Procesar resultados
            for row in rows:
                try:
                    prestamo_id = row[0]
                    cliente_id = row[1]
                    nombre_cliente = row[2]
                    cedula = row[3]
                    modelo_vehiculo = row[4]
                    correo = row[5]
                    telefono = row[6]
                    dias_atrasado = row[7]
                    fecha_vencimiento = row[8]
                    numero_cuota = row[9]
                    monto_cuota = row[10]
                    tipo_notificacion = row[11]

                    # Obtener estado de notificación
                    estado = estados_notificaciones.get((cliente_id, tipo_notificacion), "PENDIENTE")

                    resultados.append(
                        {
                            "prestamo_id": prestamo_id,
                            "cliente_id": cliente_id,
                            "nombre": nombre_cliente,
                            "cedula": cedula,
                            "modelo_vehiculo": modelo_vehiculo,
                            "correo": correo or "",
                            "telefono": telefono or "",
                            "dias_atrasado": dias_atrasado,
                            "fecha_vencimiento": fecha_vencimiento.isoformat() if fecha_vencimiento else None,
                            "numero_cuota": numero_cuota,
                            "monto_cuota": float(monto_cuota) if monto_cuota else 0.0,
                            "estado": estado,
                        }
                    )
                except Exception as e:
                    logger.warning(f"⚠️ [NotificacionesRetrasadas] Error procesando fila: {e}")
                    continue

            logger.info(f"✅ [NotificacionesRetrasadas] Procesados {len(resultados)} registros exitosamente")
            return resultados

        except Exception as e:
            logger.error(f"❌ [NotificacionesRetrasadas] Error general: {e}", exc_info=True)
            return []

    def obtener_notificaciones_retrasadas_cached(self) -> List[dict]:
        """
        Obtener notificaciones retrasadas (actualmente sin cache, calcula en tiempo real)
        """
        return self.calcular_notificaciones_retrasadas()
