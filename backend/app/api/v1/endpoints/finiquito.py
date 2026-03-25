"""
Finiquito: casos materializados (job 02:00), portal publico OTP, bandejas, admin.
"""
from __future__ import annotations

import logging
import random
import string
from datetime import datetime, timedelta
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import (
    get_finiquito_usuario_acceso,
    require_administrador,
)
from app.core.email import mask_email_for_log, send_email
from app.core.email_config_holder import get_email_activo_servicio
from app.core.security import create_access_token
from app.models.cuota import Cuota
from app.models.pago import Pago
from app.models.finiquito import (
    FiniquitoCaso,
    FiniquitoEstadoHistorial,
    FiniquitoLoginCodigo,
    FiniquitoUsuarioAcceso,
)
from app.models.prestamo import Prestamo
from app.schemas.auth import UserResponse
from app.schemas.finiquito import (
    FiniquitoCasoListaResponse,
    FiniquitoCasoOut,
    FiniquitoDetalleResponse,
    FiniquitoPatchEstadoRequest,
    FiniquitoPatchEstadoResponse,
    FiniquitoRegistroRequest,
    FiniquitoRegistroResponse,
    FiniquitoSolicitarCodigoRequest,
    FiniquitoSolicitarCodigoResponse,
    FiniquitoVerificarCodigoRequest,
    FiniquitoVerificarCodigoResponse,
)
from app.utils.cedula_almacenamiento import normalizar_cedula_almacenamiento

logger = logging.getLogger(__name__)

router = APIRouter()

ESTADOS_VALIDOS = frozenset({"REVISION", "ACEPTADO", "RECHAZADO"})
CODIGO_EXPIRA_MINUTES = 120


def _generar_codigo_6() -> str:
    return "".join(random.choices(string.digits, k=6))


def _map_ultima_fecha_pago_por_prestamo(db: Session, prestamo_ids: List[int]) -> dict[int, Any]:
    """MAX(fecha_pago) en pagos agrupado por prestamo_id."""
    seen: set[int] = set()
    uniq: List[int] = []
    for i in prestamo_ids:
        if i is None:
            continue
        ii = int(i)
        if ii not in seen:
            seen.add(ii)
            uniq.append(ii)
    if not uniq:
        return {}
    rows = (
        db.query(Pago.prestamo_id, func.max(Pago.fecha_pago).label("mx"))
        .filter(Pago.prestamo_id.in_(uniq))
        .group_by(Pago.prestamo_id)
        .all()
    )
    out: dict[int, Any] = {}
    for r in rows:
        if r.prestamo_id is not None and r.mx is not None:
            out[int(r.prestamo_id)] = r.mx
    return out


def _caso_to_out(c: FiniquitoCaso, ultima_fecha_pago: Optional[Any] = None) -> FiniquitoCasoOut:
    ufp: Optional[str] = None
    if ultima_fecha_pago is not None:
        ufp = (
            ultima_fecha_pago.isoformat()
            if hasattr(ultima_fecha_pago, "isoformat")
            else str(ultima_fecha_pago)
        )
    return FiniquitoCasoOut(
        id=c.id,
        prestamo_id=c.prestamo_id,
        cliente_id=c.cliente_id,
        cedula=c.cedula or "",
        total_financiamiento=str(c.total_financiamiento),
        sum_total_pagado=str(c.sum_total_pagado),
        estado=c.estado,
        ultimo_refresh_utc=c.ultimo_refresh_utc.isoformat() if c.ultimo_refresh_utc else None,
        ultima_fecha_pago=ufp,
    )


def _registrar_historial(
    db: Session,
    *,
    caso: FiniquitoCaso,
    estado_anterior: Optional[str],
    estado_nuevo: str,
    actor_tipo: str,
    user_id: Optional[int] = None,
    finiquito_usuario_id: Optional[int] = None,
) -> None:
    db.add(
        FiniquitoEstadoHistorial(
            caso_id=caso.id,
            estado_anterior=estado_anterior,
            estado_nuevo=estado_nuevo,
            user_id=user_id,
            finiquito_usuario_id=finiquito_usuario_id,
            actor_tipo=actor_tipo,
        )
    )


