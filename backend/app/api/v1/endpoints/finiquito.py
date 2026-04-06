"""
Finiquito: casos materializados solo para prestamos LIQUIDADO con cuotas = financiamiento
(job 02:00), portal publico OTP, bandejas, admin.
"""
from __future__ import annotations

import logging
import random
import string
import time
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.cobros_public_rate_limit import (
    FINIQUITO_SOLICITAR_CODIGO_MAX,
    check_rate_limit_finiquito_solicitar_codigo,
    get_client_ip,
)
from app.core.database import get_db
from app.core.deps import (
    get_finiquito_usuario_acceso,
    require_admin,
)
from app.core.email import mask_email_for_log, send_email
from app.core.email_cuentas import SERVICIO_FINIQUITO
from app.services.notificaciones_exclusion_desistimiento import (
    cliente_bloqueado_por_desistimiento,
)
from app.core.email_config_holder import (
    get_email_activo,
    get_email_activo_servicio,
    get_modo_pruebas_email,
    get_smtp_config,
    sync_from_db,
)
from app.core.security import create_access_token
from app.models.cliente import Cliente
from app.models.cuota import Cuota
from app.models.pago import Pago
from app.models.finiquito import (
    FiniquitoAreaTrabajoAuditoria,
    FiniquitoCaso,
    FiniquitoEstadoHistorial,
    FiniquitoLoginCodigo,
    FiniquitoUsuarioAcceso,
)
from app.models.prestamo import Prestamo
from app.schemas.auth import UserResponse
from app.schemas.finiquito import (
    FiniquitoConteoRevisionNuevosResponse,
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
from app.services.finiquito_area_trabajo_emails import (
    enviar_correo_en_proceso_operaciones,
    enviar_correo_rechazo_itmaster,
)
from app.services.finiquito_prestamo_gestion_sync import (
    sincronizar_prestamo_estado_gestion_finiquito,
)
from app.services.finiquito_db_schema import (
    finiquito_casos_has_contacto_para_siguientes,
    finiquito_has_area_trabajo_auditoria_table,
)
from app.services.finiquito_otp_metrics import (
    finiquito_otp_bump,
    finiquito_otp_snapshot,
)
from app.utils.cedula_almacenamiento import normalizar_cedula_almacenamiento

logger = logging.getLogger(__name__)

router = APIRouter()


def _json_safe_revision_subpayload(obj: Any) -> Any:
    """
    Convierte salidas de listar_prestamos / listar_pagos (Pydantic, Decimal, fechas)
    a estructura serializable; evita fallos de jsonable_encoder en revision-datos.
    """
    if obj is None:
        return None
    if hasattr(obj, "model_dump") and callable(obj.model_dump):
        try:
            return obj.model_dump(mode="json")
        except Exception:
            return obj.model_dump()
    if hasattr(obj, "dict") and callable(getattr(obj, "dict", None)):
        try:
            return obj.dict()
        except Exception:
            pass
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, timedelta):
        return str(obj)
    if isinstance(obj, list):
        return [_json_safe_revision_subpayload(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _json_safe_revision_subpayload(v) for k, v in obj.items()}
    return obj

_ADMIN_CASOS_DEFAULT_LIMIT = 500
_ADMIN_CASOS_MAX_LIMIT = 2000

ESTADOS_VALIDOS = frozenset(
    {"REVISION", "ACEPTADO", "RECHAZADO", "EN_PROCESO", "TERMINADO", "ANTIGUO"}
)

# Ultima fecha de pago <= esta fecha: Antiguo sin nota obligatoria (operacion previa a la migracion).
FECHA_CORTE_ANTIGUO = date(2026, 1, 1)
MIN_NOTA_ANTIGUO = 15
CODIGO_EXPIRA_MINUTES = 120


def _mask_smtp_user_for_log(user: str) -> str:
    s = (user or "").strip()
    if not s:
        return "(vacío)"
    if "@" in s:
        return mask_email_for_log(s)
    if len(s) <= 2:
        return "**"
    return f"{s[:2]}***"


def _generar_codigo_6() -> str:
    return "".join(random.choices(string.digits, k=6))


def _ultima_fecha_pago_date_prestamo(db: Session, prestamo_id: int) -> Optional[date]:
    """Fecha calendario de MAX(pagos.fecha_pago) para el prestamo, o None."""
    mx = (
        db.query(func.max(Pago.fecha_pago))
        .filter(Pago.prestamo_id == int(prestamo_id))
        .scalar()
    )
    if mx is None:
        return None
    if hasattr(mx, "date"):
        return mx.date()
    if isinstance(mx, date):
        return mx
    return None


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


def _map_clientes_por_id(db: Session, cliente_ids: List[int]) -> dict[int, Cliente]:
    seen: set[int] = set()
    uniq: List[int] = []
    for i in cliente_ids:
        if i is None:
            continue
        ii = int(i)
        if ii not in seen:
            seen.add(ii)
            uniq.append(ii)
    if not uniq:
        return {}
    rows = db.query(Cliente).filter(Cliente.id.in_(uniq)).all()
    return {int(cl.id): cl for cl in rows}


def _map_finiquito_tramite_fecha_limite_por_prestamo(
    db: Session, prestamo_ids: List[int]
) -> dict[int, Any]:
    """finiquito_tramite_fecha_limite en prestamos por prestamo_id."""
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
        db.query(Prestamo.id, Prestamo.finiquito_tramite_fecha_limite)
        .filter(Prestamo.id.in_(uniq))
        .all()
    )
    return {int(r[0]): r[1] for r in rows}


