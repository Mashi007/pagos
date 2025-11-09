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
        - Préstamos con estado = 'APROBADO'
        - Cuotas que vencen en 5, 3 o 1 día
        - Cuotas con estado PENDIENTE o ADELANTADO
        - Clientes activos (estado != 'INACTIVO')
        - NO se discrimina por cuotas atrasadas (todos los préstamos aprobados)

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

            # Query optimizada: NO filtra por cuotas atrasadas, solo por días y estado
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
                        WHEN c.fecha_vencimiento = :fecha_5_dias THEN 5
                        WHEN c.fecha_vencimiento = :fecha_3_dias THEN 3
                        WHEN c.fecha_vencimiento = :fecha_1_dia THEN 1
                    END as dias_antes_vencimiento,
                    c.fecha_vencimiento,
                    c.numero_cuota,
                    c.monto_cuota,
                    CASE
                        WHEN c.fecha_vencimiento = :fecha_5_dias THEN 'PAGO_5_DIAS_ANTES'
                        WHEN c.fecha_vencimiento = :fecha_3_dias THEN 'PAGO_3_DIAS_ANTES'
                        WHEN c.fecha_vencimiento = :fecha_1_dia THEN 'PAGO_1_DIA_ANTES'
                    END as tipo_notificacion
                FROM prestamos p
                INNER JOIN cuotas c ON c.prestamo_id = p.id
                INNER JOIN clientes cl ON cl.id = p.cliente_id
                WHERE p.estado = 'APROBADO'
                  AND (c.fecha_vencimiento = :fecha_5_dias OR c.fecha_vencimiento = :fecha_3_dias OR c.fecha_vencimiento = :fecha_1_dia)
                  AND c.estado IN ('PENDIENTE', 'ADELANTADO')
                  AND cl.estado != 'INACTIVO'
                ORDER BY dias_antes_vencimiento, c.fecha_vencimiento
            """
            )

            import time
            start_time = time.time()
            
            try:
                # Ejecutar query con timeout implícito (el timeout de la conexión BD)
                result = self.db.execute(
                    query_optimizada,
                    {
                        "fecha_5_dias": fecha_5_dias,
                        "fecha_3_dias": fecha_3_dias,
                        "fecha_1_dia": fecha_1_dia,
                    },
                )
                rows = result.fetchall()
                elapsed_time = time.time() - start_time
                logger.info(f"📊 [NotificacionesPrevias] Query optimizada completada en {elapsed_time:.2f}s - Encontrados {len(rows)} registros de cuotas próximas")
                
                # Si la query tarda más de 30 segundos, registrar advertencia
                if elapsed_time > 30:
                    logger.warning(f"⚠️ [NotificacionesPrevias] Query tardó {elapsed_time:.2f}s - considerar optimización adicional o índices")
                    
            except Exception as query_error:
                elapsed_time = time.time() - start_time
                logger.error(f"❌ [NotificacionesPrevias] Error ejecutando query optimizada después de {elapsed_time:.2f}s: {query_error}", exc_info=True)
                # Retornar lista vacía en lugar de fallar completamente
                logger.warning("⚠️ [NotificacionesPrevias] Retornando lista vacía debido a error en query")
                return []

            resultados = []

            # Obtener estados de notificaciones en batch para todos los clientes
            cliente_ids = list(set(row[1] for row in rows))  # cliente_id está en índice 1
            tipos_notificacion = list(set(row[11] for row in rows if row[11]))  # tipo_notificacion está en índice 11

            # Query para obtener estados de notificaciones en batch
            estados_notificaciones = {}
            if cliente_ids and tipos_notificacion:
                try:
                    query_estados = text(
                        """
                        SELECT cliente_id, tipo, estado
                        FROM notificaciones
                        WHERE cliente_id = ANY(:cliente_ids)
                          AND tipo = ANY(:tipos)
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

                    # Crear diccionario: (cliente_id, tipo) -> estado
                    for estado_row in estados_rows:
                        cliente_id_estado = estado_row[0]
                        tipo_estado = estado_row[1]
                        estado_valor = estado_row[2]
                        # Solo guardar el más reciente (ya está ordenado por id DESC)
                        if (cliente_id_estado, tipo_estado) not in estados_notificaciones:
                            estados_notificaciones[(cliente_id_estado, tipo_estado)] = estado_valor
                except Exception as e:
                    logger.warning(f"⚠️ [NotificacionesPrevias] Error obteniendo estados de notificaciones: {e}")

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
                    dias_antes = row[7]
                    fecha_vencimiento = row[8]
                    numero_cuota = row[9]
                    monto_cuota = row[10]
                    tipo_notificacion = row[11]

                    # Obtener estado de notificación
                    estado_notificacion = "PENDIENTE"  # Por defecto
                    if tipo_notificacion and (cliente_id, tipo_notificacion) in estados_notificaciones:
                        estado_notificacion = estados_notificaciones[(cliente_id, tipo_notificacion)]

                    resultado = {
                        "prestamo_id": prestamo_id,
                        "cliente_id": cliente_id,
                        "nombre": nombre_cliente or "",
                        "cedula": cedula or "",
                        "modelo_vehiculo": modelo_vehiculo or "N/A",
                        "correo": correo or "",
                        "telefono": telefono or "",
                        "dias_antes_vencimiento": dias_antes,
                        "fecha_vencimiento": fecha_vencimiento.isoformat() if fecha_vencimiento else "",
                        "numero_cuota": numero_cuota,
                        "monto_cuota": float(monto_cuota) if monto_cuota else 0.0,
                        "estado": estado_notificacion,
                    }
                    resultados.append(resultado)
                except Exception as e:
                    logger.warning(f"⚠️ [NotificacionesPrevias] Error procesando fila: {e}")
                    continue

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
