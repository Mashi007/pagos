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
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import (
    get_finiquito_usuario_acceso,
    require_administrador,
)
from app.core.email import send_email
from app.core.security import create_access_token
from app.models.cuota import Cuota
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


def _caso_to_out(c: FiniquitoCaso) -> FiniquitoCasoOut:
    return FiniquitoCasoOut(
        id=c.id,
        prestamo_id=c.prestamo_id,
        cliente_id=c.cliente_id,
        cedula=c.cedula or "",
        total_financiamiento=str(c.total_financiamiento),
        sum_total_pagado=str(c.sum_total_pagado),
        estado=c.estado,
        ultimo_refresh_utc=c.ultimo_refresh_utc.isoformat() if c.ultimo_refresh_utc else None,
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
    db.commit()

    asunto = "[RapiCredit] Codigo de acceso Finiquito"
    cuerpo = (
        f"Su codigo de acceso al portal Finiquito es: {codigo}\n\n"
        f"Valido por {CODIGO_EXPIRA_MINUTES} minutos.\n"
        "Si usted no solicito este codigo, ignore este mensaje."
    )
    ok_send, err_send = send_email([email], asunto, cuerpo)
    if not ok_send:
        logger.warning("finiquito solicitar-codigo: no enviado a %s: %s", email, err_send)

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
    items: List[FiniquitoCasoOut] = [_caso_to_out(c) for c in q.all()]
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
        prestamo_d = {
            "id": prestamo.id,
            "cedula": prestamo.cedula,
            "nombres": prestamo.nombres,
            "total_financiamiento": str(prestamo.total_financiamiento),
            "estado": prestamo.estado,
            "producto": prestamo.producto,
            "numero_cuotas": prestamo.numero_cuotas,
        }
    cuotas_l: List[dict[str, Any]] = []
    for cu in cuotas:
        cuotas_l.append(
            {
                "id": cu.id,
                "numero_cuota": cu.numero_cuota,
                "fecha_vencimiento": cu.fecha_vencimiento.isoformat() if cu.fecha_vencimiento else None,
                "monto_cuota": str(cu.monto) if cu.monto is not None else None,
                "total_pagado": str(cu.total_pagado) if cu.total_pagado is not None else None,
                "estado": cu.estado,
            }
        )
    return FiniquitoDetalleResponse(caso=_caso_to_out(caso), prestamo=prestamo_d, cuotas=cuotas_l)


@router.get("/public/revision-datos/{caso_id}")
def finiquito_public_revision_datos(
    caso_id: int,
    db: Session = Depends(get_db),
    _: FiniquitoUsuarioAcceso = Depends(get_finiquito_usuario_acceso),
):
    """
    Misma data que GET /prestamos (filtro cedula) y GET /pagos (cedula + conciliado=si,
    como la pantalla Pagos por defecto), para revision desde el ojo en Finiquito.
    """
    caso = db.query(FiniquitoCaso).filter(FiniquitoCaso.id == caso_id).first()
    if not caso:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    cedula = (caso.cedula or "").strip()
    if not cedula:
        raise HTTPException(status_code=400, detail="Caso sin cedula")

    from app.api.v1.endpoints.pagos import listar_pagos
    from app.api.v1.endpoints.prestamos import listar_prestamos

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
        conciliado="si",
        sin_prestamo=None,
        db=db,
    )
    return jsonable_encoder(
        {
            "caso_id": caso_id,
            "cedula": cedula,
            "prestamos": prestamos_payload,
            "pagos": pagos_payload,
        }
    )


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
    return FiniquitoPatchEstadoResponse(ok=True, caso=_caso_to_out(caso))


@router.get("/admin/casos", response_model=FiniquitoCasoListaResponse)
def finiquito_admin_listar(
    estado: Optional[str] = Query(None, description="Filtrar por REVISION, ACEPTADO o RECHAZADO"),
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_administrador),
):
    q = db.query(FiniquitoCaso)
    if estado:
        e = estado.upper().strip()
        if e not in ESTADOS_VALIDOS:
            raise HTTPException(status_code=400, detail="Estado invalido")
        q = q.filter(FiniquitoCaso.estado == e)
    items = [_caso_to_out(c) for c in q.order_by(FiniquitoCaso.id.desc()).all()]
    return FiniquitoCasoListaResponse(items=items)


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
    return FiniquitoPatchEstadoResponse(ok=True, caso=_caso_to_out(caso))


@router.post("/admin/refresh-materializado")
def finiquito_admin_refresh_manual(
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_administrador),
):
    """Uso operativo: ejecutar el mismo refresco que el job 02:00 (sin esperar al cron)."""
    from app.services.finiquito_refresh import ejecutar_refresh_finiquito_casos

    return ejecutar_refresh_finiquito_casos(db)
