"""
Script para aplicar pagos conciliados que no se han aplicado a cuotas.

Este script identifica pagos conciliados (conciliado=True o verificado_concordancia='SI')
que tienen prestamo_id pero que no se han aplicado completamente a las cuotas,
y los aplica usando la función aplicar_pago_a_cuotas del sistema.
"""

import logging
import os
import sys
import time
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse, quote, urlunparse

# Agregar backend al path para imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from sqlalchemy import create_engine, and_, or_
from sqlalchemy.orm import sessionmaker, Session

from app.models.pago import Pago
from app.models.prestamo import Prestamo
from app.models.user import User
from app.api.v1.endpoints.pagos import aplicar_pago_a_cuotas

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configurar conexión a base de datos
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL no está configurada")

# Manejar encoding de DATABASE_URL
try:
    parsed = urlparse(DATABASE_URL)
    if parsed.username:
        encoded_username = quote(parsed.username, safe='')
        encoded_password = quote(parsed.password or '', safe='')
        encoded_netloc = f"{encoded_username}:{encoded_password}@{parsed.hostname}"
        if parsed.port:
            encoded_netloc += f":{parsed.port}"
        DATABASE_URL = urlunparse((
            parsed.scheme,
            encoded_netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment
        ))
except Exception as e:
    logger.warning(f"⚠️ No se pudo procesar DATABASE_URL para encoding: {e}")

engine = create_engine(
    DATABASE_URL,
    connect_args={'client_encoding': 'utf8'},
    pool_pre_ping=True
)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def identificar_pagos_conciliados_sin_aplicar(db: Session) -> list:
    """
    Identifica pagos conciliados que no se han aplicado completamente a cuotas.
    
    Un pago se considera "sin aplicar" si:
    - Está conciliado (conciliado=True o verificado_concordancia='SI')
    - Tiene prestamo_id
    - El préstamo existe y tiene cuotas
    - El monto del pago no se ha aplicado completamente a las cuotas
    
    Returns:
        Lista de tuplas (pago_id, prestamo_id, monto_pagado, total_aplicado, diferencia)
    """
    logger.info("🔍 Identificando pagos conciliados sin aplicar...")
    
    # Obtener pagos conciliados con prestamo_id
    pagos_conciliados = db.query(Pago).filter(
        and_(
            or_(Pago.conciliado == True, Pago.verificado_concordancia == 'SI'),
            Pago.prestamo_id.isnot(None),
            Pago.activo != False
        )
    ).all()
    
    logger.info(f"📊 Encontrados {len(pagos_conciliados)} pagos conciliados con prestamo_id")
    
    pagos_sin_aplicar = []
    
    for pago in pagos_conciliados:
        # Verificar que el préstamo existe
        prestamo = db.query(Prestamo).filter(Prestamo.id == pago.prestamo_id).first()
        if not prestamo:
            logger.warning(f"⚠️ Pago {pago.id}: Préstamo {pago.prestamo_id} no existe")
            continue
        
        # Verificar que la cédula coincide
        if pago.cedula != prestamo.cedula:
            logger.warning(
                f"⚠️ Pago {pago.id}: Cédula del pago ({pago.cedula}) "
                f"no coincide con cédula del préstamo ({prestamo.cedula})"
            )
            continue
        
        # Calcular monto aplicado en cuotas del préstamo
        # Nota: No podemos calcular exactamente cuánto de este pago específico
        # se aplicó, pero podemos intentar aplicar el pago y ver si hay cambios
        # Por ahora, intentamos aplicar todos los pagos conciliados que no hayan
        # sido aplicados previamente
        
        # Verificar si el pago ya fue aplicado revisando el estado
        # Si el estado es NULL o diferente de PAGADO/PARCIAL, probablemente no se aplicó
        estado_aplicado = pago.estado in ['PAGADO', 'PARCIAL']
        
        if not estado_aplicado:
            pagos_sin_aplicar.append({
                'pago_id': pago.id,
                'prestamo_id': pago.prestamo_id,
                'cedula': pago.cedula,
                'monto_pagado': pago.monto_pagado,
                'fecha_pago': pago.fecha_pago,
                'numero_documento': pago.numero_documento,
                'razon': 'Estado no indica aplicación (estado: {})'.format(pago.estado or 'NULL')
            })
        else:
            # Aún si el estado es PAGADO/PARCIAL, intentamos reaplicar para asegurar
            # que se aplicó correctamente (puede haber errores previos)
            logger.debug(
                f"ℹ️ Pago {pago.id}: Estado {pago.estado}, "
                f"pero se intentará reaplicar para verificar"
            )
            pagos_sin_aplicar.append({
                'pago_id': pago.id,
                'prestamo_id': pago.prestamo_id,
                'cedula': pago.cedula,
                'monto_pagado': pago.monto_pagado,
                'fecha_pago': pago.fecha_pago,
                'numero_documento': pago.numero_documento,
                'razon': 'Reaplicación para verificar'
            })
    
    logger.info(f"✅ Identificados {len(pagos_sin_aplicar)} pagos para aplicar")
    return pagos_sin_aplicar