def _num_str(v: Any) -> Optional[str]:
    if v is None:
        return None
    return str(v)


def _dt_iso(v: Any) -> Optional[str]:
    if v is None:
        return None
    if hasattr(v, "isoformat"):
        try:
            return v.isoformat()
        except Exception:
            return str(v)
    return str(v)


def _prestamo_caso_completo(p: Prestamo) -> dict[str, Any]:
    """Campos ampliados del préstamo vinculado al caso (lectura finiquito)."""
    return {
        "id": p.id,
        "cliente_id": p.cliente_id,
        "cedula": p.cedula,
        "nombres": p.nombres,
        "total_financiamiento": _num_str(p.total_financiamiento),
        "fecha_requerimiento": _dt_iso(p.fecha_requerimiento),
        "modalidad_pago": p.modalidad_pago,
        "numero_cuotas": p.numero_cuotas,
        "cuota_periodo": _num_str(p.cuota_periodo),
        "tasa_interes": _num_str(p.tasa_interes),
        "fecha_base_calculo": _dt_iso(p.fecha_base_calculo),
        "producto": p.producto,
        "estado": p.estado,
        "fecha_liquidado": _dt_iso(p.fecha_liquidado),
        "usuario_proponente": p.usuario_proponente,
        "usuario_aprobador": p.usuario_aprobador,
        "observaciones": p.observaciones,
        "fecha_registro": _dt_iso(p.fecha_registro),
        "fecha_aprobacion": _dt_iso(p.fecha_aprobacion),
        "fecha_actualizacion": _dt_iso(p.fecha_actualizacion),
        "concesionario": p.concesionario,
        "analista": p.analista,
        "modelo_vehiculo": p.modelo_vehiculo,
        "usuario_autoriza": p.usuario_autoriza,
        "valor_activo": _num_str(p.valor_activo),
        "requiere_revision": bool(p.requiere_revision)
        if p.requiere_revision is not None
        else False,
        "concesionario_id": p.concesionario_id,
        "analista_id": p.analista_id,
        "modelo_vehiculo_id": p.modelo_vehiculo_id,
    }


def _cuota_to_dict(cu: Cuota) -> dict[str, Any]:
    return {
        "id": cu.id,
        "prestamo_id": cu.prestamo_id,
        "numero_cuota": cu.numero_cuota,
        "fecha_vencimiento": _dt_iso(cu.fecha_vencimiento),
        "fecha_pago": _dt_iso(cu.fecha_pago),
        "monto_cuota": _num_str(cu.monto),
        "saldo_capital_inicial": _num_str(cu.saldo_capital_inicial),
        "saldo_capital_final": _num_str(cu.saldo_capital_final),
        "monto_capital": _num_str(cu.monto_capital),
        "monto_interes": _num_str(cu.monto_interes),
        "total_pagado": _num_str(cu.total_pagado),
        "dias_mora": cu.dias_mora,
        "dias_morosidad": cu.dias_morosidad,
        "estado": cu.estado,
        "observaciones": cu.observaciones,
        "pago_id": cu.pago_id,
        "es_cuota_especial": cu.es_cuota_especial,
        "cliente_id": cu.cliente_id,
    }


