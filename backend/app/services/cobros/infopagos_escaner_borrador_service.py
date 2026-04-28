"""
Alta y resolución de borradores del escáner Infopagos (tabla `infopagos_escaner_borrador`).
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Any, Dict, Optional, Tuple

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.infopagos_escaner_borrador import InfopagosEscanerBorrador
from app.models.pago_comprobante_imagen import PagoComprobanteImagen
from app.models.pago_reportado import PagoReportado
from app.services.pagos_gmail.comprobante_bd import persistir_comprobante_gmail_en_bd

logger = logging.getLogger(__name__)


def _nuevo_id_borrador() -> str:
    return uuid.uuid4().hex[:32]


def debe_persistir_borrador_escaneo(
    *,
    validacion_campos: Optional[str],
    validacion_reglas: Optional[str],
    duplicado_en_pagos: bool,
) -> bool:
    """
    Solo los escaneos que no superan validadores (o marcan duplicado en cartera)
    van a la tabla temporal; el resto sigue el flujo normal sin borrador en BD.
    """
    if duplicado_en_pagos:
        return True
    if (validacion_campos or "").strip():
        return True
    if (validacion_reglas or "").strip():
        return True
    return False


def crear_borrador_escaneo(
    db: Session,
    *,
    cliente_id: int,
    usuario_id: Optional[int],
    tipo_cedula: str,
    numero_cedula: str,
    cedula_normalizada: str,
    fuente_tasa_cambio: str,
    content: bytes,
    ctype: str,
    filename: str,
    payload: Dict[str, Any],
) -> Optional[str]:
    """
    Persiste comprobante en `pago_comprobante_imagen` e inserta fila borrador.
    Hace flush para obtener id; el caller hace commit en la misma transacción que el escáner.
    """
    stored = persistir_comprobante_gmail_en_bd(db, content, ctype)
    if not stored:
        return None
    img_id, _url = stored
    bid = _nuevo_id_borrador()
    row = InfopagosEscanerBorrador(
        id=bid,
        cliente_id=int(cliente_id),
        usuario_id=int(usuario_id) if usuario_id is not None else None,
        tipo_cedula=(tipo_cedula or "").strip().upper()[:2],
        numero_cedula=(numero_cedula or "").strip()[:13],
        cedula_normalizada=(cedula_normalizada or "").strip()[:20],
        fuente_tasa_cambio=(fuente_tasa_cambio or "")[:16] or None,
        comprobante_imagen_id=img_id,
        comprobante_nombre=(filename or "comprobante")[:255],
        payload_json=json.dumps(payload, ensure_ascii=False, default=str)[:8000],
        estado="borrador",
        pago_reportado_id=None,
    )
    db.add(row)
    db.flush()
    logger.info(
        "[INFOPAGOS_BORRADOR] creado id=%s cliente_id=%s cedula=%s",
        bid,
        cliente_id,
        cedula_normalizada[:12],
    )
    return bid


def cargar_borrador_y_bytes_comprobante(
    db: Session,
    borrador_id: str,
    *,
    cedula_lookup: str,
) -> Tuple[Optional[str], Optional[bytes], Optional[str], Optional[str], Optional[str]]:
    """
    Valida borrador activo y misma cédula que el envío.
    Devuelve (comprobante_imagen_id, content_bytes, filename, content_type, error).
    """
    bid = (borrador_id or "").strip()
    if not bid or len(bid) > 40:
        return None, None, None, None, "Borrador inválido."
    row = db.execute(
        select(InfopagosEscanerBorrador).where(InfopagosEscanerBorrador.id == bid)
    ).scalars().first()
    if row is None:
        return None, None, None, None, "Borrador no encontrado o ya utilizado."
    if (row.estado or "").strip().lower() != "borrador":
        return None, None, None, None, "Este borrador ya fue confirmado o no está disponible."
    if (row.cedula_normalizada or "").replace("-", "") != (cedula_lookup or "").replace("-", ""):
        return None, None, None, None, "La cédula del envío no coincide con el borrador escaneado."

    img = db.execute(
        select(PagoComprobanteImagen).where(
            PagoComprobanteImagen.id == row.comprobante_imagen_id
        )
    ).scalars().first()
    if img is None or not getattr(img, "imagen_data", None):
        return None, None, None, None, "El comprobante del borrador ya no está disponible."

    ctype = (getattr(img, "content_type", None) or "application/octet-stream").split(";")[0].strip()
    fn = (row.comprobante_nombre or "comprobante")[:255]
    data = bytes(img.imagen_data)
    img_id = str(row.comprobante_imagen_id or "").strip()
    return img_id, data, fn, ctype, None


def marcar_borrador_confirmado(
    db: Session,
    borrador_id: str,
    pago_reportado_id: int,
) -> None:
    db.execute(
        update(InfopagosEscanerBorrador)
        .where(
            InfopagosEscanerBorrador.id == borrador_id.strip(),
            InfopagosEscanerBorrador.estado == "borrador",
        )
        .values(estado="confirmado", pago_reportado_id=int(pago_reportado_id))
    )


def _imagen_sin_referencias(db: Session, imagen_id: str) -> bool:
    n_pr = (
        db.execute(
            select(func.count())
            .select_from(PagoReportado)
            .where(PagoReportado.comprobante_imagen_id == imagen_id)
        ).scalar()
        or 0
    )
    n_br = (
        db.execute(
            select(func.count())
            .select_from(InfopagosEscanerBorrador)
            .where(InfopagosEscanerBorrador.comprobante_imagen_id == imagen_id)
        ).scalar()
        or 0
    )
    return int(n_pr) == 0 and int(n_br) == 0


def listar_borradores_pendientes_usuario(
    db: Session, *, usuario_id: int, limit: int = 40
) -> list[dict[str, Any]]:
    lim = max(1, min(int(limit or 40), 100))
    rows = (
        db.execute(
            select(InfopagosEscanerBorrador, Cliente.nombres)
            .outerjoin(Cliente, Cliente.id == InfopagosEscanerBorrador.cliente_id)
            .where(
                InfopagosEscanerBorrador.estado == "borrador",
                InfopagosEscanerBorrador.usuario_id == int(usuario_id),
            )
            .order_by(InfopagosEscanerBorrador.created_at.desc())
            .limit(lim)
        )
        .all()
    )
    out: list[dict[str, Any]] = []
    for br, nombres_cli in rows:
        resumen = ""
        try:
            if br.payload_json:
                snap = json.loads(br.payload_json)
                resumen = (
                    (snap.get("validacion_reglas") or snap.get("validacion_campos") or "")
                    or ("Duplicado en cartera" if snap.get("duplicado_en_pagos") else "")
                )
        except Exception:
            resumen = ""
        resumen = (resumen or "Pendiente de revisión")[:200]
        out.append(
            {
                "id": br.id,
                "cedula_normalizada": br.cedula_normalizada,
                "tipo_cedula": br.tipo_cedula,
                "numero_cedula": br.numero_cedula,
                "comprobante_nombre": br.comprobante_nombre,
                "created_at": br.created_at.isoformat() if br.created_at else None,
                "resumen_validacion": resumen,
                "cliente_nombre": (nombres_cli or "").strip() or None,
            }
        )
    return out


def obtener_borrador_para_edicion(
    db: Session, *, borrador_id: str, usuario_id: int
) -> Tuple[Optional[dict[str, Any]], Optional[str]]:
    bid = (borrador_id or "").strip()
    if not bid:
        return None, "Borrador inválido."
    row = db.execute(
        select(InfopagosEscanerBorrador).where(InfopagosEscanerBorrador.id == bid)
    ).scalars().first()
    if row is None:
        return None, "Borrador no encontrado."
    if (row.estado or "").strip().lower() != "borrador":
        return None, "Este borrador ya no está disponible."
    if row.usuario_id is not None and int(row.usuario_id) != int(usuario_id):
        return None, "No tiene permiso para ver este borrador."

    cliente_nom = None
    if row.cliente_id is not None:
        c = db.execute(select(Cliente).where(Cliente.id == int(row.cliente_id))).scalars().first()
        if c is not None:
            cliente_nom = (c.nombres or "").strip() or None

    snap: Dict[str, Any] = {}
    if row.payload_json:
        try:
            snap = json.loads(row.payload_json)
        except Exception:
            snap = {}

    return (
        {
            "id": row.id,
            "tipo_cedula": row.tipo_cedula,
            "numero_cedula": row.numero_cedula,
            "cedula_normalizada": row.cedula_normalizada,
            "fuente_tasa_cambio": row.fuente_tasa_cambio or "euro",
            "comprobante_nombre": row.comprobante_nombre,
            "cliente_nombre": cliente_nom,
            "payload": snap,
        },
        None,
    )


def eliminar_borrador_escaneo(
    db: Session, *, borrador_id: str, usuario_id: int
) -> Tuple[bool, Optional[str]]:
    bid = (borrador_id or "").strip()
    if not bid:
        return False, "Borrador inválido."
    row = db.execute(
        select(InfopagosEscanerBorrador).where(InfopagosEscanerBorrador.id == bid)
    ).scalars().first()
    if row is None:
        return False, "Borrador no encontrado."
    if (row.estado or "").strip().lower() != "borrador":
        return False, "Solo se pueden eliminar borradores pendientes."
    if row.usuario_id is not None and int(row.usuario_id) != int(usuario_id):
        return False, "No tiene permiso para eliminar este borrador."

    img_id = (row.comprobante_imagen_id or "").strip()
    try:
        db.delete(row)
        db.flush()
        if img_id and _imagen_sin_referencias(db, img_id):
            db.execute(delete(PagoComprobanteImagen).where(PagoComprobanteImagen.id == img_id))
        db.commit()
    except Exception as e:
        db.rollback()
        logger.exception("[INFOPAGOS_BORRADOR] eliminar falló id=%s: %s", bid, e)
        return False, "No se pudo eliminar el borrador."

    logger.info("[INFOPAGOS_BORRADOR] eliminado id=%s usuario_id=%s", bid, usuario_id)
    return True, None
