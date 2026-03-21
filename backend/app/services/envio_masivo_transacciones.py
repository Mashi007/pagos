# -*- coding: utf-8 -*-
"""
Servicio para envío masivo de notificaciones con transacciones ACID.
Garantiza consistencia de datos: todo se guarda o nada.
"""

from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class EnvioMasivoConTransacciones:
    """
    Gestor de envío masivo con transacciones ACID.
    Asegura que si algo falla, la BD no queda en estado inconsistente.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.estadisticas = {
            'total': 0,
            'enviados': 0,
            'fallidos': 0,
            'saltados': 0,
            'errores_detalles': []
        }
    
    def enviar_lote_con_transaccion(
        self,
        clientes: List,
        funcion_envio,
        tipo_notificacion: str = 'generico'
    ) -> Dict:
        """
        Envía notificaciones a un lote de clientes dentro de una transacción.
        
        Si todo funciona: COMMIT
        Si algo falla: ROLLBACK (se deshacen los cambios)
        
        Args:
            clientes: Lista de clientes a los que enviar
            funcion_envio: Función que envía la notificación
                          Debe recibir: (cliente, db) → bool
            tipo_notificacion: Tipo de notificación (para logging)
        
        Returns:
            Dict con estadísticas del envío
        """
        
        self.estadisticas = {
            'total': len(clientes),
            'enviados': 0,
            'fallidos': 0,
            'saltados': 0,
            'errores_detalles': [],
            'tipo': tipo_notificacion,
            'timestamp': datetime.now().isoformat(),
            'estado': 'INICIADO'
        }
        
        try:
            # PASO 1: Iniciar transacción explícita
            logger.info(f"Iniciando transacción para {len(clientes)} clientes ({tipo_notificacion})")
            self.db.begin()
            
            # PASO 2: Procesar cada cliente
            for i, cliente in enumerate(clientes, 1):
                try:
                    logger.debug(f"[{i}/{len(clientes)}] Procesando cliente {cliente.id}")
                    
                    # Llamar función de envío
                    resultado = funcion_envio(cliente, self.db)
                    
                    if resultado:
                        self.estadisticas['enviados'] += 1
                        logger.debug(f"  ✓ Enviado a {cliente.id}")
                    else:
                        self.estadisticas['fallidos'] += 1
                        logger.warning(f"  ✗ Falló para {cliente.id}")
                        self.estadisticas['errores_detalles'].append({
                            'cliente_id': cliente.id,
                            'error': 'Función de envío retornó False'
                        })
                
                except Exception as e:
                    # Error individual - registrar pero continuar
                    self.estadisticas['fallidos'] += 1
                    error_msg = str(e)
                    logger.error(f"  ✗ Error para cliente {cliente.id}: {error_msg}")
                    self.estadisticas['errores_detalles'].append({
                        'cliente_id': cliente.id,
                        'error': error_msg
                    })
                    # Continuar con el siguiente cliente
                    continue
            
            # PASO 3: COMMIT si llegamos aquí sin excepciones críticas
            logger.info(f"Comitiendo transacción: {self.estadisticas['enviados']} exitosos, "
                       f"{self.estadisticas['fallidos']} fallidos")
            self.db.commit()
            self.estadisticas['estado'] = 'COMPLETADO'
            
            logger.info(f"✓ Transacción completada exitosamente")
            return self.estadisticas
        
        except IntegrityError as e:
            # Error de integridad en BD - ROLLBACK TODO
            logger.error(f"Error de integridad en BD: {e}")
            self.db.rollback()
            
            self.estadisticas['estado'] = 'FALLÓ - ROLLBACK'
            self.estadisticas['error_critico'] = f"Error de integridad: {str(e)}"
            
            raise Exception(
                f"Error de integridad en transacción: {str(e)}. "
                f"Todos los cambios fueron revertidos (ROLLBACK)."
            )
        
        except Exception as e:
            # Error inesperado - ROLLBACK TODO
            logger.error(f"Error inesperado en transacción: {e}", exc_info=True)
            self.db.rollback()
            
            self.estadisticas['estado'] = 'FALLÓ - ROLLBACK'
            self.estadisticas['error_critico'] = str(e)
            
            raise Exception(
                f"Error durante envío masivo: {str(e)}. "
                f"Todos los cambios fueron revertidos (ROLLBACK)."
            )
        
        finally:
            # Cleanup
            pass
    
    def obtener_estadisticas(self) -> Dict:
        """Retorna estadísticas del último envío."""
        
        stats = self.estadisticas.copy()
        
        # Agregar porcentajes
        if stats['total'] > 0:
            stats['porcentaje_exito'] = round(
                (stats['enviados'] / stats['total']) * 100, 
                2
            )
            stats['porcentaje_fallo'] = round(
                (stats['fallidos'] / stats['total']) * 100,
                2
            )
        
        return stats


def crear_envio_masivo_con_transaccion(
    db: Session,
    clientes: List,
    enviar_func,
    tipo: str = 'generico'
) -> Dict:
    """
    Helper function para hacer envío masivo más simple.
    
    Uso:
    
    def enviar_a_cliente(cliente, db):
        # Enviar email, SMS, etc
        try:
            send_email(cliente.email, ...)
            # Registrar en BD
            registro = EnvioNotificacion(...)
            db.add(registro)
            return True
        except:
            return False
    
    resultado = crear_envio_masivo_con_transaccion(
        db=db,
        clientes=clientes_pendientes,
        enviar_func=enviar_a_cliente,
        tipo='notificacion_5_dias_antes'
    )
    
    print(f"Enviados: {resultado['enviados']}/{resultado['total']}")
    if resultado['estado'] == 'FALLÓ - ROLLBACK':
        print(f"Alerta: {resultado['error_critico']}")
    """
    
    gestor = EnvioMasivoConTransacciones(db)
    return gestor.enviar_lote_con_transaccion(
        clientes=clientes,
        funcion_envio=enviar_func,
        tipo_notificacion=tipo
    )


# Ejemplo completo de uso:
#
# from app.models.envio_notificacion import EnvioNotificacion
# from app.services.email_service import send_email
# from sqlalchemy.orm import Session
#
# @router.post("/enviar-notificaciones-masivo-seguro")
# def enviar_notificaciones_masivo(db: Session = Depends(get_db)):
#     """Envío masivo de notificaciones con garantías ACID"""
#     
#     clientes = db.query(Cliente).filter(
#         Cliente.fecha_proximo_recordatorio <= datetime.now()
#     ).all()
#     
#     def enviar_a_cliente(cliente, db_session):
#         try:
#             # Enviar email
#             send_email(
#                 to=cliente.email,
#                 subject="Recordatorio de pago",
#                 body="Tu cuota vence en 5 días"
#             )
#             
#             # Registrar envío en BD (dentro de la transacción)
#             registro = EnvioNotificacion(
#                 cliente_id=cliente.id,
#                 email=cliente.email,
#                 exito=True,
#                 tipo_tab='dias_5'
#             )
#             db_session.add(registro)
#             
#             return True
#         
#         except Exception as e:
#             # Registrar fallo
#             registro = EnvioNotificacion(
#                 cliente_id=cliente.id,
#                 email=cliente.email,
#                 exito=False,
#                 error_mensaje=str(e),
#                 tipo_tab='dias_5'
#             )
#             db_session.add(registro)
#             
#             return False
#     
#     try:
#         resultado = crear_envio_masivo_con_transaccion(
#             db=db,
#             clientes=clientes,
#             enviar_func=enviar_a_cliente,
#             tipo='recordatorio_5_dias'
#         )
#         
#         return {
#             "estado": resultado['estado'],
#             "total": resultado['total'],
#             "enviados": resultado['enviados'],
#             "fallidos": resultado['fallidos'],
#             "porcentaje_exito": resultado.get('porcentaje_exito'),
#         }
#     
#     except Exception as e:
#         logger.error(f"Error en envío masivo: {e}")
#         return {
#             "estado": "ERROR",
#             "mensaje": str(e),
#             "recomendacion": "Contacta a administración"
#         }