def _build_revision_datos_payload(db: Session, caso: FiniquitoCaso) -> dict[str, Any]:
    """
    Datos de revisión: préstamo del caso (completo), plan de cuotas, listados
    /prestamos y /pagos por cédula; pagos sin filtrar por conciliado (tope API 100).
    """
    from app.api.v1.endpoints.pagos import listar_pagos
    from app.api.v1.endpoints.prestamos import listar_prestamos

    cedula = (caso.cedula or "").strip()
    prestamos_payload = listar_prestamos(
        page=1,
        per_page=100,
        cliente_id=None,
        estado=None,
        analista=None,
        concesionario=None,
        cedula=cedula,
        fecha_inicio=None,
        fecha_fin=None,
        requiere_revision=None,
        modelo=None,
        search=None,
        db=db,
    )
    pagos_payload = listar_pagos(
        page=1,
        per_page=100,
        cedula=cedula,
        estado=None,
        fecha_desde=None,
        fecha_hasta=None,
        analista=None,
        conciliado=None,
        sin_prestamo=None,
        db=db,
    )

    prestamo_caso: Optional[dict[str, Any]] = None
    cuotas_caso: List[dict[str, Any]] = []
    p = db.query(Prestamo).filter(Prestamo.id == caso.prestamo_id).first()
    if p:
        prestamo_caso = _prestamo_caso_completo(p)
        cuotas = (
            db.query(Cuota)
            .filter(Cuota.prestamo_id == caso.prestamo_id)
            .order_by(Cuota.numero_cuota.asc())
            .all()
        )
        cuotas_caso = [_cuota_to_dict(cu) for cu in cuotas]

    return {
        "caso_id": caso.id,
        "prestamo_id_finiquito": caso.prestamo_id,
        "cedula": cedula,
        "prestamo_caso": prestamo_caso,
        "cuotas_caso": cuotas_caso,
        "prestamos": prestamos_payload,
        "pagos": pagos_payload,
    }


@router.post("/public/registro", response_model=FiniquitoRegistroResponse)
def finiquito_public_registro(body: FiniquitoRegistroRequest, db: Session = Depends(get_db)):
    """Primera vez: cedula + email unicos en el modulo Finiquito."""
    cedula = normalizar_cedula_almacenamiento(body.cedula)
    email = (body.email or "").lower().strip()
    if not cedula or not email:
        raise HTTPException(status_code=400, detail="Cedula y correo son obligatorios.")

    por_cedula = db.query(FiniquitoUsuarioAcceso).filter(FiniquitoUsuarioAcceso.cedula == cedula).first()
    por_email = db.query(FiniquitoUsuarioAcceso).filter(FiniquitoUsuarioAcceso.email == email).first()

    if por_cedula and por_cedula.email != email:
        raise HTTPException(
            status_code=409,
            detail="Esta cedula ya esta registrada con otro correo.",
        )
    if por_email and por_email.cedula != cedula:
        raise HTTPException(
            status_code=409,
            detail="Este correo ya esta registrado con otra cedula.",
        )
    if por_cedula:
        return FiniquitoRegistroResponse(ok=True, message="Ya estaba registrado. Solicite codigo para ingresar.")

    db.add(FiniquitoUsuarioAcceso(cedula=cedula, email=email, is_active=True))
    db.commit()
    return FiniquitoRegistroResponse(ok=True, message="Registro exitoso. Solicite codigo para ingresar.")


