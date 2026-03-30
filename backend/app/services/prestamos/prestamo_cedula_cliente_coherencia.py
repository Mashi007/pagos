"""
Coherencia cedula prestamo <-> cliente (misma regla que auditoria cedula_cliente_vs_prestamo).

Al persistir, la cedula en `prestamos` debe coincidir con la del `clientes` enlazado
(normalizar_cedula_almacenamiento: trim + mayusculas). Se sincroniza desde el cliente
para no permitir altas/actualizaciones con desalineacion.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.utils.cedula_almacenamiento import normalizar_cedula_almacenamiento


class PrestamoCedulaClienteError(Exception):
    """Cliente sin cedula valida para APROBADO o cliente no encontrado."""


def _cedula_norm_presente(valor: Optional[str]) -> bool:
    return bool(normalizar_cedula_almacenamiento(valor))


def exigir_cliente_cedula_para_prestamo_aprobado(cliente: Cliente, estado_prestamo: str) -> None:
    """Si el prestamo queda APROBADO, el cliente debe tener cedula no vacia tras normalizar."""
    est = (estado_prestamo or "").strip().upper()
    if est != "APROBADO":
        return
    if not _cedula_norm_presente(cliente.cedula):
        raise PrestamoCedulaClienteError(
            "No se puede guardar un prestamo APROBADO: el cliente no tiene cedula registrada. "
            "Actualice la ficha del cliente antes de continuar."
        )


def sincronizar_cedula_prestamo_desde_cliente(prestamo: Prestamo, cliente: Cliente) -> None:
    """Asigna prestamo.cedula desde cliente (el modelo Prestamo normaliza al asignar)."""
    prestamo.cedula = cliente.cedula or ""


def asegurar_prestamo_alineado_con_cliente(
    db: Session,
    prestamo: Prestamo,
    *,
    cliente: Optional[Cliente] = None,
    estado_para_validar: Optional[str] = None,
) -> None:
    """
    Carga el cliente si hace falta, valida cedula si el estado es APROBADO y copia cedula al prestamo.
    """
    cli = cliente if cliente is not None else db.get(Cliente, prestamo.cliente_id)
    if cli is None:
        raise PrestamoCedulaClienteError("Cliente no encontrado para el prestamo.")
    est = estado_para_validar if estado_para_validar is not None else (prestamo.estado or "")
    exigir_cliente_cedula_para_prestamo_aprobado(cli, est)
    sincronizar_cedula_prestamo_desde_cliente(prestamo, cli)
