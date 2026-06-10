"""
Consultas sobre numero_documento.

Regla: el valor guardado en columna `numero_documento` es **único** en cartera. La única vía para dos pagos con el
mismo número “visible” del banco es que el **valor almacenado** difiera por **código** compuesto (`§CD:` vía
`compose_numero_documento_almacenado`), p. ej. revisión manual con token A####/P####.
"""

import re
from typing import Any, Iterator, Optional, Type

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.documento import normalize_documento
from app.models.pago import Pago
from app.models.pago_con_error import PagoConError
from app.utils.cedula_almacenamiento import (
    normalizar_cedula_almacenamiento,
    texto_cedula_comparable_bd,
)


def _candidatos_evasion_columna(column: Any, compact: str) -> Iterator[tuple[Any, str]]:
    """Consultas LIKE acotadas para encontrar posibles duplicados por sufijo/prefijo."""
    if not compact.isdigit() or len(compact) < 3:
        return
    if len(compact) <= 10:
        yield column.like(f"%{compact}"), "suffix"
    if len(compact) >= 10:
        yield column.like(f"{compact}%"), "prefix_new"
        yield column.like(f"{compact[:10]}%"), "prefix10"
        # Serial almacenado más corto (prefijo del nuevo): ej. 7400874101194 vs …119497
        if len(compact) > 10:
            yield column.like(f"{compact[:12]}%"), "prefix12"


def _candidatos_evasion_documento(model: Type[Any], compact: str) -> Iterator[tuple[Any, str]]:
    yield from _candidatos_evasion_columna(model.numero_documento, compact)


def _documento_colisiona_evasion_en_modelo(
    db: Session,
    model: Type[Any],
    numero_documento: Optional[str],
    *,
    exclude_id: Optional[int] = None,
    value_column: Any = None,
    extra_where: Optional[tuple[Any, ...]] = None,
) -> bool:
    from app.services.pagos_gmail.parse_campos_comprobante import (
        digitos_operacion_compacto,
        numeros_operacion_coinciden_o_evasion,
    )

    compact = digitos_operacion_compacto(numero_documento)
    if not compact:
        return False
    col = value_column if value_column is not None else model.numero_documento
    seen_ids: set[int] = set()
    for cond, _tag in _candidatos_evasion_columna(col, compact):
        q = select(model.id, col).where(cond).limit(150)
        if extra_where:
            q = q.where(*extra_where)
        if exclude_id is not None:
            q = q.where(model.id != exclude_id)
        for pid, stored in db.execute(q):
            ipid = int(pid)
            if ipid in seen_ids:
                continue
            seen_ids.add(ipid)
            if numeros_operacion_coinciden_o_evasion(compact, stored):
                return True
    return False


def documento_colisiona_evasion_registrado(
    db: Session,
    numero_documento: Optional[str],
    *,
    exclude_pago_id: Optional[int] = None,
    exclude_pago_con_error_id: Optional[int] = None,
    incluir_reportados_activos: bool = True,
) -> bool:
    """True si otro pago/pago_con_error (y opcionalmente reportado activo) coincide por evasión."""
    if _documento_colisiona_evasion_en_modelo(
        db, Pago, numero_documento, exclude_id=exclude_pago_id
    ):
        return True
    if _documento_colisiona_evasion_en_modelo(
        db,
        PagoConError,
        numero_documento,
        exclude_id=exclude_pago_con_error_id,
    ):
        return True
    if incluir_reportados_activos:
        from app.services.cobros.pago_reportado_documento import (
            numero_operacion_colisiona_reportado_activo,
        )

        if numero_operacion_colisiona_reportado_activo(db, numero_documento):
            return True
    return False