@router.post("/public/solicitar-codigo", response_model=FiniquitoSolicitarCodigoResponse)
def finiquito_public_solicitar_codigo(
    body: FiniquitoSolicitarCodigoRequest,
    db: Session = Depends(get_db),
):
    cedula = normalizar_cedula_almacenamiento(body.cedula)
    email = (body.email or "").lower().strip()
    if not cedula or not email:
        raise HTTPException(status_code=400, detail="Cedula y correo son obligatorios.")

    u = (
        db.query(FiniquitoUsuarioAcceso)
        .filter(
            FiniquitoUsuarioAcceso.cedula == cedula,
            FiniquitoUsuarioAcceso.email == email,
            FiniquitoUsuarioAcceso.is_active.is_(True),
        )
        .first()
    )
    if not u:
        return FiniquitoSolicitarCodigoResponse(
            ok=True,
            message="Si los datos son correctos, recibira un codigo en su correo.",
        )

    now_utc = datetime.utcnow()
    codigo = _generar_codigo_6()
    expira = now_utc + timedelta(minutes=CODIGO_EXPIRA_MINUTES)
    db.add(
        FiniquitoLoginCodigo(
            finiquito_usuario_id=u.id,
            codigo=codigo,
            expira_en=expira,
            usado=False,
            creado_en=now_utc,
        )
    )

    asunto = "[RapiCredit] Codigo de acceso Finiquito"
    cuerpo = (
        f"Su codigo de acceso al portal Finiquito es: {codigo}\n\n"
        f"Valido por {CODIGO_EXPIRA_MINUTES} minutos.\n"
        "Si usted no solicito este codigo, ignore este mensaje."
    )

    # Misma cuenta SMTP y flags que estado de cuenta publico: sin esto, modo pruebas
    # redirige el OTP al correo de pruebas y el colaborador no recibe nada.
    if not get_email_activo_servicio("estado_cuenta"):
        db.rollback()
        logger.warning(
            "finiquito solicitar-codigo: no enviado (email_activo master off o "
            "servicio 'Estado de cuenta' desactivado en Configuracion > Email)."
        )
        return FiniquitoSolicitarCodigoResponse(
            ok=True,
            message="Si los datos son correctos, recibira un codigo en su correo.",
        )

    ok_send, err_send = send_email(
        [email],
        asunto,
        cuerpo,
        servicio="estado_cuenta",
        respetar_destinos_manuales=True,
    )
    if not ok_send:
        db.rollback()
        logger.warning(
            "finiquito solicitar-codigo: SMTP fallo para %s: %s",
            mask_email_for_log(email),
            err_send or "send_email devolvio False",
        )
        return FiniquitoSolicitarCodigoResponse(
            ok=True,
            message="Si los datos son correctos, recibira un codigo en su correo.",
        )

    db.commit()
    logger.info(
        "finiquito solicitar-codigo: enviado ok dest=%s",
        mask_email_for_log(email),
    )
    return FiniquitoSolicitarCodigoResponse(
        ok=True,
        message="Si los datos son correctos, recibira un codigo en su correo.",
    )