def _admin_casos_to_items(db: Session, casos: List[FiniquitoCaso]) -> List[FiniquitoCasoOut]:
    mp = _map_ultima_fecha_pago_por_prestamo(db, [c.prestamo_id for c in casos])
    flmap = _map_finiquito_tramite_fecha_limite_por_prestamo(
        db, [c.prestamo_id for c in casos]
    )
    clmap = _map_clientes_por_id(db, [c.cliente_id for c in casos if c.cliente_id])
    items: List[FiniquitoCasoOut] = []
    for c in casos:
        base = _caso_to_out(
            c,
            mp.get(c.prestamo_id),
            db,
            finiquito_tramite_fecha_limite=flmap.get(c.prestamo_id),
        )
        cl = clmap.get(int(c.cliente_id)) if c.cliente_id else None
        items.append(
            base.model_copy(
                update={
                    "cliente_nombres": cl.nombres if cl else None,
                    "cliente_email": cl.email if cl else None,
                    "cliente_telefono": cl.telefono if cl else None,
                }
            )
        )
    return items


def _caso_to_out(
    c: FiniquitoCaso,
    ultima_fecha_pago: Optional[Any] = None,
    db: Optional[Session] = None,
    *,
    finiquito_tramite_fecha_limite: Optional[Any] = None,
) -> FiniquitoCasoOut:
    ufp: Optional[str] = None
    if ultima_fecha_pago is not None:
        ufp = (
            ultima_fecha_pago.isoformat()
            if hasattr(ultima_fecha_pago, "isoformat")
            else str(ultima_fecha_pago)
        )
    ftl: Optional[str] = None
    if finiquito_tramite_fecha_limite is not None:
        v = finiquito_tramite_fecha_limite
        ftl = v.isoformat() if hasattr(v, "isoformat") else str(v)
    cps: Optional[bool] = None
    if db is not None and finiquito_casos_has_contacto_para_siguientes(db):
        try:
            cps = c.contacto_para_siguientes
        except Exception:
            cps = None
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
        contacto_para_siguientes=cps,
        finiquito_tramite_fecha_limite=ftl,
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
    nota: Optional[str] = None,
) -> None:
    nota_val = (nota or "").strip() or None
    db.add(
        FiniquitoEstadoHistorial(
            caso_id=caso.id,
            estado_anterior=estado_anterior,
            estado_nuevo=estado_nuevo,
            user_id=user_id,
            finiquito_usuario_id=finiquito_usuario_id,
            actor_tipo=actor_tipo,
            nota=nota_val,
        )
    )


