"""
Servicio para calcular notificaciones prejudiciales
Clientes con 3 o más cuotas atrasadas
"""

import logging
from datetime import date
from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class NotificacionesPrejudicialService:
    """Servicio para gestionar notificaciones prejudiciales"""

    def __init__(self, db: Session):
        self.db = db

    def calcular_notificaciones_prejudiciales(self) -> List[dict]:
        """
        Calcula clientes con 3 o más cuotas atrasadas (prejudiciales)

        Condiciones:
        - Préstamos con estado = 'APROBADO'
        - Clientes con 3 o más cuotas atrasadas
        - Cuotas con estado ATRASADO
        - Clientes activos (estado != 'INACTIVO')
        - Ordenado por fecha de vencimiento más antigua primero

        Returns:
            Lista de diccionarios con información de clientes y préstamos
        """
        hoy = date.today()

        try:
            logger.info("🔍 [NotificacionesPrejudicial] Iniciando cálculo de notificaciones prejudiciales...")

            # Query optimizada: clientes con 3+ cuotas atrasadas
            # Ordenado por fecha de vencimiento más antigua primero
            query_optimizada = text(
                """WITH cuotas_atrasadas AS (
                    SELECT 
                        p.id as prestamo_id,
                        p.cliente_id,
                        cl.nombres as nombre_cliente,
                        p.cedula,
                        COALESCE(p.modelo_vehiculo, p.producto, 'N/A') as modelo_vehiculo,
                        cl.email as correo,
                        cl.telefono,
                        c.fecha_vencimiento,
                        c.numero_cuota,
                        c.monto_cuota,
                        ROW_NUMBER() OVER (PARTITION BY p.cliente_id ORDER BY c.fecha_vencimiento ASC) as rn
                    FROM prestamos p
                    INNER JOIN cuotas c ON c.prestamo_id = p.id
                    INNER JOIN clientes cl ON cl.id = p.cliente_id
                    WHERE p.estado = 'APROBADO'
                      AND c.estado = 'ATRASADO'
                      AND c.fecha_vencimiento < :hoy
                      AND cl.estado != 'INACTIVO'
                ),
                clientes_prejudiciales AS (
                    SELECT cliente_id
                    FROM cuotas_atrasadas
                    GROUP BY cliente_id
                    HAVING COUNT(*) >= 3
                )
                SELECT
                    ca.prestamo_id,
                    ca.cliente_id,
                    ca.nombre_cliente,
                    ca.cedula,
                    ca.modelo_vehiculo,
                    ca.correo,
                    ca.telefono,
                    ca.fecha_vencimiento,
                    ca.numero_cuota,
                    ca.monto_cuota,
                    (SELECT COUNT(*) 
                     FROM cuotas c2 
                     WHERE c2.prestamo_id = ca.prestamo_id 
                       AND c2.estado = 'ATRASADO' 
                       AND c2.fecha_vencimiento < :hoy) as total_cuotas_atrasadas,
                    'PREJUDICIAL' as tipo_notificacion
                FROM cuotas_atrasadas ca
                INNER JOIN clientes_prejudiciales cp ON cp.cliente_id = ca.cliente_id
                ORDER BY ca.fecha_vencimiento ASC, ca.cliente_id, ca.numero_cuota"""
            )

            import time

            start_time = time.time()

            try:
                # Usar bindparams para asegurar que los parámetros se pasen correctamente
                query_bind = query_optimizada.bindparams(hoy=hoy)
                result = self.db.execute(query_bind)
                rows = result.fetchall()
                elapsed_time = time.time() - start_time
                logger.info(
                    f"📊 [NotificacionesPrejudicial] Query completada en {elapsed_time:.2f}s - Encontrados {len(rows)} registros"
                )

                if elapsed_time > 30:
                    logger.warning(f"⚠️ [NotificacionesPrejudicial] Query tardó {elapsed_time:.2f}s - considerar optimización")

            except Exception as query_error:
                elapsed_time = time.time() - start_time
                logger.error(
                    f"❌ [NotificacionesPrejudicial] Error ejecutando query después de {elapsed_time:.2f}s: {query_error}",
                    exc_info=True,
                )
                return []

            resultados = []

            # Obtener estados de notificaciones en batch
            cliente_ids = list(set(row[1] for row in rows))
            tipo_notificacion = "PREJUDICIAL"

            estados_notificaciones = {}
            if cliente_ids:
                try:
                    query_estados = text(
                        """
                        SELECT cliente_id, tipo::text, estado
                        FROM notificaciones
                        WHERE cliente_id = ANY(:cliente_ids)
                          AND tipo::text = :tipo
                        ORDER BY id DESC
                    """
                    )
                    result_estados = self.db.execute(
                        query_estados,
                        {
                            "cliente_ids": cliente_ids,
                            "tipo": tipo_notificacion,
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
                    logger.warning(f"⚠️ [NotificacionesPrejudicial] Error obteniendo estados: {e}")

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
                    fecha_vencimiento = row[7]
                    numero_cuota = row[8]
                    monto_cuota = row[9]
                    total_cuotas_atrasadas = row[10]
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
                            "fecha_vencimiento": fecha_vencimiento.isoformat() if fecha_vencimiento else "",
                            "numero_cuota": numero_cuota,
                            "monto_cuota": float(monto_cuota) if monto_cuota else 0.0,
                            "total_cuotas_atrasadas": int(total_cuotas_atrasadas) if total_cuotas_atrasadas else 0,
                            "estado": estado,
                        }
                    )
                except Exception as e:
                    logger.warning(f"⚠️ [NotificacionesPrejudicial] Error procesando fila: {e}")
                    continue

            logger.info(f"✅ [NotificacionesPrejudicial] Procesados {len(resultados)} registros exitosamente")
            return resultados

        except Exception as e:
            logger.error(f"❌ [NotificacionesPrejudicial] Error general: {e}", exc_info=True)
            return []

    def obtener_notificaciones_prejudiciales_cached(self) -> List[dict]:
        """
        Obtener notificaciones prejudiciales (actualmente sin cache, calcula en tiempo real)
        """
        return self.calcular_notificaciones_prejudiciales()
