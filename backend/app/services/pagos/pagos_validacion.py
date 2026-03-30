"""Servicios de validación para pagos."""

from typing import Optional

from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.services.pago_numero_documento import numero_documento_ya_registrado
from .pagos_excepciones import (
    PagoValidationError,
    PagoConflictError,
    ClienteNotFoundError,
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
        Misma regla que POST /pagos: `numero_documento` canónico único en `pagos` y `pagos_con_errores`.
        """
        if not documento or not documento.strip():
            return True

        if numero_documento_ya_registrado(
            self.db, documento, exclude_pago_id=excluir_pago_id
        ):
            raise PagoConflictError(
                f"Documento '{documento}' ya existe. Los numeros de documento no pueden duplicarse."
            )

        return True

    def validar_referencia_pago(self, referencia: str) -> bool:
        """Valida que la referencia de pago sea válida."""
        if referencia and len(referencia) > 100:
            raise PagoValidationError("referencia", "Referencia no puede exceder 100 caracteres")
        return True

    def validar_estado_pago(self, estado: str) -> bool:
        """Estados usados en tabla `pagos` (mayusculas) y valores legados en minuscula."""
        e = (estado or "").strip()
        if not e:
            raise PagoValidationError("estado", "Estado vacio")
        estados_validos = (
            "PENDIENTE",
            "PAGADO",
            "ANULADO_IMPORT",
            "DUPLICADO",
            "CANCELADO",
            "RECHAZADO",
            "REVERSADO",
            "pendiente",
            "aplicado",
            "rechazado",
            "cancelado",
        )
        if e not in estados_validos:
            raise PagoValidationError(
                "estado",
                f"Estado no reconocido: {e!r}. Use valores de la tabla pagos (ej. PAGADO, PENDIENTE).",
            )
        return True

    def validar_datos_pago_completos(self, datos: dict) -> bool:
        """Valida que todos los datos requeridos estén presentes."""
        campos_requeridos = ["cliente_id", "monto"]
        
        for campo in campos_requeridos:
            if campo not in datos or datos[campo] is None:
                raise PagoValidationError(campo, f"Campo requerido")
        
        return True
