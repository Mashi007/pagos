"""Helper para registrar acciones de auditoría
Integración automática con todos los módulos
"""

import logging
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models.auditoria import Auditoria
from app.models.user import User

logger = logging.getLogger(__name__)


def registrar_auditoria(
    db: Session,
    usuario: User,
    accion: str,
    modulo: str,
    tabla: str,
    registro_id: Optional[int] = None,
    descripcion: Optional[str] = None,
    datos_anteriores: Optional[Dict[str, Any]] = None,
    datos_nuevos: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    resultado: str = "EXITOSO",
    mensaje_error: Optional[str] = None,
) -> Auditoria:
    """
    Registrar una acción en la auditoría del sistema
    
    Args:
        db: Sesión de base de datos
        usuario: Usuario que realizó la acción
        accion: Tipo de acción (CREAR, ACTUALIZAR, ELIMINAR, LOGIN, etc.)
        modulo: Módulo del sistema (USUARIOS, CLIENTES, PRESTAMOS, etc.)
        tabla: Tabla afectada
        registro_id: ID del registro afectado
        descripcion: Descripción de la acción
        datos_anteriores: Estado anterior (dict)
        datos_nuevos: Estado nuevo (dict)
        ip_address: IP del usuario
        user_agent: User agent del navegador
        resultado: Resultado de la acción
        mensaje_error: Mensaje de error si falló
    
    Returns:
        Auditoria: Registro de auditoría creado
    """
    # Validar que el usuario no sea None
    if usuario is None:
        logger.warning(
            f"Intento de registrar auditoría sin"
            + f"usuario válido: {accion} - {modulo}"
        )
        raise ValueError(
            "No se puede registrar auditoría sin un usuario válido"
        )

    try:
        auditoria = Auditoria.registrar(
            usuario_id=usuario.id,
            usuario_email=usuario.email,
            accion=accion,
            modulo=modulo,
            tabla=tabla,
            registro_id=registro_id,
            descripcion=descripcion,
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos,
            ip_address=ip_address,
            user_agent=user_agent,
            resultado=resultado,
            mensaje_error=mensaje_error,
        )

        db.add(auditoria)
        db.commit()
        db.refresh(auditoria)

        logger.info(
            f"Auditoría registrada: {usuario.email} - {accion} - {modulo}"
        )
        return auditoria
    except Exception as e:
        logger.error(f"Error registrando auditoría: {e}")
        db.rollback()
        raise


def registrar_login_exitoso(
    db: Session,
    usuario: User,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Auditoria:
    """Registrar login exitoso"""
    return registrar_auditoria(
        db=db,
        usuario=usuario,
        accion="LOGIN",
        modulo="AUTH",
        tabla="usuarios",
        registro_id=usuario.id,
        descripcion=f"Inicio de sesión exitoso para {usuario.email}",
        ip_address=ip_address,
        user_agent=user_agent,
        resultado="EXITOSO",
    )


def registrar_logout(
    db: Session,
    usuario: User,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Auditoria:
    """Registrar logout"""
    return registrar_auditoria(
        db=db,
        usuario=usuario,
        accion="LOGOUT",
        modulo="AUTH",
        tabla="usuarios",
        registro_id=usuario.id,
        descripcion=f"Cierre de sesión para {usuario.email}",
        ip_address=ip_address,
        user_agent=user_agent,
        resultado="EXITOSO",
    )


def registrar_creacion(
    db: Session,
    usuario: User,
    modulo: str,
    tabla: str,
    registro_id: int,
    descripcion: str,
    datos_nuevos: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Auditoria:
    """Registrar creación de registro"""
    return registrar_auditoria(
        db=db,
        usuario=usuario,
        accion="CREAR",
        modulo=modulo,
        tabla=tabla,
        registro_id=registro_id,
        descripcion=descripcion,
        datos_nuevos=datos_nuevos,
        ip_address=ip_address,
        user_agent=user_agent,
        resultado="EXITOSO",
    )


def registrar_actualizacion(
    db: Session,
    usuario: User,
    modulo: str,
    tabla: str,
    registro_id: int,
    descripcion: str,
    datos_anteriores: Optional[Dict[str, Any]] = None,
    datos_nuevos: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Auditoria:
    """Registrar actualización de registro"""
    return registrar_auditoria(
        db=db,
        usuario=usuario,
        accion="ACTUALIZAR",
        modulo=modulo,
        tabla=tabla,
        registro_id=registro_id,
        descripcion=descripcion,
        datos_anteriores=datos_anteriores,
        datos_nuevos=datos_nuevos,
        ip_address=ip_address,
        user_agent=user_agent,
        resultado="EXITOSO",
    )


def registrar_eliminacion(
    db: Session,
    usuario: User,
    modulo: str,
    tabla: str,
    registro_id: int,
    descripcion: str,
    datos_anteriores: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Auditoria:
    """Registrar eliminación de registro"""
    return registrar_auditoria(
        db=db,
        usuario=usuario,
        accion="ELIMINAR",
        modulo=modulo,
        tabla=tabla,
        registro_id=registro_id,
        descripcion=descripcion,
        datos_anteriores=datos_anteriores,
        ip_address=ip_address,
        user_agent=user_agent,
        resultado="EXITOSO",
    )


def registrar_error(
    db: Session,
    usuario: User,
    accion: str,
    modulo: str,
    tabla: str,
    descripcion: str,
    mensaje_error: str,
    registro_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Auditoria:
    """Registrar error en acción"""
    return registrar_auditoria(
        db=db,
        usuario=usuario,
        accion=accion,
        modulo=modulo,
        tabla=tabla,
        registro_id=registro_id,
        descripcion=descripcion,
        ip_address=ip_address,
        user_agent=user_agent,
        resultado="FALLIDO",
        mensaje_error=mensaje_error,
    )