def _registrar_auditoria_area_trabajo(
    db: Session,
    *,
    caso_id: int,
    accion: str,
    estado_anterior: Optional[str],
    estado_nuevo: str,
    contacto_para_siguientes: Optional[bool],
    user_id: Optional[int],
) -> None:
    db.add(
        FiniquitoAreaTrabajoAuditoria(
            caso_id=caso_id,
            accion=accion,
            estado_anterior=estado_anterior,
            estado_nuevo=estado_nuevo,
            contacto_para_siguientes=contacto_para_siguientes,
            user_id=user_id,
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
        "estado_gestion_finiquito": getattr(p, "estado_gestion_finiquito", None),
        "finiquito_tramite_fecha_limite": _dt_iso(
            getattr(p, "finiquito_tramite_fecha_limite", None)
        ),
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
    try:
        # Pasar valores reales (None/str), no omitir parametros: sus defaults son
        # objetos Query(...) y listar_* hacen .strip() → AttributeError → 500.
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
            revision_manual_estado=None,
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
            prestamo_cartera="todos",
            db=db,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "finiquito revision-datos: fallo listar_prestamos/pagos cedula=%s caso_id=%s",
            cedula,
            caso.id,
        )
        raise HTTPException(
            status_code=500,
            detail=f"Error al cargar listados por cedula: {type(e).__name__}: {e}",
        ) from e

    prestamos_payload = _json_safe_revision_subpayload(prestamos_payload)
    pagos_payload = _json_safe_revision_subpayload(pagos_payload)

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
    request: Request,
    body: FiniquitoSolicitarCodigoRequest,
    db: Session = Depends(get_db),
):
    cedula = normalizar_cedula_almacenamiento(body.cedula)
    email = (body.email or "").lower().strip()
    if not cedula or not email:
        raise HTTPException(status_code=400, detail="Cedula y correo son obligatorios.")

    ip = get_client_ip(request)
    try:
        check_rate_limit_finiquito_solicitar_codigo(ip)
    except HTTPException as e:
        if e.status_code == 429:
            finiquito_otp_bump("rate_limit_429")
            logger.info(
                "finiquito solicitar-codigo: rate limit 429 (max %s por hora por IP)",
                FINIQUITO_SOLICITAR_CODIGO_MAX,
            )
        raise
    finiquito_otp_bump("solicitudes_recibidas")

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
        finiquito_otp_bump("usuario_no_encontrado")
        logger.debug(
            "finiquito solicitar-codigo: sin usuario activo cedula+email (respuesta generica al cliente). email_MASK=%s",
            mask_email_for_log(email),
        )
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

    # SMTP: servicio "finiquito" usa la misma cuenta que "estado_cuenta" (Cuenta 2 por defecto).
    # respetar_destinos_manuales=True evita redirigir el OTP al correo de pruebas del modo pruebas.
    sync_from_db()
    master_on = get_email_activo()
    finiquito_on = get_email_activo_servicio(SERVICIO_FINIQUITO)
    modo_pruebas, emails_prueba = get_modo_pruebas_email(servicio=SERVICIO_FINIQUITO)
    cfg_smtp = get_smtp_config(servicio=SERVICIO_FINIQUITO)
    smtp_host = (cfg_smtp.get("smtp_host") or "").strip()
    smtp_user = (cfg_smtp.get("smtp_user") or "").strip()
    pwd_set = bool((cfg_smtp.get("smtp_password") or "").strip()) and (
        cfg_smtp.get("smtp_password") or ""
    ).strip() != "***"
    logger.info(
        "finiquito solicitar-codigo: diagnostico pre-envio finiquito_usuario_id=%s dest_MASK=%s "
        "email_master_activo=%s email_servicio_finiquito=%s modo_pruebas_finiquito=%s "
        "correos_prueba_configurados=%s smtp_host=%s smtp_user_MASK=%s smtp_password_configurada=%s",
        u.id,
        mask_email_for_log(email),
        master_on,
        finiquito_on,
        modo_pruebas,
        bool(emails_prueba),
        smtp_host[:120] if smtp_host else "(vacío)",
        _mask_smtp_user_for_log(smtp_user),
        pwd_set,
    )

    if not finiquito_on:
        db.rollback()
        finiquito_otp_bump("envio_bloqueado_config_email")
        logger.warning(
            "finiquito solicitar-codigo: no enviado email_master=%s email_finiquito_o_estado_cuenta=%s "
            "(Configuracion > Email: interruptor general o Finiquito/Estado de cuenta desactivado).",
            master_on,
            finiquito_on,
        )
        return FiniquitoSolicitarCodigoResponse(
            ok=True,
            message="Si los datos son correctos, recibira un codigo en su correo.",
        )

    if cliente_bloqueado_por_desistimiento(db, email=email):
        db.rollback()
        finiquito_otp_bump("envio_bloqueado_desistimiento")
        logger.info(
            "finiquito solicitar-codigo: bloqueo por DESISTIMIENTO dest_MASK=%s",
            mask_email_for_log(email),
        )
        return FiniquitoSolicitarCodigoResponse(
            ok=True,
            message="Si los datos son correctos, recibira un codigo en su correo.",
        )

    t0 = time.perf_counter()
    ok_send, err_send = send_email(
        [email],
        asunto,
        cuerpo,
        servicio=SERVICIO_FINIQUITO,
        respetar_destinos_manuales=True,
    )
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    if not ok_send:
        db.rollback()
        finiquito_otp_bump("envio_smtp_fallo")
        logger.warning(
            "finiquito solicitar-codigo: SMTP fallo dest_MASK=%s duracion_ms=%.0f err=%s",
            mask_email_for_log(email),
            elapsed_ms,
            err_send or "send_email devolvio False",
        )
        return FiniquitoSolicitarCodigoResponse(
            ok=True,
            message="Si los datos son correctos, recibira un codigo en su correo.",
        )

    db.commit()
    finiquito_otp_bump("envio_smtp_ok")
    logger.info(
        "finiquito solicitar-codigo: enviado ok finiquito_usuario_id=%s dest_MASK=%s duracion_ms=%.0f",
        u.id,
        mask_email_for_log(email),
        elapsed_ms,
    )
    return FiniquitoSolicitarCodigoResponse(
        ok=True,
        message="Si los datos son correctos, recibira un codigo en su correo.",
    )


