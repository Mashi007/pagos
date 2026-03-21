# -*- coding: utf-8 -*-
"""
Patch para integrar validación de emails en notificaciones.
Este módulo agrega validación antes de enviar emails.
"""

from app.utils.validators import es_email_valido
from app.core.logger import logger  # Ajustar según tu logger


def validar_email_antes_envio(cliente_email: str, cliente_id: int = None) -> tuple[bool, str]:
    """
    Valida email antes de intentar enviar.
    
    Returns:
        (es_valido, motivo_si_invalido)
    """
    
    if not cliente_email:
        return False, f"Cliente {cliente_id}: Email vacío"
    
    if not es_email_valido(cliente_email):
        return False, f"Cliente {cliente_id}: Email inválido '{cliente_email}'"
    
    return True, None


def validar_lote_emails(clientes: list) -> dict:
    """
    Valida un lote de clientes antes de envío masivo.
    
    Returns:
        {
            'total': int,
            'validos': int,
            'invalidos': int,
            'saltados': list de {'cliente_id', 'razon'}
        }
    """
    
    stats = {
        'total': len(clientes),
        'validos': 0,
        'invalidos': 0,
        'saltados': []
    }
    
    for cliente in clientes:
        es_valido, razon = validar_email_antes_envio(
            getattr(cliente, 'email', None),
            getattr(cliente, 'id', None)
        )
        
        if es_valido:
            stats['validos'] += 1
        else:
            stats['invalidos'] += 1
            stats['saltados'].append({
                'cliente_id': cliente.id,
                'razon': razon
            })
            logger.warning(razon)
    
    return stats


# Ejemplo de uso en endpoint:
# 
# @router.post("/enviar-todas-validado")
# def enviar_todas_validado(db: Session = Depends(get_db)):
#     clientes = db.query(Cliente).all()
#     stats = validar_lote_emails(clientes)
#     
#     if stats['invalidos'] > 0:
#         logger.warning(f"Se saltarán {stats['invalidos']} clientes con email inválido")
#     
#     # Solo procesar clientes con email válido
#     for cliente in clientes:
#         es_valido, _ = validar_email_antes_envio(cliente.email, cliente.id)
#         if es_valido:
#             enviar_notificacion(cliente)
#     
#     return {
#         'total': stats['total'],
#         'procesados': stats['validos'],
#         'saltados': stats['invalidos']
#     }