@router.post("/public/verificar-codigo", response_model=FiniquitoVerificarCodigoResponse)
def finiquito_public_verificar_codigo(
    body: FiniquitoVerificarCodigoRequest,
    db: Session = Depends(get_db),
):
    cedula = normalizar_cedula_almacenamiento(body.cedula)
    email = (body.email or "").lower().strip()
    codigo = (body.codigo or "").strip()
    if not cedula or not email or not codigo:
        return FiniquitoVerificarCodigoResponse(ok=False, error="Cedula, correo y codigo son obligatorios.")

    u = (
        db.query(FiniquitoUsuarioAcceso)
        .filter(
            FiniquitoUsuarioAcceso.cedula == cedula,
            FiniquitoUsuarioAcceso.email == email,
            FiniquitoUsuarioAcceso.is_active.is_(True),
        )
        .first()
    )
    if not u:
        return FiniquitoVerificarCodigoResponse(ok=False, error="Credenciales invalidas.")

    now_utc = datetime.utcnow()
    row = (
        db.query(FiniquitoLoginCodigo)
        .filter(
            FiniquitoLoginCodigo.finiquito_usuario_id == u.id,
            FiniquitoLoginCodigo.codigo == codigo,
            FiniquitoLoginCodigo.usado.is_(False),
            FiniquitoLoginCodigo.expira_en > now_utc,
        )
        .order_by(FiniquitoLoginCodigo.creado_en.desc())
        .first()
    )
    if not row:
        return FiniquitoVerificarCodigoResponse(ok=False, error="Codigo invalido o expirado.")

    row.usado = True
    db.commit()

    access = create_access_token(
        subject=u.id,
        extra={"scope": "finiquito", "cedula": u.cedula, "email": u.email},
        expire_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
    )
    return FiniquitoVerificarCodigoResponse(
        ok=True,
        access_token=access,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/public/casos", response_model=FiniquitoCasoListaResponse)
def finiquito_public_listar_casos(
    bandeja: Optional[str] = Query(
        None,
        description=(
            "entrada = solo REVISION; desk = solo ACEPTADO; "
            "todos o omitir = todos los casos (prestamos con suma abonos = financiamiento)"
        ),
    ),
    db: Session = Depends(get_db),
    _: FiniquitoUsuarioAcceso = Depends(get_finiquito_usuario_acceso),
):
    b = (bandeja or "").lower().strip()
    if b in ("", "todos", "todas", "all"):
        q = db.query(FiniquitoCaso).order_by(FiniquitoCaso.id.desc())
    elif b == "entrada":
        q = db.query(FiniquitoCaso).filter(FiniquitoCaso.estado == "REVISION").order_by(FiniquitoCaso.id.desc())
    elif b == "desk":
        q = db.query(FiniquitoCaso).filter(FiniquitoCaso.estado == "ACEPTADO").order_by(FiniquitoCaso.id.desc())
    else:
        raise HTTPException(
            status_code=400,
            detail="bandeja debe ser entrada, desk, todos u omitirse",
        )
    casos = q.all()
    mp = _map_ultima_fecha_pago_por_prestamo(db, [c.prestamo_id for c in casos])
    items: List[FiniquitoCasoOut] = [
        _caso_to_out(c, mp.get(c.prestamo_id)) for c in casos
    ]
    return FiniquitoCasoListaResponse(items=items)


@router.get("/public/casos/{caso_id}/detalle", response_model=FiniquitoDetalleResponse)
def finiquito_public_detalle(
    caso_id: int,
    db: Session = Depends(get_db),
    _: FiniquitoUsuarioAcceso = Depends(get_finiquito_usuario_acceso),
):
    caso = db.query(FiniquitoCaso).filter(FiniquitoCaso.id == caso_id).first()
    if not caso:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    prestamo = db.query(Prestamo).filter(Prestamo.id == caso.prestamo_id).first()
    cuotas = (
        db.query(Cuota)
        .filter(Cuota.prestamo_id == caso.prestamo_id)
        .order_by(Cuota.numero_cuota.asc())
        .all()
    )
    prestamo_d: Optional[dict[str, Any]] = None
    if prestamo:
        prestamo_d = _prestamo_caso_completo(prestamo)
    cuotas_l = [_cuota_to_dict(cu) for cu in cuotas]
    mp = _map_ultima_fecha_pago_por_prestamo(db, [caso.prestamo_id])
    return FiniquitoDetalleResponse(
        caso=_caso_to_out(caso, mp.get(caso.prestamo_id)),
        prestamo=prestamo_d,
        cuotas=cuotas_l,
    )


@router.get("/public/revision-datos/{caso_id}")
def finiquito_public_revision_datos(
    caso_id: int,
    db: Session = Depends(get_db),
    _: FiniquitoUsuarioAcceso = Depends(get_finiquito_usuario_acceso),
):
    """
    Detalle del caso: préstamo vinculado (campos ampliados), plan de cuotas,
    listado /prestamos por cédula y /pagos por cédula (todos los pagos, tope 100 por API).
    """
    caso = db.query(FiniquitoCaso).filter(FiniquitoCaso.id == caso_id).first()
    if not caso:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    cedula = (caso.cedula or "").strip()
    if not cedula:
        raise HTTPException(status_code=400, detail="Caso sin cedula")
    return jsonable_encoder(_build_revision_datos_payload(db, caso))


@router.patch("/public/casos/{caso_id}/estado", response_model=FiniquitoPatchEstadoResponse)
def finiquito_public_patch_estado(
    caso_id: int,
    body: FiniquitoPatchEstadoRequest,
    db: Session = Depends(get_db),
    fu: FiniquitoUsuarioAcceso = Depends(get_finiquito_usuario_acceso),
):
    """Usuario portal: solo desde REVISION a ACEPTADO o RECHAZADO."""
    nuevo = (body.estado or "").upper().strip()
    if nuevo not in ("ACEPTADO", "RECHAZADO"):
        return FiniquitoPatchEstadoResponse(
            ok=False,
            error="Solo puede aceptar o rechazar desde la bandeja de entrada (REVISION).",
        )
    caso = db.query(FiniquitoCaso).filter(FiniquitoCaso.id == caso_id).first()
    if not caso:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    if caso.estado != "REVISION":
        return FiniquitoPatchEstadoResponse(
            ok=False,
            error="Solo puede cambiar casos en estado REVISION.",
        )
    anterior = caso.estado
    caso.estado = nuevo
    _registrar_historial(
        db,
        caso=caso,
        estado_anterior=anterior,
        estado_nuevo=nuevo,
        actor_tipo="finiquito_externo",
        finiquito_usuario_id=fu.id,
    )
    db.commit()
    db.refresh(caso)
    mp = _map_ultima_fecha_pago_por_prestamo(db, [caso.prestamo_id])
    return FiniquitoPatchEstadoResponse(
        ok=True, caso=_caso_to_out(caso, mp.get(caso.prestamo_id))
    )


@router.get("/admin/casos", response_model=FiniquitoCasoListaResponse)
def finiquito_admin_listar(
    estado: Optional[str] = Query(None, description="Filtrar por REVISION, ACEPTADO o RECHAZADO"),
    cedula: Optional[str] = Query(
        None,
        description="Subcadena de cedula (coincidencia parcial, sin distinguir mayusculas)",
    ),
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_administrador),
):
    q = db.query(FiniquitoCaso)
    if estado:
        e = estado.upper().strip()
        if e not in ESTADOS_VALIDOS:
            raise HTTPException(status_code=400, detail="Estado invalido")
        q = q.filter(FiniquitoCaso.estado == e)
    if cedula and cedula.strip():
        q = q.filter(FiniquitoCaso.cedula.ilike(f"%{cedula.strip()}%"))
    casos = q.order_by(FiniquitoCaso.id.desc()).all()
    mp = _map_ultima_fecha_pago_por_prestamo(db, [c.prestamo_id for c in casos])
    items = [_caso_to_out(c, mp.get(c.prestamo_id)) for c in casos]
    return FiniquitoCasoListaResponse(items=items)