@router.get("/admin/otp-email-metricas")
def finiquito_admin_otp_email_metricas(
    _: UserResponse = Depends(require_admin),
):
    """
    Contadores en memoria desde el arranque del proceso (solicitudes OTP Finiquito).
    Se reinician al reiniciar el servidor; con varios workers cada uno tiene su propio contador.
    """
    return finiquito_otp_snapshot()


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
            "entrada = solo REVISION; desk = ACEPTADO, EN_PROCESO o TERMINADO; "
            "todos o omitir = todos los casos (solo prestamos LIQUIDADO materializados por el job)"
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
        q = (
            db.query(FiniquitoCaso)
            .filter(FiniquitoCaso.estado.in_(["ACEPTADO", "EN_PROCESO", "TERMINADO"]))
            .order_by(FiniquitoCaso.id.desc())
        )
    else:
        raise HTTPException(
            status_code=400,
            detail="bandeja debe ser entrada, desk, todos u omitirse",
        )
    casos = q.all()
    mp = _map_ultima_fecha_pago_por_prestamo(db, [c.prestamo_id for c in casos])
    flmap = _map_finiquito_tramite_fecha_limite_por_prestamo(
        db, [c.prestamo_id for c in casos]
    )
    items: List[FiniquitoCasoOut] = [
        _caso_to_out(
            c,
            mp.get(c.prestamo_id),
            db,
            finiquito_tramite_fecha_limite=flmap.get(c.prestamo_id),
        )
        for c in casos
    ]
    n = len(items)
    return FiniquitoCasoListaResponse(items=items, total=n, limit=n, offset=0)


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
    flmap = _map_finiquito_tramite_fecha_limite_por_prestamo(db, [caso.prestamo_id])
    return FiniquitoDetalleResponse(
        caso=_caso_to_out(
            caso,
            mp.get(caso.prestamo_id),
            db,
            finiquito_tramite_fecha_limite=flmap.get(caso.prestamo_id),
        ),
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
    sincronizar_prestamo_estado_gestion_finiquito(db, caso.prestamo_id, caso.estado)
    db.commit()
    db.refresh(caso)
    mp = _map_ultima_fecha_pago_por_prestamo(db, [caso.prestamo_id])
    flmap = _map_finiquito_tramite_fecha_limite_por_prestamo(db, [caso.prestamo_id])
    return FiniquitoPatchEstadoResponse(
        ok=True,
        caso=_caso_to_out(
            caso,
            mp.get(caso.prestamo_id),
            db,
            finiquito_tramite_fecha_limite=flmap.get(caso.prestamo_id),
        ),
    )


@router.get("/admin/casos", response_model=FiniquitoCasoListaResponse)
def finiquito_admin_listar(
    estado: Optional[str] = Query(
        None,
        description="Un solo estado (REVISION, ACEPTADO, RECHAZADO, EN_PROCESO, TERMINADO, ANTIGUO)",
    ),
    estado_in: Optional[str] = Query(
        None,
        description="Varios estados separados por coma (ej. ACEPTADO,EN_PROCESO,TERMINADO). Tiene prioridad sobre estado.",
    ),
    cedula: Optional[str] = Query(
        None,
        description="Subcadena de cedula (coincidencia parcial, sin distinguir mayusculas)",
    ),
    limit: int = Query(
        _ADMIN_CASOS_DEFAULT_LIMIT,
        ge=1,
        le=_ADMIN_CASOS_MAX_LIMIT,
        description="Tamano de pagina (max 2000).",
    ),
    offset: int = Query(0, ge=0, description="Desplazamiento para paginacion."),
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_admin),
):
    # Filtros reutilizables: no usar .count() y luego el mismo Query con order_by
    # (en SQLAlchemy eso puede dejar el objeto en estado invalido y producir 500).
    filters: List[Any] = []
    if estado_in and estado_in.strip():
        parts = [p.strip().upper() for p in estado_in.split(",") if p.strip()]
        if not parts:
            raise HTTPException(status_code=400, detail="estado_in vacio")
        bad = [p for p in parts if p not in ESTADOS_VALIDOS]
        if bad:
            raise HTTPException(status_code=400, detail="Estado invalido en estado_in")
        filters.append(FiniquitoCaso.estado.in_(parts))
    elif estado:
        e = estado.upper().strip()
        if e not in ESTADOS_VALIDOS:
            raise HTTPException(status_code=400, detail="Estado invalido")
        filters.append(FiniquitoCaso.estado == e)
    if cedula and cedula.strip():
        filters.append(FiniquitoCaso.cedula.ilike(f"%{cedula.strip()}%"))

    count_q = db.query(func.count(FiniquitoCaso.id))
    list_q = db.query(FiniquitoCaso)
    if filters:
        count_q = count_q.filter(*filters)
        list_q = list_q.filter(*filters)
    total_raw = count_q.scalar()
    total = int(total_raw or 0)
    casos = (
        list_q.order_by(FiniquitoCaso.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    items = _admin_casos_to_items(db, casos)
    return FiniquitoCasoListaResponse(
        items=items, total=total, limit=limit, offset=offset
    )


@router.get(
    "/admin/casos/conteo-revision-nuevos",
    response_model=FiniquitoConteoRevisionNuevosResponse,
)
def finiquito_admin_conteo_revision_nuevos(
    horas: int = Query(
        72,
        ge=1,
        le=720,
        description=(
            "Ventana en horas: cuenta casos en REVISION cuyo creado_en (materializacion) "
            "cae en ese intervalo hacia atras desde ahora (UTC)."
        ),
    ),
    cedula: Optional[str] = Query(
        None,
        description="Subcadena de cedula (coincidencia parcial), misma regla que GET /admin/casos.",
    ),
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_admin),
):
    """
    KPI alarma: préstamos recién ingresados a finiquito (REVISION) al catalogarse como
    LIQUIDADO elegibles en el job / refresco materializado.
    """
    cutoff = datetime.utcnow() - timedelta(hours=int(horas))
    q = db.query(func.count(FiniquitoCaso.id)).filter(
        FiniquitoCaso.estado == "REVISION",
        FiniquitoCaso.creado_en >= cutoff,
    )
    if cedula and cedula.strip():
        q = q.filter(FiniquitoCaso.cedula.ilike(f"%{cedula.strip()}%"))
    total_raw = q.scalar()
    total = int(total_raw or 0)
    return FiniquitoConteoRevisionNuevosResponse(
        total=total, ventana_horas=int(horas)
    )


@router.get("/admin/casos/{caso_id}/revision-datos")
def finiquito_admin_revision_datos(
    caso_id: int,
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_admin),
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
    admin: UserResponse = Depends(require_admin),
):
    """Administrador: bandejas y area de trabajo (REVISION desde area, EN_PROCESO, TERMINADO)."""
    nuevo = (body.estado or "").upper().strip()
    if nuevo not in ESTADOS_VALIDOS:
        return FiniquitoPatchEstadoResponse(ok=False, error="Estado invalido")
    caso = db.query(FiniquitoCaso).filter(FiniquitoCaso.id == caso_id).first()
    if not caso:
        raise HTTPException(status_code=404, detail="Caso no encontrado")
    anterior = caso.estado

    if nuevo == "ANTIGUO":
        if anterior != "REVISION":
            return FiniquitoPatchEstadoResponse(
                ok=False,
                error="Antiguo solo desde la bandeja principal (estado Revisión).",
            )
        ufp_d = _ultima_fecha_pago_date_prestamo(db, caso.prestamo_id)
        nota = (body.nota_antiguo or "").strip()
        requiere_nota = ufp_d is None or ufp_d > FECHA_CORTE_ANTIGUO
        if requiere_nota and len(nota) < MIN_NOTA_ANTIGUO:
            return FiniquitoPatchEstadoResponse(
                ok=False,
                error=(
                    "Nota justificativa obligatoria (minimo 15 caracteres) si la ultima fecha de pago "
                    "es posterior al 01/01/2026 o no consta."
                ),
            )
        caso.estado = nuevo
        if finiquito_casos_has_contacto_para_siguientes(db):
            caso.contacto_para_siguientes = None
        _registrar_historial(
            db,
            caso=caso,
            estado_anterior=anterior,
            estado_nuevo=nuevo,
            actor_tipo="admin",
            user_id=admin.id,
            nota=nota or None,
        )
        sincronizar_prestamo_estado_gestion_finiquito(db, caso.prestamo_id, caso.estado)
        db.commit()
        db.refresh(caso)
        caso_out = _admin_casos_to_items(db, [caso])[0]
        return FiniquitoPatchEstadoResponse(ok=True, caso=caso_out)

    if nuevo == "REVISION":
        if anterior not in ("ACEPTADO", "EN_PROCESO", "TERMINADO"):
            return FiniquitoPatchEstadoResponse(
                ok=False,
                error=(
                    "Solo puede devolver a Revision desde el area de trabajo "
                    "(Aceptado, En proceso o Terminado)."
                ),
            )
        caso.estado = nuevo
        if finiquito_casos_has_contacto_para_siguientes(db):
            caso.contacto_para_siguientes = None
        _registrar_historial(
            db,
            caso=caso,
            estado_anterior=anterior,
            estado_nuevo=nuevo,
            actor_tipo="admin",
            user_id=admin.id,
        )
        if finiquito_has_area_trabajo_auditoria_table(db):
            _registrar_auditoria_area_trabajo(
                db,
                caso_id=caso.id,
                accion="REVISION",
                estado_anterior=anterior,
                estado_nuevo=nuevo,
                contacto_para_siguientes=None,
                user_id=admin.id,
            )
        sincronizar_prestamo_estado_gestion_finiquito(db, caso.prestamo_id, caso.estado)
        db.commit()
        db.refresh(caso)
        caso_out = _admin_casos_to_items(db, [caso])[0]
        return FiniquitoPatchEstadoResponse(ok=True, caso=caso_out)

    if nuevo in ("EN_PROCESO", "TERMINADO") and not finiquito_casos_has_contacto_para_siguientes(db):
        return FiniquitoPatchEstadoResponse(
            ok=False,
            error=(
                "Aplique la migracion de finiquito area de trabajo en la base de datos "
                "(backend/sql/2026-03-24_finiquito_area_trabajo_auditoria.sql o alembic upgrade head / 025_finiquito_area_trabajo)."
            ),
        )

    if nuevo == "TERMINADO":
        if anterior not in ("EN_PROCESO", "ACEPTADO"):
            return FiniquitoPatchEstadoResponse(
                ok=False,
                error="Terminado solo desde Aceptado o En proceso.",
            )
        if anterior == "EN_PROCESO" and body.contacto_para_siguientes is None:
            return FiniquitoPatchEstadoResponse(
                ok=False,
                error="Debe indicar si contacto al cliente para pasos siguientes (Si o No).",
            )
    elif nuevo == "EN_PROCESO":
        if anterior != "ACEPTADO":
            return FiniquitoPatchEstadoResponse(
                ok=False,
                error="Solo puede marcar En proceso desde Aceptado.",
            )

    caso.estado = nuevo
    if finiquito_casos_has_contacto_para_siguientes(db):
        if nuevo == "TERMINADO":
            cps = body.contacto_para_siguientes
            if cps is None and anterior == "ACEPTADO":
                cps = False
            caso.contacto_para_siguientes = cps
        else:
            caso.contacto_para_siguientes = None

    _registrar_historial(
        db,
        caso=caso,
        estado_anterior=anterior,
        estado_nuevo=nuevo,
        actor_tipo="admin",
        user_id=admin.id,
    )
    if finiquito_has_area_trabajo_auditoria_table(db):
        if nuevo == "EN_PROCESO":
            _registrar_auditoria_area_trabajo(
                db,
                caso_id=caso.id,
                accion="EN_PROCESO",
                estado_anterior=anterior,
                estado_nuevo=nuevo,
                contacto_para_siguientes=None,
                user_id=admin.id,
            )
        elif nuevo == "TERMINADO":
            _cps_aud = body.contacto_para_siguientes
            if _cps_aud is None and anterior == "ACEPTADO":
                _cps_aud = False
            _registrar_auditoria_area_trabajo(
                db,
                caso_id=caso.id,
                accion="TERMINADO",
                estado_anterior=anterior,
                estado_nuevo=nuevo,
                contacto_para_siguientes=_cps_aud,
                user_id=admin.id,
            )

    sincronizar_prestamo_estado_gestion_finiquito(db, caso.prestamo_id, caso.estado)
    db.commit()
    db.refresh(caso)
    if nuevo == "EN_PROCESO":
        enviar_correo_en_proceso_operaciones(
            db,
            caso,
            admin_email=admin.email or "",
            admin_nombre=f"{(admin.nombre or '').strip()} {(admin.apellido or '').strip()}".strip(),
        )
    elif nuevo == "RECHAZADO":
        enviar_correo_rechazo_itmaster(caso)
    caso_out = _admin_casos_to_items(db, [caso])[0]
    return FiniquitoPatchEstadoResponse(ok=True, caso=caso_out)


@router.post("/admin/refresh-materializado")
def finiquito_admin_refresh_manual(
    db: Session = Depends(get_db),
    _: UserResponse = Depends(require_admin),
):
    """Uso operativo: ejecutar el mismo refresco que el job 02:00 (sin esperar al cron)."""
    from app.services.finiquito_refresh import ejecutar_refresh_finiquito_casos

    return ejecutar_refresh_finiquito_casos(db)