def aplicar_pago_a_cuotas_seguro(pago_id: int, db: Session) -> dict:
    """
    Aplica un pago a cuotas de forma segura con manejo de errores.
    
    Returns:
        dict con resultado: {'exito': bool, 'cuotas_completadas': int, 'error': str}
    """
    try:
        # Obtener el pago
        pago = db.query(Pago).filter(Pago.id == pago_id).first()
        if not pago:
            return {
                'exito': False,
                'cuotas_completadas': 0,
                'error': f'Pago {pago_id} no encontrado'
            }
        
        # Verificar que esté conciliado
        if not pago.conciliado and getattr(pago, 'verificado_concordancia', None) != 'SI':
            return {
                'exito': False,
                'cuotas_completadas': 0,
                'error': f'Pago {pago_id} no está conciliado'
            }
        
        # Obtener usuario del sistema para aplicar
        usuario_sistema = db.query(User).first()
        if not usuario_sistema:
            logger.warning("⚠️ No se encontró usuario del sistema, usando usuario por defecto")
            # Crear usuario temporal si no existe
            usuario_sistema = User(
                email="sistema@rapicredit.com",
                nombre="Sistema",
                activo=True
            )
        
        # Aplicar pago a cuotas
        cuotas_completadas = aplicar_pago_a_cuotas(pago, db, usuario_sistema)
        
        return {
            'exito': True,
            'cuotas_completadas': cuotas_completadas,
            'error': None
        }
        
    except Exception as e:
        logger.error(f"❌ Error aplicando pago {pago_id}: {str(e)}", exc_info=True)
        db.rollback()
        return {
            'exito': False,
            'cuotas_completadas': 0,
            'error': str(e)
        }


