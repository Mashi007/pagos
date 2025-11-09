"""
Servicio para calcular notificaciones del día de pago
Clientes con cuotas que vencen HOY
"""

import logging
from datetime import date
from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class NotificacionesDiaPagoService:
    """Servicio para gestionar notificaciones del día de pago"""

    def __init__(self, db: Session):
        self.db = db

    def calcular_notificaciones_dia_pago(self) -> List[dict]:
        """
        Calcula clientes con cuotas que vencen HOY

        Condiciones:
        - Préstamos con estado = 'APROBADO'
        - Cuotas con fecha_vencimiento = HOY
        - Cuotas con estado PENDIENTE o ATRASADO
        - Clientes activos (estado != 'INACTIVO')
        - Ordenado alfabéticamente por nombre del cliente

        Returns:
            Lista de diccionarios con información de clientes y préstamos
        """
        hoy = date.today()

        try:
            logger.info("🔍 [NotificacionesDiaPago] Iniciando cálculo de notificaciones del día de pago...")

            # Query optimizada: cuotas que vencen hoy, ordenadas alfabéticamente
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
                    c.fecha_vencimiento,
                    c.numero_cuota,
                    c.monto_cuota,
                    'PAGO_DIA_0' as tipo_notificacion
                FROM prestamos p
                INNER JOIN cuotas c ON c.prestamo_id = p.id
                INNER JOIN clientes cl ON cl.id = p.cliente_id
                WHERE p.estado = 'APROBADO'
                  AND c.fecha_vencimiento = :hoy
                  AND c.estado IN ('PENDIENTE', 'ATRASADO')
                  AND cl.estado != 'INACTIVO'
                ORDER BY cl.nombres ASC, c.numero_cuota ASC
            """
            )

            import time

            start_time = time.time()

            try:
                result = self.db.execute(
                    query_optimizada,
                    {
                        "hoy": hoy,
                    },
                )
                rows = result.fetchall()
                elapsed_time = time.time() - start_time
                logger.info(
                    f"📊 [NotificacionesDiaPago] Query completada en {elapsed_time:.2f}s - Encontrados {len(rows)} registros"
                )

                if elapsed_time > 30:
                    logger.warning(
                        f"⚠️ [NotificacionesDiaPago] Query tardó {elapsed_time:.2f}s - considerar optimización"
                    )

            except Exception as query_error:
                elapsed_time = time.time() - start_time
                logger.error(
                    f"❌ [NotificacionesDiaPago] Error ejecutando query después de {elapsed_time:.2f}s: {query_error}",
                    exc_info=True,
                )
                return []

            resultados = []

            # Obtener estados de notificaciones en batch
            cliente_ids = list(set(row[1] for row in rows))
            tipo_notificacion = 'PAGO_DIA_0'

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
                    logger.warning(f"⚠️ [NotificacionesDiaPago] Error obteniendo estados: {e}")

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
                    tipo_notificacion = row[10]

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
                            "fecha_vencimiento": fecha_vencimiento.isoformat() if fecha_vencimiento else None,
                            "numero_cuota": numero_cuota,
                            "monto_cuota": float(monto_cuota) if monto_cuota else 0.0,
                            "estado": estado,
                        }
                    )
                except Exception as e:
                    logger.warning(f"⚠️ [NotificacionesDiaPago] Error procesando fila: {e}")
                    continue

            logger.info(f"✅ [NotificacionesDiaPago] Procesados {len(resultados)} registros exitosamente")
            return resultados

        except Exception as e:
            logger.error(f"❌ [NotificacionesDiaPago] Error general: {e}", exc_info=True)
            return []

    def obtener_notificaciones_dia_pago_cached(self) -> List[dict]:
        """
        Obtener notificaciones del día de pago (actualmente sin cache, calcula en tiempo real)
        """
        return self.calcular_notificaciones_dia_pago()

