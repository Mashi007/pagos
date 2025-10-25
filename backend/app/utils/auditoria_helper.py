"""
Helper para registrar acciones de auditoría
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
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    resultado: str = "SUCCESS",
    mensaje_error: Optional[str] = None,
) -> Auditoria:
    """
    Registrar una acción en la auditoría del sistema

    Args:
        usuario: Usuario que realizó la acción
        accion: Tipo de acción (CREAR, ACTUALIZAR, ELIMINAR, LOGIN, etc.)
        modulo: Módulo del sistema (USUARIOS, CLIENTES, PRESTAMOS, etc.)
        tabla: Tabla afectada
        registro_id: ID del registro afectado
        descripcion: Descripción de la acción
        ip_address: IP del usuario
        user_agent: User agent del navegador
        resultado: Resultado de la acción
        mensaje_error: Mensaje de error si falló

    Returns:
        Auditoria: Registro de auditoría creado
    """
    # Validar que el usuario no sea None
    if usuario is None:
        logger.warning("Intento de registrar auditoría sin usuario")
        raise ValueError("El usuario no puede ser None")

    try:
        auditoria = Auditoria.registrar(
            usuario_id=usuario.id,
            accion=accion,
            modulo=modulo,
            tabla=tabla,
            registro_id=registro_id,
            descripcion=descripcion,
            ip_address=ip_address,
            user_agent=user_agent,
            resultado=resultado,
            mensaje_error=mensaje_error
        )

        db.add(auditoria)
        db.commit()
        db.refresh(auditoria)

        logger.info(f"Auditoría registrada: {accion} en {modulo}")
        return auditoria
    except Exception as e:
        logger.error(f"Error registrando auditoría: {e}")
        db.rollback()
        raise


def registrar_login(
    db: Session,
    usuario: User,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> Auditoria:
    return registrar_auditoria(
        db=db,
        usuario=usuario,
        accion="LOGIN",
        modulo="AUTH",
        tabla="users",
        descripcion="Inicio de sesión",
        ip_address=ip_address,
        user_agent=user_agent
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
        tabla="users",
        descripcion="Cierre de sesión",
        ip_address=ip_address,
        user_agent=user_agent
    )


def registrar_creacion(
    db: Session,
    usuario: User,
    modulo: str,
    tabla: str,
    registro_id: int,
    descripcion: Optional[str] = None,
) -> Auditoria:
    """Registrar creación de registro"""
    return registrar_auditoria(
        db=db,
        usuario=usuario,
        accion="CREAR",
        modulo=modulo,
        tabla=tabla,
        registro_id=registro_id,
        descripcion=descripcion or f"Creación de registro en {tabla}"
    )


def registrar_actualizacion(
    db: Session,
    usuario: User,
    modulo: str,
    tabla: str,
    registro_id: int,
    descripcion: Optional[str] = None,
) -> Auditoria:
    """Registrar actualización de registro"""
    return registrar_auditoria(
        db=db,
        usuario=usuario,
        accion="ACTUALIZAR",
        modulo=modulo,
        tabla=tabla,
        registro_id=registro_id,
        descripcion=descripcion or f"Actualización de registro en {tabla}"
    )


def registrar_eliminacion(
    db: Session,
    usuario: User,
    modulo: str,
    tabla: str,
    registro_id: int,
    descripcion: Optional[str] = None,
) -> Auditoria:
    """Registrar eliminación de registro"""
    return registrar_auditoria(
        db=db,
        usuario=usuario,
        accion="ELIMINAR",
        modulo=modulo,
        tabla=tabla,
        registro_id=registro_id,
        descripcion=descripcion or f"Eliminación de registro en {tabla}"
    )


def registrar_error(
    db: Session,
    usuario: User,
    modulo: str,
    tabla: str,
    error: str,
    registro_id: Optional[int] = None,
) -> Auditoria:
    """Registrar error en acción"""
    return registrar_auditoria(
        db=db,
        usuario=usuario,
        accion="ERROR",
        modulo=modulo,
        tabla=tabla,
        registro_id=registro_id,
        resultado="ERROR",
        mensaje_error=error,
        descripcion=f"Error en {modulo}"
    )