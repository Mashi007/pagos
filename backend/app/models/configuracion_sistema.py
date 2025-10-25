"""
Modelo de Configuración del Sistema
Configuración centralizada del sistema
"""

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.db.session import Base


class ConfiguracionSistema(Base):
    """
    Configuración centralizada del sistema
    """

    __tablename__ = "configuracion_sistema"

    id = Column(Integer, primary_key=True, index=True)
    categoria = Column(
        String(50), nullable=False, index=True
    )  # AI, EMAIL, WHATSAPP, etc.
    subcategoria = Column(
        String(50), nullable=True, index=True
    )  # OPENAI, GMAIL, TWILIO, etc.
    clave = Column(
        String(100), nullable=False, index=True
    )  # Nombre de la configuración
    valor = Column(Text, nullable=True)  # Valor de la configuración
    valor_json = Column(JSON, nullable=True)  # Para configuraciones complejas

    descripcion = Column(Text, nullable=True)
    tipo_dato = Column(
        String(20), default="STRING"
    )  # STRING, INTEGER, BOOLEAN, JSON, PASSWORD
    requerido = Column(Boolean, default=False)
    visible_frontend = Column(Boolean, default=True)
    solo_lectura = Column(Boolean, default=False)

    # Validaciones
    valor_minimo = Column(String(100), nullable=True)
    valor_maximo = Column(String(100), nullable=True)
    opciones_validas = Column(Text, nullable=True)  # JSON array de opciones válidas
    patron_validacion = Column(String(200), nullable=True)  # Regex para validación

    # Auditoría
    creado_en = Column(DateTime, server_default=func.now())
    actualizado_en = Column(DateTime, server_default=func.now(), onupdate=func.now())
    creado_por = Column(String(100), nullable=True)
    actualizado_por = Column(String(100), nullable=True)

    def __repr__(self):
        return f"<ConfiguracionSistema {self.categoria}.{self.clave}={self.valor}>"

    def obtener_valor_tipado(self) -> Any:
        """Obtiene el valor con el tipo correcto según tipo_dato"""
        if not self.valor:
            return None

        if self.tipo_dato == "INTEGER":
            try:
                return int(self.valor)
            except ValueError:
                return None
        elif self.tipo_dato == "BOOLEAN":
            return self.valor.lower() in ("true", "1", "yes", "on")
        elif self.tipo_dato == "JSON":
            return self.valor_json
        else:
            return self.valor

    def establecer_valor(self, nuevo_valor: Any, usuario: str = None):
        """Establece un nuevo valor con validación de tipo"""
        if self.tipo_dato == "INTEGER":
            try:
                self.valor = str(int(nuevo_valor))
            except ValueError:
                raise ValueError(f"Valor {nuevo_valor} no es un entero válido")
        elif self.tipo_dato == "BOOLEAN":
            if isinstance(nuevo_valor, bool):
                self.valor = str(nuevo_valor).lower()
            else:
                self.valor = str(nuevo_valor)
        else:
            self.valor = str(nuevo_valor)

        if usuario:
            self.actualizado_por = usuario

    @staticmethod
    def obtener_por_clave(
        db, categoria: str, clave: str
    ) -> Optional["ConfiguracionSistema"]:
        """Obtener configuración por categoría y clave"""
        return (
            db.query(ConfiguracionSistema)
            .filter(
                ConfiguracionSistema.categoria == categoria,
                ConfiguracionSistema.clave == clave,
            )
            .first()
        )

    @staticmethod
    def obtener_categoria(db, categoria: str) -> Dict[str, Any]:
        """Obtener todas las configuraciones de una categoría"""
        configs = (
            db.query(ConfiguracionSistema)
            .filter(ConfiguracionSistema.categoria == categoria)
            .all()
        )
        resultado = {}
        for config in configs:
            resultado[config.clave] = config.obtener_valor_tipado()
        return resultado

    def to_dict(self):
        """Convierte la configuración a diccionario"""
        return {
            "id": self.id,
            "categoria": self.categoria,
            "subcategoria": self.subcategoria,
            "clave": self.clave,
            "valor": self.valor,
            "valor_json": self.valor_json,
            "descripcion": self.descripcion,
            "tipo_dato": self.tipo_dato,
            "requerido": self.requerido,
            "visible_frontend": self.visible_frontend,
            "solo_lectura": self.solo_lectura,
            "valor_minimo": self.valor_minimo,
            "valor_maximo": self.valor_maximo,
            "opciones_validas": self.opciones_validas,
            "patron_validacion": self.patron_validacion,
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
            "actualizado_en": (
                self.actualizado_en.isoformat() if self.actualizado_en else None
            ),
            "creado_por": self.creado_por,
            "actualizado_por": self.actualizado_por,
        }