@router.get("/admin/casos/{caso_id}/revision-datos")
def finiquito_admin_revision_datos(
    caso_id: int,
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_administrador),
):
    """Misma carga que GET public/revision-datos (préstamo caso, cuotas, préstamos/pagos por cédula)."""
    caso = db.query(FiniquitoCaso).filter(FiniquitoCaso.id == caso_id).first()
    if not caso:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    cedula = (caso.cedula or "").strip()
    if not cedula:
        raise HTTPException(status_code=400, detail="Caso sin cedula")
    return jsonable_encoder(_build_revision_datos_payload(db, caso))


@router.patch("/admin/casos/{caso_id}/estado", response_model=FiniquitoPatchEstadoResponse)
def finiquito_admin_patch_estado(
    caso_id: int,
    body: FiniquitoPatchEstadoRequest,
    db: Session = Depends(get_db),
    admin: UserResponse = Depends(require_administrador),
):
    """Administrador: puede pasar a cualquier estado (incl. salida de RECHAZADO)."""
    nuevo = (body.estado or "").upper().strip()
    if nuevo not in ESTADOS_VALIDOS:
        return FiniquitoPatchEstadoResponse(ok=False, error="Estado invalido")
    caso = db.query(FiniquitoCaso).filter(FiniquitoCaso.id == caso_id).first()
    if not caso:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    anterior = caso.estado
    caso.estado = nuevo
    _registrar_historial(
        db,
        caso=caso,
        estado_anterior=anterior,
        estado_nuevo=nuevo,
        actor_tipo="admin",
        user_id=admin.id,
    )
    db.commit()
    db.refresh(caso)
    mp = _map_ultima_fecha_pago_por_prestamo(db, [caso.prestamo_id])
    return FiniquitoPatchEstadoResponse(
        ok=True, caso=_caso_to_out(caso, mp.get(caso.prestamo_id))
    )


@router.post("/admin/refresh-materializado")
def finiquito_admin_refresh_manual(
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_administrador),
):
    """Uso operativo: ejecutar el mismo refresco que el job 02:00 (sin esperar al cron)."""
    from app.services.finiquito_refresh import ejecutar_refresh_finiquito_casos

    return ejecutar_refresh_finiquito_casos(db)