def main():
    """Función principal para aplicar pagos conciliados pendientes."""
    logger.info("=" * 80)
    logger.info("🚀 INICIANDO APLICACIÓN DE PAGOS CONCILIADOS PENDIENTES")
    logger.info("=" * 80)
    
    # Verificar confirmación automática
    auto_confirm = os.getenv("AUTO_CONFIRM_APLICAR_PAGOS", "").upper() == "SI"
    
    if not auto_confirm:
        try:
            respuesta = input(
                "\nEste script aplicara pagos conciliados a cuotas. "
                "Desea continuar? (SI/no): "
            ).strip().upper()
            if respuesta != "SI":
                logger.info("Operacion cancelada por el usuario")
                return
        except (EOFError, KeyboardInterrupt, UnicodeEncodeError):
            logger.info("Operacion cancelada o error de encoding")
            logger.info("Para ejecutar sin confirmacion, configure AUTO_CONFIRM_APLICAR_PAGOS=SI")
            return
    
    db = SessionLocal()
    
    try:
        # Identificar pagos pendientes
        pagos_pendientes = identificar_pagos_conciliados_sin_aplicar(db)
        
        if not pagos_pendientes:
            logger.info("✅ No hay pagos conciliados pendientes de aplicar")
            return
        
        total_pagos = len(pagos_pendientes)
        logger.info(f"📊 Total de pagos a procesar: {total_pagos}")
        
        # Estadísticas
        pagos_exitosos = 0
        pagos_fallidos = 0
        total_cuotas_completadas = 0
        monto_total_aplicado = Decimal("0.00")
        errores = []
        
        # Tiempo de inicio
        tiempo_inicio = time.time()
        ultimo_reporte_tiempo = tiempo_inicio
        intervalo_reporte_tiempo = 600  # 10 minutos
        
        # Procesar cada pago
        for idx, pago_info in enumerate(pagos_pendientes, 1):
            pago_id = pago_info['pago_id']
            
            # Reporte periódico cada 50 pagos o cada 10 minutos
            tiempo_actual = time.time()
            if idx % 50 == 0 or (tiempo_actual - ultimo_reporte_tiempo) >= intervalo_reporte_tiempo:
                tiempo_transcurrido = tiempo_actual - tiempo_inicio
                tiempo_promedio = tiempo_transcurrido / idx if idx > 0 else 0
                tiempo_restante = tiempo_promedio * (total_pagos - idx)
                
                logger.info("=" * 80)
                logger.info(f"📊 REPORTE DE AVANCE (Pago {idx}/{total_pagos})")
                logger.info(f"   ✅ Exitosos: {pagos_exitosos}")
                logger.info(f"   ❌ Fallidos: {pagos_fallidos}")
                logger.info(f"   💰 Cuotas completadas: {total_cuotas_completadas}")
                logger.info(f"   💵 Monto aplicado: ${monto_total_aplicado:,.2f}")
                logger.info(f"   ⏱️ Tiempo transcurrido: {timedelta(seconds=int(tiempo_transcurrido))}")
                logger.info(f"   ⏱️ Tiempo estimado restante: {timedelta(seconds=int(tiempo_restante))}")
                logger.info("=" * 80)
                
                ultimo_reporte_tiempo = tiempo_actual
            
            # Aplicar pago
            logger.info(
                f"[{idx}/{total_pagos}] Aplicando pago ID {pago_id} "
                f"(Préstamo: {pago_info['prestamo_id']}, Monto: ${pago_info['monto_pagado']:,.2f})"
            )
            
            resultado = aplicar_pago_a_cuotas_seguro(pago_id, db)
            
            if resultado['exito']:
                pagos_exitosos += 1
                total_cuotas_completadas += resultado['cuotas_completadas']
                monto_total_aplicado += pago_info['monto_pagado']
                
                if resultado['cuotas_completadas'] > 0:
                    logger.info(
                        f"   ✅ Pago aplicado exitosamente. "
                        f"Cuotas completadas: {resultado['cuotas_completadas']}"
                    )
                else:
                    logger.info(f"   ℹ️ Pago aplicado pero no completó cuotas (puede ser parcial)")
            else:
                pagos_fallidos += 1
                errores.append({
                    'pago_id': pago_id,
                    'error': resultado['error']
                })
                logger.warning(f"   ❌ Error: {resultado['error']}")
        
        # Reporte final
        tiempo_total = time.time() - tiempo_inicio
        
        logger.info("=" * 80)
        logger.info("📊 REPORTE FINAL")
        logger.info("=" * 80)
        logger.info(f"✅ Pagos aplicados exitosamente: {pagos_exitosos}")
        logger.info(f"❌ Pagos fallidos: {pagos_fallidos}")
        logger.info(f"💰 Total cuotas completadas: {total_cuotas_completadas}")
        logger.info(f"💵 Monto total aplicado: ${monto_total_aplicado:,.2f}")
        logger.info(f"⏱️ Tiempo total: {timedelta(seconds=int(tiempo_total))}")
        logger.info(f"📈 Tasa de éxito: {(pagos_exitosos/total_pagos*100):.2f}%")
        
        if errores:
            logger.info("\n❌ ERRORES ENCONTRADOS:")
            for error in errores[:10]:  # Mostrar primeros 10
                logger.info(f"   - Pago {error['pago_id']}: {error['error']}")
            if len(errores) > 10:
                logger.info(f"   ... y {len(errores) - 10} errores más")
        
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"❌ Error crítico: {str(e)}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
