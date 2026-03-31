"""
Servicio para registrar cambios en el sistema.
Proporciona funciones para registrar cambios de forma centralizada.
"""
from datetime import datetime, timezone
from typing import Any, Optional, Dict
from sqlalchemy.orm import Session
from app.models.registro_cambios import RegistroCambios
from app.models.user import User


def registrar_cambio(
    db: Session,
    usuario_id: int,
    modulo: str,
    tipo_cambio: str,
    descripcion: str,
    registro_id: Optional[int] = None,
    tabla_afectada: Optional[str] = None,
    campos_anteriores: Optional[Dict[str, Any]] = None,
    campos_nuevos: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> RegistroCambios:
    """
    Registra un cambio en la tabla registro_cambios.
    
    Args:
        db: Sesión de base de datos
        usuario_id: ID del usuario que realiza el cambio
        modulo: Módulo del sistema (ej: 'Préstamos', 'Pagos', 'Auditoría')
        tipo_cambio: Tipo de cambio (CREAR, ACTUALIZAR, ELIMINAR, etc.)
        descripcion: Descripción legible del cambio
        registro_id: ID del registro afectado (opcional)
        tabla_afectada: Nombre de la tabla afectada (opcional)
        campos_anteriores: Dict con valores anteriores (opcional)
        campos_nuevos: Dict con valores nuevos (opcional)
        ip_address: Dirección IP del cliente (opcional)
        user_agent: User agent del cliente (opcional)
    
    Returns:
        RegistroCambios: El registro creado
    """
    # Obtener email del usuario
    usuario = db.query(User).filter(User.id == usuario_id).first()
    usuario_email = usuario.email if usuario else None
    
    # Crear el registro
    cambio = RegistroCambios(
        usuario_id=usuario_id,
        usuario_email=usuario_email,
        modulo=modulo,
        tipo_cambio=tipo_cambio,
        descripcion=descripcion,
        registro_id=registro_id,
        tabla_afectada=tabla_afectada,
        campos_anteriores=campos_anteriores,
        campos_nuevos=campos_nuevos,
        ip_address=ip_address,
        user_agent=user_agent,
        fecha_hora=datetime.now(timezone.utc),
    )
    
    db.add(cambio)
    db.commit()
    db.refresh(cambio)
    
    return cambio


def obtener_cambios_recientes(
    db: Session,
    modulo: Optional[str] = None,
    usuario_id: Optional[int] = None,
    registro_id: Optional[int] = None,
    limite: int = 100,
) -> list[RegistroCambios]:
    """
    Obtiene los cambios más recientes con filtros opcionales.
    
    Args:
        db: Sesión de base de datos
        modulo: Filtrar por módulo (opcional)
        usuario_id: Filtrar por usuario (opcional)
        registro_id: Filtrar por ID de registro (opcional)
        limite: Número máximo de registros a retornar
    
    Returns:
        Lista de cambios ordenados por fecha descendente
    """
    query = db.query(RegistroCambios)
    
    if modulo:
        query = query.filter(RegistroCambios.modulo == modulo)
    
    if usuario_id:
        query = query.filter(RegistroCambios.usuario_id == usuario_id)
    
    if registro_id:
        query = query.filter(RegistroCambios.registro_id == registro_id)
    
    return query.order_by(RegistroCambios.fecha_hora.desc()).limit(limite).all()
