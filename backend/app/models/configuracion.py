"""
Modelo para tabla configuracion (clave-valor). Usado para persistir configuración de email, etc.

Campos:
- clave: Identificador único (primary key)
- valor: Valor en texto plano (para compatibilidad hacia atrás)
- valor_encriptado: Valor encriptado con Fernet (para datos sensibles como API keys, contraseñas)

Si tanto valor como valor_encriptado están presentes, se prefiere el encriptado.
"""
from sqlalchemy import Column, String, Text, LargeBinary

from app.core.database import Base


class Configuracion(Base):
    __tablename__ = "configuracion"

    clave = Column(String(100), primary_key=True)
    valor = Column(Text, nullable=True)
    valor_encriptado = Column(LargeBinary, nullable=True)
