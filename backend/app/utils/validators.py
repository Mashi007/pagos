# -*- coding: utf-8 -*-
"""
Validadores para notificaciones y datos de contacto.
Incluye validación de emails, teléfonos y plantillas de notificación.
"""

import re
from typing import Tuple
from datetime import datetime

# Expresión regular para validar emails según RFC 5322 simplificado
EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

# Expresión regular para validar teléfonos internacionales
PHONE_REGEX = r'^\+?[0-9]{7,15}$'

# Dominios bloqueados (testing, localhost, etc.)
BLOCKED_DOMAINS = {
    'localhost',
    '127.0.0.1',
    'example.com',
    'test.com',
    'demo.com',
    'sample.com',
    'email.test',
    'mailinator.com',
    'guerrillamail.com',
    'tempmail.com',
    '10minutemail.com',
}


def es_email_valido(email: str, strict: bool = True) -> bool:
    """
    Valida formato y estructura de un email.
    
    Args:
        email: Dirección de email a validar
        strict: Si True, aplica validaciones adicionales
    
    Returns:
        bool: True si email es válido, False en caso contrario
    
    Examples:
        >>> es_email_valido('usuario@example.com')
        True
        >>> es_email_valido('usuario@localhost')
        False (localhost está bloqueado)
        >>> es_email_valido('')
        False
    """
    
    if not email or not isinstance(email, str):
        return False
    
    # Limpiar espacios
    email = email.strip().lower()
    
    # Validar longitud
    if len(email) < 5 or len(email) > 254:
        return False
    
    # Validar formato con regex
    if not re.match(EMAIL_REGEX, email):
        return False
    
    # Extraer dominio
    dominio = email.split('@')[1]
    
    # Validaciones estrictas si aplican
    if strict:
        # Bloquear dominios sospechosos
        if dominio in BLOCKED_DOMAINS:
            return False
        
        # Bloquear dominios que no tienen TLD válido
        if not re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', dominio):
            return False
        
        # Bloquear emails con patrones sospechosos (ej: ++++, ...)
        if '..' in email or email.startswith('.') or email.endswith('.'):
            return False
    
    return True


def limpiar_email(email: str) -> Tuple[str, bool]:
    """
    Limpia y valida un email.
    
    Returns:
        Tupla (email_limpio, es_valido)
    """
    if not email:
        return None, False
    
    email_limpio = email.strip().lower()
    es_valido = es_email_valido(email_limpio)
    
    return email_limpio if es_valido else email, es_valido


def es_telefono_valido(telefono: str) -> bool:
    """
    Valida formato de número telefónico.
    
    Args:
        telefono: Número de teléfono a validar (ej: +584121234567 o 04121234567)
    
    Returns:
        bool: True si teléfono es válido
    """
    
    if not telefono or not isinstance(telefono, str):
        return False
    
    # Limpiar espacios, guiones, paréntesis
    telefono_limpio = re.sub(r'[\s\-\(\)]', '', telefono)
    
    # Validar formato
    if not re.match(PHONE_REGEX, telefono_limpio):
        return False
    
    return True


def obtener_dominio_email(email: str) -> str:
    """Extrae el dominio de un email."""
    if '@' not in email:
        return None
    return email.split('@')[1].lower()


def es_email_corporativo(email: str, dominios_corporativos: set = None) -> bool:
    """
    Verifica si un email pertenece a dominios corporativos permitidos.
    
    Args:
        email: Email a verificar
        dominios_corporativos: Set de dominios permitidos
    
    Returns:
        bool: True si está en lista blanca
    """
    if not email or not es_email_valido(email):
        return False
    
    dominio = obtener_dominio_email(email)
    
    if dominios_corporativos is None:
        # Si no hay lista, permitir todo
        return True
    
    return dominio in dominios_corporativos


def obtener_estadisticas_email_valido(emails: list) -> dict:
    """
    Analiza un lote de emails y retorna estadísticas.
    
    Returns:
        dict con conteos de válidos, inválidos, bloqueados, etc.
    """
    stats = {
        'total': len(emails),
        'validos': 0,
        'inválidos': 0,
        'bloqueados': 0,
        'vacios': 0,
        'detalles': {
            'inválidos_por_formato': 0,
            'inválidos_por_dominio_bloqueado': 0,
            'inválidos_por_longitud': 0,
        }
    }
    
    for email in emails:
        if not email:
            stats['vacios'] += 1
            continue
        
        if es_email_valido(email, strict=False):  # Validar formato
            if es_email_valido(email, strict=True):  # Validar strict
                stats['validos'] += 1
            else:
                stats['bloqueados'] += 1
                stats['detalles']['inválidos_por_dominio_bloqueado'] += 1
        else:
            stats['inválidos'] += 1
            if len(email) > 254 or len(email) < 5:
                stats['detalles']['inválidos_por_longitud'] += 1
            else:
                stats['detalles']['inválidos_por_formato'] += 1
    
    # Calcular porcentajes
    if stats['total'] > 0:
        stats['porcentaje_valido'] = round((stats['validos'] / stats['total']) * 100, 2)
        stats['porcentaje_inválido'] = round(((stats['inválidos'] + stats['bloqueados']) / stats['total']) * 100, 2)
    
    return stats


def validar_plantilla_notificacion(asunto: str, cuerpo: str, variables_disponibles: set = None) -> dict:
    """
    Valida una plantilla de notificación.
    
    Returns:
        dict con resultado de validación y detalles
    """
    resultado = {
        'valido': True,
        'errores': [],
        'advertencias': [],
        'variables_utilizadas': set()
    }
    
    # Validar que no estén vacíos
    if not asunto or not asunto.strip():
        resultado['valido'] = False
        resultado['errores'].append('Asunto no puede estar vacío')
    
    if not cuerpo or not cuerpo.strip():
        resultado['valido'] = False
        resultado['errores'].append('Cuerpo no puede estar vacío')
    
    # Buscar variables en formato {{variable}}
    variable_pattern = r'\{\{(\w+)\}\}'
    variables_encontradas = set(re.findall(variable_pattern, asunto + ' ' + cuerpo))
    resultado['variables_utilizadas'] = variables_encontradas
    
    # Si hay lista de variables disponibles, validar que todas existan
    if variables_disponibles and variables_encontradas:
        variables_invalidas = variables_encontradas - variables_disponibles
        if variables_invalidas:
            resultado['errores'].append(
                f"Variables no disponibles: {', '.join(variables_invalidas)}"
            )
            resultado['valido'] = False
    
    # Advertencias
    if len(asunto) > 500:
        resultado['advertencias'].append('Asunto muy largo (>500 caracteres)')
    
    if len(cuerpo) > 10000:
        resultado['advertencias'].append('Cuerpo muy largo (>10000 caracteres)')
    
    if not variables_encontradas:
        resultado['advertencias'].append('Plantilla sin variables dinámicas')
    
    return resultado
