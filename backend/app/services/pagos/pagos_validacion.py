"""Servicios de validación para pagos."""

from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.cliente import Cliente
from app.models.cuenta import Cuenta
from app.models.pago import Pago
from app.core.documento import normalize_documento
from .pagos_excepciones import (
    PagoValidationError,
    PagoConflictError,
    ClienteNotFoundError,
    CuentaNotFoundError,
)


class PagosValidacion:
    """Servicio de validaciones para pagos."""

    def __init__(self, db: Session):
        self.db = db

    def validar_cliente_existe(self, cliente_id: int) -> Cliente:
        """Valida que el cliente existe en la BD."""
        cliente = self.db.query(Cliente).filter(Cliente.id == cliente_id).first()
        if not cliente:
            raise ClienteNotFoundError(cliente_id)
        return cliente

    def validar_cuenta_existe(self, cuenta_id: int) -> Cuenta:
        """Valida que la cuenta existe en la BD."""
        cuenta = self.db.query(Cuenta).filter(Cuenta.id == cuenta_id).first()
        if not cuenta:
            raise CuentaNotFoundError(cuenta_id)
        return cuenta

    def validar_monto(self, monto: float) -> bool:
        """Valida que el monto sea válido (> 0)."""
        if not monto or monto <= 0:
            raise PagoValidationError("monto", "Monto debe ser mayor a 0")
        return True

    def validar_monto_numerico(self, monto: any) -> float:
        """Valida y convierte monto a número."""
        try:
            monto_float = float(monto)
            self.validar_monto(monto_float)
            return monto_float
        except (ValueError, TypeError):
            raise PagoValidationError("monto", "Monto debe ser un número válido")

    def validar_documento_no_duplicado(
        self, documento: str, excluir_pago_id: Optional[int] = None
    ) -> bool:
        """
        Valida que el documento no esté duplicado en la BD.
        Si excluir_pago_id es proporcionado, lo excluye de la búsqueda (para actualizaciones).
        """
        if not documento or not documento.strip():
            # Documentos vacíos son permitidos (múltiples filas sin documento)
            return True

        documento_normalizado = normalize_documento(documento)
        query = self.db.query(Pago).filter(
            Pago.documento_normalizado == documento_normalizado
        )

        if excluir_pago_id:
            query = query.filter(Pago.id != excluir_pago_id)

        duplicado = query.first()
        if duplicado:
            raise PagoConflictError(
                f"Documento '{documento}' ya existe. NAº documentos no pueden duplicarse."
            )

        return True

    def validar_referencia_pago(self, referencia: str) -> bool:
        """Valida que la referencia de pago sea válida."""
        if referencia and len(referencia) > 100:
            raise PagoValidationError("referencia", "Referencia no puede exceder 100 caracteres")
        return True

    def validar_estado_pago(self, estado: str) -> bool:
        """Valida que el estado sea un estado válido."""
        estados_validos = ["pendiente", "aplicado", "rechazado", "cancelado"]
        if estado not in estados_validos:
            raise PagoValidationError("estado", f"Estado debe ser uno de: {', '.join(estados_validos)}")
        return True

    def validar_datos_pago_completos(self, datos: dict) -> bool:
        """Valida que todos los datos requeridos estén presentes."""
        campos_requeridos = ["cliente_id", "monto"]
        
        for campo in campos_requeridos:
            if campo not in datos or datos[campo] is None:
                raise PagoValidationError(campo, f"Campo requerido")
        
        return True
