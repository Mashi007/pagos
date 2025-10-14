# backend/app/models/configuracion.py
"""
Modelo de Configuración del Sistema
Almacena configuraciones dinámicas del sistema
"""
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON
from sqlalchemy.sql import func
from datetime import datetime
from typing import Any, Dict, List

from app.db.session import Base


class Configuracion(Base):
    """
    Modelo de Configuración del Sistema
    Permite almacenar configuraciones dinámicas como JSON
    """
    __tablename__ = "configuracion"
    
    # Identificación
    id = Column(Integer, primary_key=True, index=True)
    
    # Clave única de configuración
    clave = Column(
        String(100),
        nullable=False,
        unique=True,
        index=True
    )
    
    # Valor de la configuración (JSON)
    valor = Column(JSON, nullable=False)
    
    # Tipo de configuración
    tipo = Column(
        String(50),
        nullable=False,
        index=True
    )  # TASA, LIMITE, NOTIFICACION, EMPRESA, etc.
    
    # Descripción
    descripcion = Column(Text, nullable=True)
    
    # Auditoría
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    def __repr__(self):
        return f"<Configuracion {self.clave} - {self.tipo}>"
    
    @classmethod
    def obtener_valor(cls, db_session, clave: str, valor_defecto: Any = None) -> Any:
        """
        Obtiene el valor de una configuración
        
        Args:
            db_session: Sesión de base de datos
            clave: Clave de configuración
            valor_defecto: Valor por defecto si no existe
            
        Returns:
            Valor de la configuración
        """
        config = db_session.query(cls).filter(cls.clave == clave).first()
        return config.valor if config else valor_defecto
    
    @classmethod
    def establecer_valor(
        cls, 
        db_session, 
        clave: str, 
        valor: Any, 
        tipo: str = "GENERAL",
        descripcion: str = None
    ) -> 'Configuracion':
        """
        Establece el valor de una configuración
        
        Args:
            db_session: Sesión de base de datos
            clave: Clave de configuración
            valor: Valor a establecer
            tipo: Tipo de configuración
            descripcion: Descripción opcional
            
        Returns:
            Configuracion: Registro de configuración
        """
        config = db_session.query(cls).filter(cls.clave == clave).first()
        
        if config:
            # Actualizar existente
            config.valor = valor
            config.tipo = tipo
            config.descripcion = descripcion
            config.updated_at = datetime.utcnow()
        else:
            # Crear nuevo
            config = cls(
                clave=clave,
                valor=valor,
                tipo=tipo,
                descripcion=descripcion
            )
            db_session.add(config)
        
        db_session.commit()
        db_session.refresh(config)
        
        return config
    
    @classmethod
    def obtener_por_tipo(cls, db_session, tipo: str) -> List['Configuracion']:
        """
        Obtiene todas las configuraciones de un tipo
        
        Args:
            db_session: Sesión de base de datos
            tipo: Tipo de configuración
            
        Returns:
            List[Configuracion]: Lista de configuraciones
        """
        return db_session.query(cls).filter(cls.tipo == tipo).all()
