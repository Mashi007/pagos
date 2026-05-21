"""Logica de negocio: casos de cobranza, acuerdos y cruces con pagos."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.models.cliente import Cliente
from app.models.cobranza import (
    CobranzaAcuerdo,
    CobranzaCaso,
    CobranzaImagen,
    CobranzaNotaAdjunto,
)
from app.models.pago import Pago
from app.models.prestamo import Prestamo
from app.schemas.cobranza import (
    ESTADOS_ACUERDO,
    ESTADOS_CASO,
    MOTIVOS_COBRANZA,
    CobranzaAcuerdoCreate,
    CobranzaAcuerdoOut,
    CobranzaAcuerdoUpdate,
    CobranzaBuscarResponse,
    CobranzaCasoCreate,
    CobranzaCasoOut,
    CobranzaCasoUpdate,
    CobranzaImagenMeta,
    CobranzaNotaAdjuntoMeta,
    CobranzaPrestamoResumen,
    CobranzaSesionNotaOut,
)
from app.services.cobranzas.imagen_service import url_cobranza_imagen_api
from app.services.cobranzas.nota_adjunto_service import persistir_adjuntos_nota
from app.services.notificacion_service import (
    contar_cuotas_atraso_por_prestamos,
    sum_saldo_pendiente_cuotas_tabla_amortizacion_ui,
)
from app.utils.cedula_almacenamiento import (
    expr_cedula_normalizada_para_comparar,
    normalizar_cedula_almacenamiento,
    texto_cedula_comparable_bd,
)


def _to_float(v) -> float:
    if v is None:
        return 0.0
    if isinstance(v, Decimal):
        return float(v)
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _texto_mensaje_acuerdo(a: CobranzaAcuerdo) -> str:
    msg = getattr(a, "mensaje", None) or a.notas or ""
    return str(msg).strip()


def _cantidad_acuerdo(a: CobranzaAcuerdo) -> Optional[float]:
    c = getattr(a, "cantidad", None)
    if c is not None:
        return _to_float(c)
    if a.monto_compromiso is not None:
        return _to_float(a.monto_compromiso)
    return None


def _moneda_acuerdo(a: CobranzaAcuerdo) -> str:
    m = (getattr(a, "moneda", None) or "USD").strip().upper()
    return m if m in ("USD", "BS") else "USD"


def _adjuntos_meta_acuerdo(db: Session, acuerdo_id: int) -> List[CobranzaNotaAdjuntoMeta]:
    try:
        rows = (
            db.query(CobranzaNotaAdjunto)
            .filter(CobranzaNotaAdjunto.acuerdo_id == acuerdo_id)
            .order_by(CobranzaNotaAdjunto.creado_en.asc())
            .all()
        )
    except ProgrammingError:
        return []
    return [
        CobranzaNotaAdjuntoMeta(
            id=r.id,
            nombre_archivo=r.nombre_archivo,
            content_type=r.content_type,
            creado_en=r.creado_en,
        )
        for r in rows
    ]


def _acuerdo_to_out(db: Session, a: CobranzaAcuerdo) -> CobranzaAcuerdoOut:
    cant = _cantidad_acuerdo(a)
    return CobranzaAcuerdoOut(
        id=a.id,
        caso_id=a.caso_id,
        fecha=a.fecha_acuerdo,
        mensaje=_texto_mensaje_acuerdo(a),
        cantidad=cant,
        moneda=_moneda_acuerdo(a),
        estado=a.estado,
        fecha_compromiso=a.fecha_compromiso,
        adjuntos=_adjuntos_meta_acuerdo(db, a.id),
        creado_en=a.creado_en,
        actualizado_en=a.actualizado_en,
    )


def _caso_activo_prestamo(db: Session, prestamo_id: int) -> Optional[CobranzaCaso]:
    return (
        db.query(CobranzaCaso)
        .filter(
            CobranzaCaso.prestamo_id == prestamo_id,
            CobranzaCaso.estado.in_(("ABIERTO", "EN_GESTION")),
        )
        .first()
    )


def _casos_abiertos_por_prestamo(db: Session, prestamo_ids: List[int]) -> Dict[int, CobranzaCaso]:
    if not prestamo_ids:
        return {}
    try:
        rows = (
            db.query(CobranzaCaso)
            .filter(
                CobranzaCaso.prestamo_id.in_(prestamo_ids),
                CobranzaCaso.estado.in_(("ABIERTO", "EN_GESTION")),
            )
            .all()
        )
    except ProgrammingError:
        return {}
    out: Dict[int, CobranzaCaso] = {}
    for c in rows:
        out[c.prestamo_id] = c
    return out


def buscar_por_cedula(db: Session, cedula_raw: str) -> CobranzaBuscarResponse:
    ced_norm = normalizar_cedula_almacenamiento(cedula_raw)
    if not ced_norm:
        raise HTTPException(status_code=400, detail="Cedula invalida.")
    ced_cmp = texto_cedula_comparable_bd(ced_norm)
    cliente = (
        db.query(Cliente)
        .filter(expr_cedula_normalizada_para_comparar(Cliente.cedula) == ced_cmp)
        .first()
    )
    q = db.query(Prestamo).filter(
        expr_cedula_normalizada_para_comparar(Prestamo.cedula) == ced_cmp,
        ~Prestamo.estado.in_(("DESISTIMIENTO",)),
    )
    if cliente:
        q = q.filter(
            or_(
                Prestamo.cliente_id == cliente.id,
                expr_cedula_normalizada_para_comparar(Prestamo.cedula) == ced_cmp,
            )
        )
    prestamos = q.order_by(Prestamo.id.desc()).limit(50).all()
    pids = [p.id for p in prestamos]
    saldos = sum_saldo_pendiente_cuotas_tabla_amortizacion_ui(db, pids)
    atrasos = contar_cuotas_atraso_por_prestamos(db, pids)
    casos_map = _casos_abiertos_por_prestamo(db, pids)
    items: List[CobranzaPrestamoResumen] = []
    for p in prestamos:
        caso = casos_map.get(p.id)
        items.append(
            CobranzaPrestamoResumen(
                id=p.id,
                cliente_id=p.cliente_id,
                cedula=p.cedula or ced_norm,
                nombres=p.nombres,
                total_financiamiento=_to_float(p.total_financiamiento),
                saldo_pendiente=saldos.get(p.id, 0.0),
                modalidad_pago=p.modalidad_pago,
                numero_cuotas=p.numero_cuotas,
                estado=p.estado or "",
                cuotas_atrasadas=atrasos.get(p.id, 0),
                caso_id=caso.id if caso else None,
                caso_estado=caso.estado if caso else None,
                caso_motivo=caso.motivo if caso else None,
            )
        )
    nombres = None
    if cliente:
        nombres = cliente.nombres
    elif prestamos:
        nombres = prestamos[0].nombres
    return CobranzaBuscarResponse(
        cedula=ced_norm,
        cliente_id=cliente.id if cliente else (prestamos[0].cliente_id if prestamos else None),
        nombres=nombres,
        prestamos=items,
    )


def _prestamo_o_404(db: Session, prestamo_id: int) -> Prestamo:
    p = db.get(Prestamo, prestamo_id)
    if not p:
        raise HTTPException(status_code=404, detail="Prestamo no encontrado.")
    return p


def _caso_o_404(db: Session, caso_id: int) -> CobranzaCaso:
    try:
        c = db.get(CobranzaCaso, caso_id)
    except ProgrammingError:
        raise HTTPException(
            status_code=503,
            detail="Tablas de cobranzas no disponibles. Ejecute migracion_cobranzas_modulo.sql.",
        )
    if not c:
        raise HTTPException(status_code=404, detail="Caso de cobranza no encontrado.")
    return c


def _snapshot_prestamo(db: Session, prestamo: Prestamo) -> tuple[float, int]:
    saldos = sum_saldo_pendiente_cuotas_tabla_amortizacion_ui(db, [prestamo.id])
    atrasos = contar_cuotas_atraso_por_prestamos(db, [prestamo.id])
    return saldos.get(prestamo.id, 0.0), atrasos.get(prestamo.id, 0)


def crear_caso(
    db: Session, body: CobranzaCasoCreate, user_id: Optional[int]
) -> CobranzaCasoOut:
    if body.motivo not in MOTIVOS_COBRANZA:
        raise HTTPException(status_code=400, detail="Motivo invalido.")
    prestamo = _prestamo_o_404(db, body.prestamo_id)
    existente = (
        db.query(CobranzaCaso)
        .filter(
            CobranzaCaso.prestamo_id == prestamo.id,
            CobranzaCaso.estado.in_(("ABIERTO", "EN_GESTION")),
        )
        .first()
    )
    if existente:
        return obtener_caso_detalle(db, existente.id, sincronizar_acuerdos=True)
    saldo, atraso = _snapshot_prestamo(db, prestamo)
    caso = CobranzaCaso(
        prestamo_id=prestamo.id,
        cliente_id=prestamo.cliente_id,
        cedula=prestamo.cedula or "",
        nombres=prestamo.nombres,
        motivo=body.motivo,
        estado="ABIERTO",
        observaciones=body.observaciones,
        monto_financiamiento=prestamo.total_financiamiento,
        saldo_pendiente_snapshot=saldo,
        cuotas_atrasadas_snapshot=atraso,
        user_id=user_id,
    )
    db.add(caso)
    db.commit()
    db.refresh(caso)
    return obtener_caso_detalle(db, caso.id, sincronizar_acuerdos=False)


def actualizar_caso(
    db: Session, caso_id: int, body: CobranzaCasoUpdate
) -> CobranzaCasoOut:
    caso = _caso_o_404(db, caso_id)
    if body.motivo is not None:
        if body.motivo not in MOTIVOS_COBRANZA:
            raise HTTPException(status_code=400, detail="Motivo invalido.")
        caso.motivo = body.motivo
    if body.estado is not None:
        if body.estado not in ESTADOS_CASO:
            raise HTTPException(status_code=400, detail="Estado de caso invalido.")
        caso.estado = body.estado
    if body.observaciones is not None:
        caso.observaciones = body.observaciones
    db.commit()
    db.refresh(caso)
    return obtener_caso_detalle(db, caso.id, sincronizar_acuerdos=True)


def _hay_pago_despues_de(
    db: Session, prestamo_id: int, desde: date
) -> bool:
    """True si existe pago del prestamo con fecha >= desde (cruce para cumplimiento)."""
    dt_desde = datetime.combine(desde, datetime.min.time())
    q = (
        select(func.count())
        .select_from(Pago)
        .where(
            Pago.prestamo_id == prestamo_id,
            Pago.fecha_pago >= dt_desde,
            Pago.monto_pagado > 0,
        )
    )
    estados_excl = ("ANULADO", "RECHAZADO", "CANCELADO")
    q = q.where(
        or_(
            Pago.estado.is_(None),
            ~func.upper(func.trim(Pago.estado)).in_(estados_excl),
        )
    )
    n = db.execute(q).scalar() or 0
    return int(n) > 0


def _estado_acuerdo_automatico(
    db: Session,
    prestamo_id: int,
    fecha_compromiso: Optional[date],
    fecha_acuerdo: date,
) -> str:
    ref = fecha_compromiso or fecha_acuerdo
    if _hay_pago_despues_de(db, prestamo_id, ref):
        return "CUMPLIDO"
    hoy = date.today()
    if ref < hoy:
        return "INCUMPLIDO"
    return "PENDIENTE"


def sincronizar_estados_acuerdos(db: Session, caso: CobranzaCaso) -> None:
    acuerdos = (
        db.query(CobranzaAcuerdo)
        .filter(CobranzaAcuerdo.caso_id == caso.id)
        .order_by(CobranzaAcuerdo.fecha_acuerdo.desc(), CobranzaAcuerdo.id.desc())
        .all()
    )
    changed = False
    for a in acuerdos:
        nuevo = _estado_acuerdo_automatico(
            db, caso.prestamo_id, a.fecha_compromiso, a.fecha_acuerdo
        )
        if a.estado != nuevo:
            a.estado = nuevo
            changed = True
    if changed:
        db.commit()


def obtener_caso_detalle(
    db: Session, caso_id: int, *, sincronizar_acuerdos: bool = True
) -> CobranzaCasoOut:
    caso = _caso_o_404(db, caso_id)
    if sincronizar_acuerdos:
        sincronizar_estados_acuerdos(db, caso)
        db.refresh(caso)
    prestamo = db.get(Prestamo, caso.prestamo_id)
    saldo_act, atraso_act = (
        _snapshot_prestamo(db, prestamo) if prestamo else (0.0, 0)
    )
    imagenes = (
        db.query(CobranzaImagen)
        .filter(CobranzaImagen.caso_id == caso.id)
        .order_by(CobranzaImagen.creado_en.desc())
        .all()
    )
    acuerdos = (
        db.query(CobranzaAcuerdo)
        .filter(CobranzaAcuerdo.caso_id == caso.id)
        .order_by(CobranzaAcuerdo.fecha_acuerdo.desc(), CobranzaAcuerdo.id.desc())
        .all()
    )
    return CobranzaCasoOut(
        id=caso.id,
        prestamo_id=caso.prestamo_id,
        cliente_id=caso.cliente_id,
        cedula=caso.cedula,
        nombres=caso.nombres,
        motivo=caso.motivo,
        estado=caso.estado,
        observaciones=caso.observaciones,
        monto_financiamiento=_to_float(caso.monto_financiamiento),
        saldo_pendiente_snapshot=_to_float(caso.saldo_pendiente_snapshot),
        cuotas_atrasadas_snapshot=caso.cuotas_atrasadas_snapshot,
        creado_en=caso.creado_en,
        actualizado_en=caso.actualizado_en,
        saldo_pendiente_actual=saldo_act,
        cuotas_atrasadas_actual=atraso_act,
        total_financiamiento_actual=_to_float(prestamo.total_financiamiento)
        if prestamo
        else _to_float(caso.monto_financiamiento),
        modalidad_pago=prestamo.modalidad_pago if prestamo else None,
        numero_cuotas=prestamo.numero_cuotas if prestamo else None,
        prestamo_estado=prestamo.estado if prestamo else None,
        imagenes=[
            CobranzaImagenMeta(
                id=img.id,
                descripcion=img.descripcion,
                content_type=img.content_type,
                creado_en=img.creado_en,
            )
            for img in imagenes
        ],
        acuerdos=[_acuerdo_to_out(db, a) for a in acuerdos],
    )


MENSAJE_SESION_ABIERTA = "Sesion de negociacion abierta."


def _asegurar_caso_gestion(
    db: Session,
    prestamo: Prestamo,
    motivo: str,
    user_id: Optional[int],
) -> CobranzaCaso:
    if motivo not in MOTIVOS_COBRANZA:
        raise HTTPException(status_code=400, detail="Motivo invalido.")
    caso = _caso_activo_prestamo(db, prestamo.id)
    if not caso:
        saldo, atraso = _snapshot_prestamo(db, prestamo)
        caso = CobranzaCaso(
            prestamo_id=prestamo.id,
            cliente_id=prestamo.cliente_id,
            cedula=prestamo.cedula or "",
            nombres=prestamo.nombres,
            motivo=motivo,
            estado="EN_GESTION",
            monto_financiamiento=prestamo.total_financiamiento,
            saldo_pendiente_snapshot=saldo,
            cuotas_atrasadas_snapshot=atraso,
            user_id=user_id,
        )
        db.add(caso)
        db.flush()
    elif caso.estado == "ABIERTO":
        caso.estado = "EN_GESTION"
    return caso


def _crear_acuerdo_nota(
    db: Session,
    caso: CobranzaCaso,
    prestamo_id: int,
    *,
    mensaje: str,
    cantidad: Optional[float],
    moneda: str,
    user_id: Optional[int],
) -> CobranzaAcuerdo:
    hoy = date.today()
    estado_ini = _estado_acuerdo_automatico(db, prestamo_id, None, hoy)
    acuerdo = CobranzaAcuerdo(
        caso_id=caso.id,
        fecha_acuerdo=hoy,
        fecha_compromiso=None,
        mensaje=mensaje,
        cantidad=cantidad,
        moneda=moneda,
        notas=mensaje,
        estado=estado_ini,
        monto_compromiso=cantidad,
        user_id=user_id,
    )
    db.add(acuerdo)
    db.flush()
    return acuerdo


def abrir_sesion_nota(
    db: Session,
    *,
    prestamo_id: int,
    motivo: str = "OTRO",
    user_id: Optional[int] = None,
) -> CobranzaSesionNotaOut:
    """Al abrir negociacion: nueva fila en cobranza_acuerdos (fecha = hoy)."""
    prestamo = _prestamo_o_404(db, prestamo_id)
    caso = _asegurar_caso_gestion(db, prestamo, motivo, user_id)
    acuerdo = _crear_acuerdo_nota(
        db,
        caso,
        prestamo.id,
        mensaje=MENSAJE_SESION_ABIERTA,
        cantidad=None,
        moneda="USD",
        user_id=user_id,
    )
    db.commit()
    detalle = obtener_caso_detalle(db, caso.id, sincronizar_acuerdos=True)
    return CobranzaSesionNotaOut(nota_id=acuerdo.id, caso=detalle)


def guardar_nota_sesion(
    db: Session,
    acuerdo_id: int,
    *,
    mensaje: str,
    cantidad: Optional[float],
    moneda: str,
    archivos: Optional[List[tuple]] = None,
    user_id: Optional[int] = None,
) -> CobranzaCasoOut:
    """
    Completa la nota de la sesion: fecha = hoy, mensaje/monto y adjuntos en BD.
    archivos: [(bytes, content_type, filename), ...] -> cobranza_nota_adjuntos
    """
    texto = (mensaje or "").strip()
    if not texto:
        raise HTTPException(status_code=400, detail="El mensaje es obligatorio.")
    mon = (moneda or "USD").strip().upper()
    if mon not in ("USD", "BS"):
        raise HTTPException(status_code=400, detail="Moneda debe ser USD o BS.")

    acuerdo = db.get(CobranzaAcuerdo, acuerdo_id)
    if not acuerdo:
        raise HTTPException(status_code=404, detail="Nota no encontrada.")
    caso = _caso_o_404(db, acuerdo.caso_id)
    hoy = date.today()
    acuerdo.fecha_acuerdo = hoy
    acuerdo.mensaje = texto
    acuerdo.notas = texto
    acuerdo.cantidad = cantidad
    acuerdo.monto_compromiso = cantidad
    acuerdo.moneda = mon
    acuerdo.estado = _estado_acuerdo_automatico(
        db, caso.prestamo_id, acuerdo.fecha_compromiso, hoy
    )
    if archivos:
        persistir_adjuntos_nota(db, acuerdo.id, archivos, user_id=user_id)
    db.commit()
    return obtener_caso_detalle(db, caso.id, sincronizar_acuerdos=True)


def crear_nota(
    db: Session,
    *,
    prestamo_id: int,
    mensaje: str,
    cantidad: Optional[float],
    moneda: str,
    motivo: str = "OTRO",
    archivos: Optional[List[tuple]] = None,
    user_id: Optional[int] = None,
) -> CobranzaCasoOut:
    """
    Nueva nota del dia en un solo paso: crea caso si no existe, fecha = hoy, hasta 3 adjuntos.
    archivos: [(bytes, content_type, filename), ...]
    """
    texto = (mensaje or "").strip()
    if not texto:
        raise HTTPException(status_code=400, detail="El mensaje es obligatorio.")
    mon = (moneda or "USD").strip().upper()
    if mon not in ("USD", "BS"):
        raise HTTPException(status_code=400, detail="Moneda debe ser USD o BS.")

    prestamo = _prestamo_o_404(db, prestamo_id)
    caso = _asegurar_caso_gestion(db, prestamo, motivo, user_id)
    acuerdo = _crear_acuerdo_nota(
        db,
        caso,
        prestamo.id,
        mensaje=texto,
        cantidad=cantidad,
        moneda=mon,
        user_id=user_id,
    )

    if archivos:
        persistir_adjuntos_nota(db, acuerdo.id, archivos, user_id=user_id)

    db.commit()
    return obtener_caso_detalle(db, caso.id, sincronizar_acuerdos=True)


def crear_acuerdo(
    db: Session,
    caso_id: int,
    body: CobranzaAcuerdoCreate,
    user_id: Optional[int],
) -> CobranzaAcuerdoOut:
    caso = _caso_o_404(db, caso_id)
    hoy = date.today()
    fecha_nota = body.fecha if body.fecha else hoy
    estado_ini = _estado_acuerdo_automatico(
        db, caso.prestamo_id, body.fecha_compromiso, fecha_nota
    )
    texto = body.mensaje.strip()
    cant = body.cantidad
    mon = body.moneda
    acuerdo = CobranzaAcuerdo(
        caso_id=caso.id,
        fecha_acuerdo=fecha_nota,
        fecha_compromiso=body.fecha_compromiso,
        mensaje=texto,
        cantidad=cant,
        moneda=mon,
        notas=texto,
        estado=estado_ini,
        monto_compromiso=cant,
        user_id=user_id,
    )
    db.add(acuerdo)
    if caso.estado == "ABIERTO":
        caso.estado = "EN_GESTION"
    db.commit()
    db.refresh(acuerdo)
    return _acuerdo_to_out(db, acuerdo)


def actualizar_acuerdo(
    db: Session,
    caso_id: int,
    acuerdo_id: int,
    body: CobranzaAcuerdoUpdate,
) -> CobranzaAcuerdoOut:
    caso = _caso_o_404(db, caso_id)
    acuerdo = (
        db.query(CobranzaAcuerdo)
        .filter(
            CobranzaAcuerdo.id == acuerdo_id,
            CobranzaAcuerdo.caso_id == caso.id,
        )
        .first()
    )
    if not acuerdo:
        raise HTTPException(status_code=404, detail="Acuerdo no encontrado.")
    if body.fecha is not None:
        acuerdo.fecha_acuerdo = body.fecha
    if body.fecha_compromiso is not None:
        acuerdo.fecha_compromiso = body.fecha_compromiso
    if body.mensaje is not None:
        acuerdo.mensaje = body.mensaje.strip()
        acuerdo.notas = acuerdo.mensaje
    if body.cantidad is not None:
        acuerdo.cantidad = body.cantidad
        acuerdo.monto_compromiso = body.cantidad
    if body.moneda is not None:
        acuerdo.moneda = body.moneda
    if body.estado is not None:
        if body.estado not in ESTADOS_ACUERDO:
            raise HTTPException(status_code=400, detail="Estado de acuerdo invalido.")
        acuerdo.estado = body.estado
    else:
        acuerdo.estado = _estado_acuerdo_automatico(
            db,
            caso.prestamo_id,
            acuerdo.fecha_compromiso,
            acuerdo.fecha_acuerdo,
        )
    db.commit()
    db.refresh(acuerdo)
    return _acuerdo_to_out(db, acuerdo)