def cedulas_compatibles_adopcion_huerfano(
    cedula_a: Optional[str],
    cedula_b: Optional[str],
) -> bool:
    """Misma persona (V/E/J + dígitos, tolera ceros a la izquierda en el número)."""
    ca = texto_cedula_comparable_bd(cedula_a)
    cb = texto_cedula_comparable_bd(cedula_b)
    if not ca or not cb:
        return False
    if ca == cb:
        return True
    da = re.sub(r"\D", "", ca).lstrip("0") or "0"
    db = re.sub(r"\D", "", cb).lstrip("0") or "0"
    return len(da) >= 6 and len(db) >= 6 and da == db


def pago_huerfano_adoptable_por_documento(
    db: Session,
    numero_documento: Optional[str],
    *,
    prestamo_id_destino: int,
    cedula_cliente: Optional[str],
    exclude_pago_id: Optional[int] = None,
) -> Optional[int]:
    """
    Si el duplicado en cartera es un único `Pago` sin préstamo y la cédula cuadra,
    devuelve su id para asignar el crédito del formulario (evita segundo insert con mismo serial).
    """
    if not prestamo_id_destino or int(prestamo_id_destino) <= 0:
        return None
    pid, prid = primer_pago_cartera_por_documento(
        db, numero_documento, exclude_pago_id=exclude_pago_id
    )
    if pid is None or prid is not None:
        return None
    pago = db.get(Pago, int(pid))
    if pago is None:
        return None
    if not cedulas_compatibles_adopcion_huerfano(
        getattr(pago, "cedula_cliente", None), cedula_cliente
    ):
        return None
    return int(pid)


def primer_pago_cartera_por_documento(
    db: Session,
    numero_documento: Optional[str],
    *,
    exclude_pago_id: Optional[int] = None,
) -> tuple[Optional[int], Optional[int]]:
    """
    Primer `Pago` en cartera cuyo `numero_documento` normalizado coincide.

    Returns (pago_id, prestamo_id) o (None, None). `exclude_pago_id` excluye el
    pago en edición para detectar *otro* registro con el mismo documento.
    """
    num = normalize_documento(numero_documento)
    if not num:
        return None, None
    nu = num.upper()
    q = select(Pago.id, Pago.prestamo_id).where(func.upper(Pago.numero_documento) == nu)
    if exclude_pago_id is not None:
        q = q.where(Pago.id != exclude_pago_id)
    q = q.order_by(Pago.id.asc()).limit(1)
    row = db.execute(q).first()
    if row is not None:
        pid = int(row[0])
        prid = row[1]
        return pid, (int(prid) if prid is not None else None)
    pid, prid = _primer_pago_cartera_por_evasion(
        db, numero_documento, exclude_pago_id=exclude_pago_id
    )
    return pid, prid


def _primer_pago_cartera_por_evasion(
    db: Session,
    numero_documento: Optional[str],
    *,
    exclude_pago_id: Optional[int] = None,
) -> tuple[Optional[int], Optional[int]]:
    from app.services.pagos_gmail.parse_campos_comprobante import (
        digitos_operacion_compacto,
        numeros_operacion_coinciden_o_evasion,
    )

    compact = digitos_operacion_compacto(numero_documento)
    if not compact:
        return None, None
    seen_ids: set[int] = set()
    for cond, _tag in _candidatos_evasion_documento(Pago, compact):
        q = select(Pago.id, Pago.prestamo_id, Pago.numero_documento).where(cond).limit(150)
        if exclude_pago_id is not None:
            q = q.where(Pago.id != exclude_pago_id)
        for pid, prid, stored in db.execute(q):
            ipid = int(pid)
            if ipid in seen_ids:
                continue
            seen_ids.add(ipid)
            if numeros_operacion_coinciden_o_evasion(compact, stored):
                return ipid, (int(prid) if prid is not None else None)
    return None, None


def documento_ya_en_tabla_pagos(db: Session, numero_documento: Optional[str]) -> bool:
    """
    True si el documento normalizado ya existe en la tabla `pagos` (cartera operativa).

    Usado en listados de `pagos_con_errores` para marcar filas que no podrán moverse
    hasta desambiguar con código (misma regla que mover-a-pagos).
    """
    other_id, _ = primer_pago_cartera_por_documento(db, numero_documento)
    return other_id is not None


