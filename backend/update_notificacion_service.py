# -*- coding: utf-8 -*-
"""
Script para actualizar el servicio de notificación de LIQUIDADO
para incluir generación y envío de PDF del estado de cuenta.
"""

import os

nuevo_contenido = '''# -*- coding: utf-8 -*-
"""
Servicio de notificaciones automáticas para préstamos LIQUIDADO con PDF de estado de cuenta.
Se dispara cuando el scheduler actualiza estado a LIQUIDADO cada 9 PM.
Genera PDF de estado de cuenta y lo adjunta al correo de notificación.
"""

from datetime import date
from typing import Optional, List, Tuple
from app.core.database import SessionLocal
from app.services.estado_cuenta_pdf import generar_pdf_estado_cuenta
from app.core.email import send_email
from app.services.cuota_estado import estado_cuota_para_mostrar
from sqlalchemy import text
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)


class LiquidadoNotificacionService:
    """Crea notificaciones con PDF de estado de cuenta cuando préstamos se marcan como LIQUIDADO"""
    
    @staticmethod
    def crear_notificacion(prestamo_id: int, capital: float, suma_pagado: float) -> bool:
        """
        Crea y envía notificación cuando un préstamo se marca como LIQUIDADO.
        Adjunta PDF del estado de cuenta actual del cliente.
        La notificación aparecerá en la pestaña 'liquidados' del frontend.
        
        Args:
            prestamo_id: ID del préstamo
            capital: Monto total financiado
            suma_pagado: Total pagado
            
        Returns:
            bool: True si se creó exitosamente, False si hubo error
        """
        db = SessionLocal()
        try:
            # 1. Obtener datos del préstamo y cliente
            result = db.execute(text("""
                SELECT 
                    p.cliente_id,
                    c.email,
                    c.cedula,
                    p.referencia_interna,
                    c.nombres,
                    p.total_financiamiento,
                    p.id
                FROM prestamos p
                LEFT JOIN clientes c ON p.cliente_id = c.id
                WHERE p.id = :prestamo_id
            """), {'prestamo_id': prestamo_id}).fetchone()
            
            if not result:
                logger.warning(f'[LIQUIDADO_NOTIF] Prestamo {prestamo_id} no encontrado para notificacion')
                return False
            
            cliente_id, email, cedula, referencia, nombre_cliente, capital_bd, _ = result
            
            if not email:
                logger.warning(f'[LIQUIDADO_NOTIF] Cliente {cliente_id} sin email registrado')
                return False
            
            # 2. Generar PDF de estado de cuenta
            logger.info(f'[LIQUIDADO_NOTIF] Generando PDF para prestamo {prestamo_id}, cliente {cliente_id}')
            try:
                pdf_bytes = LiquidadoNotificacionService._generar_pdf_estado_cuenta(db, cliente_id)
                if not pdf_bytes:
                    logger.warning(f'[LIQUIDADO_NOTIF] No se pudo generar PDF para cliente {cliente_id}')
                    pdf_bytes = None
            except Exception as e:
                logger.error(f'[LIQUIDADO_NOTIF] Error generando PDF: {e}')
                pdf_bytes = None
            
            # 3. Preparar datos del correo
            asunto = f'Préstamo {referencia} - 100% Liquidado'
            cuerpo_texto = f"""Estimado(a) {nombre_cliente or 'Cliente'},

Su préstamo por {capital:,.2f} ha sido completamente pagado.

Total pagado: {suma_pagado:,.2f}

Su estado de cuenta actualizado se adjunta a este correo.

Muchas gracias por su confianza en RapiCredit.

Saludos cordiales,
Equipo RapiCredit"""
            
            # 4. Enviar correo con PDF adjunto (si se generó)
            adjuntos: Optional[List[Tuple[str, bytes]]] = None
            if pdf_bytes:
                nombre_pdf = f'estado_cuenta_{referencia.replace(" ", "_")[:50]}.pdf'
                adjuntos = [(nombre_pdf, pdf_bytes)]
                logger.info(f'[LIQUIDADO_NOTIF] Enviando correo con PDF adjunto a {email}')
            else:
                logger.info(f'[LIQUIDADO_NOTIF] Enviando correo sin PDF adjunto a {email}')
            
            try:
                exito, error_msg = send_email(
                    to_emails=[email],
                    subject=asunto,
                    body_text=cuerpo_texto,
                    attachments=adjuntos,
                    tipo_tab='liquidados'
                )
                
                if exito:
                    logger.info(f'[LIQUIDADO_NOTIF] Correo enviado exitosamente a {email}')
                else:
                    logger.warning(f'[LIQUIDADO_NOTIF] Error enviando correo a {email}: {error_msg}')
            except Exception as e:
                logger.error(f'[LIQUIDADO_NOTIF] Excepción enviando correo: {e}')
                exito = False
            
            # 5. Insertar en tabla envio_notificacion para auditoria
            db.execute(text("""
                INSERT INTO envio_notificacion 
                    (prestamo_id, cliente_id, cedula, email, tipo, asunto, cuerpo, exito, fecha_envio)
                VALUES 
                    (:prestamo_id, :cliente_id, :cedula, :email, :tipo, :asunto, :cuerpo, :exito, NOW())
            """), {
                'prestamo_id': prestamo_id,
                'cliente_id': cliente_id,
                'cedula': cedula or '',
                'email': email or '',
                'tipo': 'liquidado',
                'asunto': asunto,
                'cuerpo': cuerpo_texto[:2000]
            })
            
            db.commit()
            logger.info(f'[LIQUIDADO_NOTIF] Notificacion auditada: prestamo_id={prestamo_id}, cliente={cliente_id}')
            return exito
            
        except Exception as e:
            logger.error(f'[LIQUIDADO_NOTIF] Error: prestamo_id={prestamo_id}: {e}', exc_info=True)
            try:
                db.rollback()
            except:
                pass
            return False
        finally:
            try:
                db.close()
            except:
                pass
    
    @staticmethod
    def _generar_pdf_estado_cuenta(db: Session, cliente_id: int) -> Optional[bytes]:
        """
        Genera PDF de estado de cuenta para un cliente.
        
        Args:
            db: Sesion de base de datos
            cliente_id: ID del cliente
            
        Returns:
            bytes: Contenido del PDF o None si hay error
        """
        try:
            # Obtener datos del cliente
            result_cliente = db.execute(text("""
                SELECT cedula, nombres, email FROM clientes WHERE id = :cliente_id
            """), {'cliente_id': cliente_id}).fetchone()
            
            if not result_cliente:
                return None
            
            cedula, nombre, email = result_cliente
            
            # Obtener préstamos del cliente
            result_prestamos = db.execute(text("""
                SELECT id, producto, total_financiamiento, estado 
                FROM prestamos 
                WHERE cliente_id = :cliente_id
                ORDER BY id DESC
            """), {'cliente_id': cliente_id}).fetchall()
            
            prestamos_data = []
            for row in result_prestamos:
                prestamos_data.append({
                    'id': row[0],
                    'producto': row[1] or 'Préstamo',
                    'total_financiamiento': float(row[2] or 0),
                    'estado': row[3],
                })
            
            # Obtener cuotas pendientes del cliente
            result_cuotas = db.execute(text("""
                SELECT c.prestamo_id, c.numero_cuota, c.fecha_vencimiento, c.monto_cuota, c.estado
                FROM cuotas c
                INNER JOIN prestamos p ON c.prestamo_id = p.id
                WHERE p.cliente_id = :cliente_id AND c.estado = 'PENDIENTE'
                ORDER BY c.prestamo_id, c.numero_cuota
            """), {'cliente_id': cliente_id}).fetchall()
            
            cuotas_data = []
            total_pendiente = 0.0
            for row in result_cuotas:
                estado_str = estado_cuota_para_mostrar(row[4])
                cuotas_data.append({
                    'prestamo_id': row[0],
                    'numero_cuota': row[1],
                    'fecha_vencimiento': row[2].isoformat() if row[2] else '',
                    'monto': float(row[3] or 0),
                    'estado': estado_str,
                })
                total_pendiente += float(row[3] or 0)
            
            # Generar PDF
            pdf_bytes = generar_pdf_estado_cuenta(
                cedula=cedula or '',
                nombre=nombre or '',
                prestamos=prestamos_data,
                cuotas_pendientes=cuotas_data,
                total_pendiente=total_pendiente,
                fecha_corte=date.today(),
            )
            
            return pdf_bytes
            
        except Exception as e:
            logger.error(f'[LIQUIDADO_NOTIF] Error en _generar_pdf_estado_cuenta: {e}', exc_info=True)
            return None


# Instancia global del servicio
notificacion_service = LiquidadoNotificacionService()
'''

archivo_destino = r"c:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos\backend\app\services\liquidado_notificacion_service.py"

try:
    with open(archivo_destino, 'w', encoding='utf-8') as f:
        f.write(nuevo_contenido)
    print(f"✓ Archivo actualizado exitosamente: {archivo_destino}")
except Exception as e:
    print(f"✗ Error actualizando archivo: {e}")
