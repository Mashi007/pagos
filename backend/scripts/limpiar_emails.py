#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para limpiar y validar emails en la base de datos.
Marca emails inválidos y documenta problemas encontrados.
"""

import sys
import logging
from datetime import datetime
from typing import List, Dict

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Importar desde app
sys.path.insert(0, '/path/to/backend')  # Ajustar path según necesidad

from app.core.database import SessionLocal
from app.models.cliente import Cliente
from app.utils.validators import es_email_valido


def limpiar_emails_bd():
    """
    Limpia y valida todos los emails en la BD.
    """
    
    db = SessionLocal()
    
    try:
        logger.info("=" * 70)
        logger.info("INICIANDO LIMPIEZA Y VALIDACIÓN DE EMAILS")
        logger.info("=" * 70)
        
        # Obtener todos los clientes
        clientes = db.query(Cliente).all()
        logger.info(f"Total de clientes en BD: {len(clientes)}")
        
        estadisticas = {
            'total': len(clientes),
            'validos': 0,
            'inválidos': 0,
            'vacios': 0,
            'corregidos': 0,
            'detalles_invalidos': []
        }
        
        # Procesar cada cliente
        for cliente in clientes:
            email_original = cliente.email
            
            # Caso 1: Email vacío
            if not email_original or email_original.strip() == '':
                estadisticas['vacios'] += 1
                cliente.email_valido = False
                logger.debug(f"Cliente {cliente.id}: Email vacío")
                continue
            
            # Caso 2: Validar email
            if es_email_valido(email_original):
                estadisticas['validos'] += 1
                cliente.email_valido = True
                logger.debug(f"Cliente {cliente.id}: Email válido")
            else:
                # Email inválido
                estadisticas['inválidos'] += 1
                cliente.email_valido = False
                
                # Registrar detalle
                razones = []
                if '@' not in email_original:
                    razones.append("Sin @")
                elif len(email_original) > 254:
                    razones.append("Demasiado largo")
                elif len(email_original) < 5:
                    razones.append("Muy corto")
                else:
                    razones.append("Formato inválido")
                
                estadisticas['detalles_invalidos'].append({
                    'cliente_id': cliente.id,
                    'cliente_nombre': cliente.nombre if hasattr(cliente, 'nombre') else 'N/A',
                    'email_invalido': email_original,
                    'razon': ', '.join(razones)
                })
                
                logger.warning(f"Cliente {cliente.id}: Email inválido - {email_original} ({', '.join(razones)})")
        
        # Guardar cambios
        logger.info(f"\nGuardando cambios en BD...")
        db.commit()
        
        # Mostrar reporte
        logger.info("\n" + "=" * 70)
        logger.info("REPORTE FINAL")
        logger.info("=" * 70)
        logger.info(f"Total clientes:           {estadisticas['total']}")
        logger.info(f"Emails válidos:           {estadisticas['validos']} ({(estadisticas['validos']/estadisticas['total']*100):.1f}%)")
        logger.info(f"Emails inválidos:         {estadisticas['inválidos']} ({(estadisticas['inválidos']/estadisticas['total']*100):.1f}%)")
        logger.info(f"Emails vacíos:            {estadisticas['vacios']} ({(estadisticas['vacios']/estadisticas['total']*100):.1f}%)")
        
        # Mostrar detalles de inválidos
        if estadisticas['detalles_invalidos']:
            logger.info("\n" + "-" * 70)
            logger.info("PRIMEROS 20 EMAILS INVÁLIDOS:")
            logger.info("-" * 70)
            for i, detalle in enumerate(estadisticas['detalles_invalidos'][:20], 1):
                logger.info(f"{i}. Cliente {detalle['cliente_id']} ({detalle['cliente_nombre']})")
                logger.info(f"   Email: {detalle['email_invalido']}")
                logger.info(f"   Razón: {detalle['razon']}")
            
            if len(estadisticas['detalles_invalidos']) > 20:
                logger.info(f"\n... y {len(estadisticas['detalles_invalidos']) - 20} más")
        
        logger.info("\n" + "=" * 70)
        logger.info("✓ LIMPIEZA COMPLETADA EXITOSAMENTE")
        logger.info("=" * 70)
        
        return estadisticas
    
    except Exception as e:
        logger.error(f"Error durante limpieza: {e}", exc_info=True)
        db.rollback()
        return None
    
    finally:
        db.close()


def generar_reporte_csv(estadisticas: Dict, nombre_archivo: str = 'emails_invalidos.csv'):
    """
    Genera reporte CSV de emails inválidos.
    """
    if not estadisticas or not estadisticas['detalles_invalidos']:
        logger.info("No hay emails inválidos para reportar.")
        return
    
    try:
        import csv
        
        with open(nombre_archivo, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(
                f,
                fieldnames=['cliente_id', 'cliente_nombre', 'email_invalido', 'razon', 'fecha']
            )
            writer.writeheader()
            
            for detalle in estadisticas['detalles_invalidos']:
                detalle['fecha'] = datetime.now().isoformat()
                writer.writerow(detalle)
        
        logger.info(f"\n✓ Reporte generado: {nombre_archivo}")
    
    except Exception as e:
        logger.error(f"Error al generar CSV: {e}")


if __name__ == '__main__':
    logger.info("Script de Limpieza de Emails")
    logger.info("Uso: python limpiar_emails.py")
    logger.info("")
    logger.warning("⚠️ IMPORTANTE: Ajusta el path a la BD antes de ejecutar")
    logger.warning("⚠️ Este script modifica la BD - hacer backup primero")
    logger.info("")
    
    # Ejecutar limpieza
    stats = limpiar_emails_bd()
    
    # Generar reporte si hay inválidos
    if stats and stats['detalles_invalidos']:
        generar_reporte_csv(stats)