def numero_documento_ya_registrado(
    db: Session,
    numero_documento: Optional[str],
    *,
    exclude_pago_id: Optional[int] = None,
    exclude_pago_con_error_id: Optional[int] = None,
) -> bool:
    """
    True si el valor almacenado (comprobante + §CD: + código) ya existe en `pagos` o `pagos_con_errores`.

    Comparación **insensible a mayúsculas** sobre la columna completa, alineada con duplicados
    que solo diferían en casing (misma clave operativa para el usuario).

    `exclude_pago_con_error_id`: al validar o mover un registro en `pagos_con_errores`, excluir su propio id
    para no contar la fila actual como duplicado de sí misma.
    """
    num = normalize_documento(numero_documento)
    if not num:
        return False

    nu = num.upper()

    q = select(Pago.id).where(func.upper(Pago.numero_documento) == nu)
    if exclude_pago_id is not None:
        q = q.where(Pago.id != exclude_pago_id)
    if db.scalar(q) is not None:
        return True

    qe = select(PagoConError.id).where(func.upper(PagoConError.numero_documento) == nu)
    if exclude_pago_con_error_id is not None:
        qe = qe.where(PagoConError.id != exclude_pago_con_error_id)
    qe = qe.limit(1)
    if db.scalar(qe) is not None:
        return True

    return documento_colisiona_evasion_registrado(
        db,
        numero_documento,
        exclude_pago_id=exclude_pago_id,
        exclude_pago_con_error_id=exclude_pago_con_error_id,
    )


def pago_con_error_ya_cargado_estricto(
    db: Session,
    perr: PagoConError,
) -> Optional[int]:
    """
    Devuelve el `Pago.id` cargado en cartera que vuelve **redundante** a este `PagoConError`,
    o `None` si no hay coincidencia estricta.

    Criterio máximo rigor (acordado con negocio):
      1) mismo `numero_documento` canónico (case-insensitive sobre el valor almacenado completo)
      2) ese pago ya tiene aplicaciones en `cuota_pagos` (evita falsos positivos en cartera vacía)
      3) misma cédula del cliente (normalizada) y mismo `prestamo_id` cuando está informado en el PagoConError

    Si el PagoConError no tiene `prestamo_id`, exigimos al menos coincidencia de cédula y cuota_pagos
    aplicado al pago en cartera (no se asume préstamo arbitrario).
    """
    # Import local para evitar ciclos al cargar este módulo.
    from app.services.cuota_pago_integridad import pago_tiene_aplicaciones_cuotas

    if perr is None:
        return None

    num = normalize_documento(getattr(perr, "numero_documento", None))
    if not num:
        return None
    nu = num.upper()

    cedula_perr = normalizar_cedula_almacenamiento(
        getattr(perr, "cedula_cliente", None) or ""
    )
    prestamo_perr = getattr(perr, "prestamo_id", None)

    q = select(Pago.id, Pago.cedula_cliente, Pago.prestamo_id).where(
        func.upper(Pago.numero_documento) == nu
    )
    rows = db.execute(q).all()
    for row in rows:
        pago_id = int(row[0])
        cedula_pago = normalizar_cedula_almacenamiento(row[1] or "")
        prestamo_pago = row[2]
        # Cédula igual (cuando el PagoConError trae cédula).
        if cedula_perr and cedula_pago and cedula_perr != cedula_pago:
            continue
        # Préstamo igual cuando el PagoConError lo informa.
        if prestamo_perr is not None and prestamo_pago is not None:
            if int(prestamo_perr) != int(prestamo_pago):
                continue
        # Debe estar aplicado a cuotas: si no, no es "ya cargado" en sentido estricto.
        if not pago_tiene_aplicaciones_cuotas(db, pago_id):
            continue
        return pago_id
    return None
