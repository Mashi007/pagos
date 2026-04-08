"""
Endpoints para Revisión Manual de Préstamos (post-migración).
Lista de préstamos con detalles completos, edición de cliente/préstamo/pagos, y marcado como revisado.
Incluye validaciones y logging para garantizar integridad de datos.
"""
import logging
from datetime import date, datetime
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, Body
from sqlalchemy import select, func, and_, case, literal_column, text
from sqlalchemy.orm import Session, aliased
from sqlalchemy.exc import ProgrammingError
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.rol_normalization import canonical_rol
from app.constants.prestamo_estados import prestamo_estado_exige_fecha_aprobacion
from app.services.prestamos.fechas_prestamo_coherencia import (
    alinear_fecha_aprobacion_y_base_calculo,
    rellenar_fecha_aprobacion_desde_base_si_falta,
)
from app.core.serializers import format_datetime_iso, to_finite_float, to_finite_float_or_zero
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.models.cuota import Cuota
from app.models.pago import Pago
from app.models.revision_manual_prestamo import RevisionManualPrestamo
from app.models.revision_manual_solicitud_reapertura import RevisionManualSolicitudReapertura
from app.models.user import User
from app.models.auditoria import Auditoria
from app.models.estado_cliente import EstadoCliente
from app.api.v1.endpoints.pagos import aplicar_pagos_pendientes_prestamo
from app.services.notificacion_service import (
    contar_cuotas_pagadas_tabla_amortizacion_ui,
    sum_saldo_pendiente_cuotas_tabla_amortizacion_ui,
)
from app.services.prestamo_estado_coherencia import prestamo_bloquea_nuevas_cuotas_o_cambio_plazo
from app.services.prestamos.prestamo_cedula_cliente_coherencia import (
    PrestamoCedulaClienteError,
    asegurar_prestamo_alineado_con_cliente,
)
from app.services.registro_cambios_service import registrar_cambio
from app.services.revision_manual.revision_manual_flags import (
    marcar_o_crear_prestamo_editado_en_revision_manual,
)
from app.services.revision_manual.revision_manual_reapertura_notificaciones import (
    notify_admins_nueva_solicitud_reapertura,
    notify_operario_solicitud_reapertura_aprobada,
)

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])


def _solicitud_reapertura_estado_pendiente_sql(column):
    """
    Comparación robusta del estado de la solicitud (trim + minúsculas).
    Evita que filas con 'PENDIENTE' u otros matices queden fuera del listado admin.
    """
    return func.lower(func.trim(func.coalesce(column, ""))) == "pendiente"


def _usuario_rol_elevado_revision_manual(current_user: Any) -> bool:
    """
    Admin u operario: pueden editar mientras la revisión NO está cerrada (pendiente / revisando / en_espera).
    Con estado revisado (Visto), el permiso lo define `_usuario_puede_mutar_revision_visto`.
    """
    if isinstance(current_user, dict):
        rol_raw = current_user.get("rol")
    else:
        rol_raw = getattr(current_user, "rol", None)
    rol = rol_raw if isinstance(rol_raw, str) else None
    return canonical_rol(rol) in ("admin", "operator")


def _usuario_es_admin_revision_manual(current_user: Any) -> bool:
    """Administrador: puede reabrir desde Visto (revisado) y editar con la revisión cerrada."""
    if isinstance(current_user, dict):
        rol_raw = current_user.get("rol")
    else:
        rol_raw = getattr(current_user, "rol", None)
    rol = rol_raw if isinstance(rol_raw, str) else None
    return canonical_rol(rol) == "admin"


def _usuario_puede_mutar_revision_visto(current_user: Any) -> bool:
    """Con revisión en Visto (revisado): admin, gerente y operador (misma política que la UI)."""
    if isinstance(current_user, dict):
        rol_raw = current_user.get("rol")
    else:
        rol_raw = getattr(current_user, "rol", None)
    rol = rol_raw if isinstance(rol_raw, str) else None
    return canonical_rol(rol) in ("admin", "manager", "operator")


def _actor_revision_manual(current_user: Any) -> str:
    """Identificador seguro para logs (sin tokens ni datos sensibles)."""
    if current_user is None:
        return "anonimo"
    if isinstance(current_user, dict):
        return str(
            current_user.get("email")
            or current_user.get("sub")
            or current_user.get("preferred_username")
            or "usuario"
        )
    return str(
        getattr(current_user, "email", None)
        or getattr(current_user, "id", None)
        or "usuario"
    )


def _commit_revision_seguro(
    db: Session,
    *,
    operacion: str,
    actor: str,
    tabla_principal: str,
    id_principal: Optional[int],
    resumen_campos: Optional[List[str]] = None,
) -> None:
    """
    Persiste la transacción; ante fallo hace rollback, deja traza y responde 500.
    Tras éxito registra INFO para auditoría operativa (tabla e ids).
    """
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception(
            "revision_manual COMMIT_FALLIDO operacion=%s tabla=%s id=%s actor=%s",
            operacion,
            tabla_principal,
            id_principal,
            actor,
        )
        orig = getattr(exc, "orig", None)
        if orig is not None:
            logger.error(
                "revision_manual COMMIT_FALLIDO orig tipo=%s mensaje=%s",
                type(orig).__name__,
                str(orig)[:800],
            )
        detail = "Error al persistir en la base de datos. Los cambios no se aplicaron."
        if settings.DEBUG:
            detail = f"{detail} [{type(exc).__name__}: {str(exc)[:400]}]"
        raise HTTPException(status_code=500, detail=detail) from exc
    logger.info(
        "revision_manual BD_GUARDADO operacion=%s tabla=%s id=%s actor=%s campos=%s",
        operacion,
        tabla_principal,
        id_principal,
        actor,
        resumen_campos or [],
    )


def _validar_permiso_edicion(
    db: Session,
    prestamo_id: int,
    current_user: Any,
    actor: str,
) -> None:
    """
    Valida permisos de edición según el estado y rol del usuario.
    
    Reglas:
    - ✓ REVISADO (Visto): administrador, gerente o operador (corrección tras cierre; alineado con UI)
    - ❓ REVISANDO: solo admin u operario
    - ⚠️ PENDIENTE, ❌ EN ESPERA: cualquier usuario autenticado con acceso al endpoint
    """
    rev = db.execute(
        select(RevisionManualPrestamo).where(RevisionManualPrestamo.prestamo_id == prestamo_id)
    ).scalars().first()
    
    if not rev:
        # Si no existe registro de revisión, permitir
        return
    
    estado = (rev.estado_revision or "").strip().lower()
    elevado = _usuario_rol_elevado_revision_manual(current_user)

    # ✓ REVISADO (Visto): admin, gerente u operador
    if estado == "revisado":
        if _usuario_puede_mutar_revision_visto(current_user):
            return
        logger.warning(
            "revision_manual EDICION_RECHAZADA prestamo_id=%s motivo=revisado_sin_permiso actor=%s",
            prestamo_id,
            actor,
        )
        raise HTTPException(
            status_code=403,
            detail=(
                "Esta revisión está cerrada (Visto). Solo administrador, gerente u operario pueden editarla "
                "o reabrirla pasando el estado a «En revisión»."
            ),
        )
    
    # ❓ REVISANDO: admin u operario
    if estado == "revisando" and not elevado:
        logger.warning(
            "revision_manual EDICION_RECHAZADA prestamo_id=%s motivo=revisando_solo_elevado actor=%s",
            prestamo_id,
            actor,
        )
        raise HTTPException(
            status_code=403,
            detail="Este préstamo está en revisión. Solo personal autorizado (administrador u operario) puede editar en este estado.",
        )


# ===== SCHEMAS VALIDACION =====


def _body_tiene_fecha_iso_no_vacia(val: Optional[str]) -> bool:
    """True si el cliente envió un string de fecha con contenido (evita '' que no es None en Pydantic)."""
    return val is not None and bool(str(val).strip())


class ClienteUpdateData(BaseModel):
    nombres: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    direccion: Optional[str] = None
    ocupacion: Optional[str] = None
    estado: Optional[str] = None
    fecha_nacimiento: Optional[str] = None
    notas: Optional[str] = None

class PrestamoUpdateData(BaseModel):
    total_financiamiento: Optional[float] = Field(None, ge=0)
    numero_cuotas: Optional[int] = Field(None, ge=1, le=50)
    tasa_interes: Optional[float] = Field(None, ge=0)
    producto: Optional[str] = None
    observaciones: Optional[str] = None
    cedula: Optional[str] = None
    nombres: Optional[str] = None
    fecha_requerimiento: Optional[str] = None
    modalidad_pago: Optional[str] = None
    cuota_periodo: Optional[float] = Field(None, ge=0)
    fecha_base_calculo: Optional[str] = None
    fecha_aprobacion: Optional[str] = None
    estado: Optional[str] = None
    concesionario: Optional[str] = None
    analista: Optional[str] = None
    modelo_vehiculo: Optional[str] = None
    valor_activo: Optional[float] = Field(None, ge=0)
    usuario_proponente: Optional[str] = None
    usuario_aprobador: Optional[str] = None

class CuotaUpdateData(BaseModel):
    fecha_pago: Optional[str] = None
    fecha_vencimiento: Optional[str] = None
    monto: Optional[float] = Field(None, ge=0)
    total_pagado: Optional[float] = Field(None, ge=0)
    # [A1] Acepta mayúsculas y minúsculas; el endpoint normaliza a MAYÚSCULAS antes de guardar.
    estado: Optional[str] = Field(
        None,
        pattern="^(?i)(pendiente|parcial|vencido|mora|pagado|pago_adelantado|cancelada|PENDIENTE|PARCIAL|VENCIDO|MORA|PAGADO|PAGO_ADELANTADO|CANCELADA)$",
    )
    observaciones: Optional[str] = None

# ===== SCHEMAS RESPUESTA =====


class PrestamoDetalleRevision(BaseModel):
    prestamo_id: int
    cliente_id: int
    cedula: str
    nombres: str
    total_prestamo: float
    total_abonos: float
    saldo: float
    cuotas_pagadas: Optional[int] = None
    cuotas_total: Optional[int] = None
    cuotas_vencidas: int
    cuotas_morosas: int
    estado_revision: str
    fecha_revision: Optional[str] = None


class ResumenRevisionManual(BaseModel):
    total_prestamos: int
    prestamos_revisados: int
    prestamos_pendientes: int
    porcentaje_completado: float
    prestamos: List[PrestamoDetalleRevision]


def _safe_float(val) -> float:
    if val is None:
        return 0.0
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0


def _pago_no_conciliar_saldo_cero(pago: Pago) -> bool:
    """Pagos excluidos de conciliación forzada (misma familia que reaplicación FIFO)."""
    est = (pago.estado or "").strip().upper()
    if est in ("ANULADO_IMPORT", "DUPLICADO", "CANCELADO", "RECHAZADO", "REVERSADO"):
        return True
    if "ANUL" in est or "REVERS" in est:
        return True
    el = (pago.estado or "").strip().lower()
    if el in ("cancelado", "rechazado"):
        return True
    return False


def _aplicar_saldo_cero_si_corresponde(db: Session, prestamo: Prestamo) -> None:
    """
    Si total_prestamo = total_abonos (saldo cero) para ESTE préstamo, aplicar:
    - préstamo.estado: se mantiene (APROBADO, no FINALIZADO, para no romper reportes/KPIs)
    - cliente.estado = FINALIZADO (solo para este caso)
    - pagos operativos: conciliado=True, fecha_conciliacion=now (estado PAGADO si era PENDIENTE;
      evita chk_pagos_conciliado_pendiente_inconsistente en BD)
    - todas las cuotas: estado=pagado
    Cada préstamo se analiza por separado (no por cédula).
    Solo se ejecuta al confirmar en Revisión Manual.
    """
    total_prestamo = _safe_float(prestamo.total_financiamiento)
    cuotas = db.execute(select(Cuota).where(Cuota.prestamo_id == prestamo.id)).scalars().all()
    total_abonos = sum(_safe_float(c.total_pagado) for c in cuotas)
    if abs(total_prestamo - total_abonos) >= 0.01:
        return
    # Saldo cero: aplicar reglas (préstamo se mantiene APROBADO)
    cliente = db.get(Cliente, prestamo.cliente_id)
    if cliente:
        cliente.estado = "FINALIZADO"
    ahora = datetime.now()
    pagos = db.execute(select(Pago).where(Pago.prestamo_id == prestamo.id)).scalars().all()
    for pago in pagos:
        if _pago_no_conciliar_saldo_cero(pago):
            continue
        if (pago.estado or "").strip().upper() == "PENDIENTE":
            pago.estado = "PAGADO"
        pago.conciliado = True
        pago.fecha_conciliacion = ahora
    # Aplicar a cuotas cualquier pago conciliado que aún no tenga enlaces en cuota_pagos
    aplicar_pagos_pendientes_prestamo(prestamo.id, db)
    for cuota in cuotas:
        cuota.estado = "PAGADO"  # [A1] Usar MAYÚSCULAS para consistencia con el resto del backend


@router.get("/prestamos", response_model=ResumenRevisionManual)
def get_prestamos_revision_manual(
    db: Session = Depends(get_db),
    filtro_estado: Optional[str] = Query(None, description="pendiente, revisando o revisado"),
    cedula: Optional[str] = Query(None, description="Buscar por cédula (parcial)"),
    limit: int = Query(20, ge=1, le=100, description="Préstamos por página"),
    offset: int = Query(0, ge=0, description="Desplazamiento para paginación"),
):
    """
    Lista de préstamos para revisión manual. LIMIT en SQL para carga rápida.
    """
    hoy_lit = literal_column("(CURRENT_TIMESTAMP AT TIME ZONE 'America/Caracas')::date")
    dias_retraso = func.greatest(0, hoy_lit - Cuota.fecha_vencimiento)
    no_pago_completo = func.coalesce(Cuota.total_pagado, 0) < (Cuota.monto - 0.01)
    cedula_trim = cedula.strip() if cedula and cedula.strip() else None

    # 1. Query base: Prestamo LEFT JOIN RevisionManualPrestamo
    q_base = (
        select(Prestamo, RevisionManualPrestamo.estado_revision, RevisionManualPrestamo.fecha_revision)
        .outerjoin(RevisionManualPrestamo, RevisionManualPrestamo.prestamo_id == Prestamo.id)
        .order_by(Prestamo.id.desc())
    )
    if cedula_trim:
        q_base = q_base.where(Prestamo.cedula.ilike(f"%{cedula_trim}%"))

    # 2. Filtrar por estado si aplica (pendiente = sin registro o estado 'pendiente')
    if filtro_estado:
        if filtro_estado == "pendiente":
            q_base = q_base.where(
                (RevisionManualPrestamo.id.is_(None)) | (RevisionManualPrestamo.estado_revision == "pendiente")
            )
        else:
            q_base = q_base.where(RevisionManualPrestamo.estado_revision == filtro_estado)

    # 3. Count total (ligero, sin cargar filas)
    q_count = select(func.count()).select_from(q_base.subquery())
    total = db.scalar(q_count) or 0

    if total == 0:
        return ResumenRevisionManual(
            total_prestamos=0, prestamos_revisados=0, prestamos_pendientes=0,
            porcentaje_completado=0.0, prestamos=[]
        )

    # 4. Solo los prestamos de esta página (LIMIT/OFFSET en SQL)
    q_page = q_base.offset(offset).limit(limit)
    rows = db.execute(q_page).all()

    prestamo_ids = [r[0].id for r in rows]

    # 5. Agregados de cuotas solo para estos prestamos
    agg_subq = (
        select(
            Cuota.prestamo_id,
            func.coalesce(func.sum(Cuota.total_pagado), 0).label("total_abonos"),
            func.sum(
                case(
                    (
                        and_(no_pago_completo, dias_retraso >= 1, hoy_lit < (Cuota.fecha_vencimiento + literal_column("INTERVAL '4 months 1 day'"))),
                        1,
                    ),
                    else_=0,
                )
            ).label("vencidas"),
            func.sum(
                case(
                    (and_(no_pago_completo, hoy_lit >= (Cuota.fecha_vencimiento + literal_column("INTERVAL '4 months 1 day'"))), 1),
                    else_=0,
                )
            ).label("morosas"),
        )
        .where(Cuota.prestamo_id.in_(prestamo_ids))
        .group_by(Cuota.prestamo_id)
    )
    agg_rows = db.execute(agg_subq).all()
    agg_map = {r.prestamo_id: {"abonos": _safe_float(r.total_abonos), "vencidas": int(r.vencidas or 0), "morosas": int(r.morosas or 0)} for r in agg_rows}

    saldos_tabla = sum_saldo_pendiente_cuotas_tabla_amortizacion_ui(db, prestamo_ids)
    cuotas_pagadas_map = contar_cuotas_pagadas_tabla_amortizacion_ui(db, prestamo_ids)

    # 6. Construir respuesta
    prestamos_detalles: List[PrestamoDetalleRevision] = []
    for prestamo, estado_rev, fecha_rev in rows:
        estado_revision = estado_rev if estado_rev else "pendiente"
        fecha_revision = fecha_rev.isoformat() if fecha_rev else None
        agg = agg_map.get(prestamo.id, {"abonos": 0.0, "vencidas": 0, "morosas": 0})
        total_prestamo = _safe_float(prestamo.total_financiamiento)
        saldo = _safe_float(saldos_tabla.get(prestamo.id, 0.0))
        _cp = cuotas_pagadas_map.get(prestamo.id)
        prestamos_detalles.append(
            PrestamoDetalleRevision(
                prestamo_id=prestamo.id,
                cliente_id=prestamo.cliente_id,
                cedula=prestamo.cedula or "",
                nombres=prestamo.nombres or "",
                total_prestamo=total_prestamo,
                total_abonos=agg["abonos"],
                saldo=saldo,
                cuotas_pagadas=int(_cp[0]) if _cp is not None else None,
                cuotas_total=int(_cp[1]) if _cp is not None else None,
                cuotas_vencidas=agg["vencidas"],
                cuotas_morosas=agg["morosas"],
                estado_revision=estado_revision,
                fecha_revision=fecha_revision,
            )
        )

    # Totales: revisados según filtro
    if filtro_estado == "revisado":
        revisados = total
    elif filtro_estado in ("pendiente", "revisando"):
        revisados = 0
    else:
        q_revisados = (
            select(func.count())
            .select_from(Prestamo)
            .join(RevisionManualPrestamo, RevisionManualPrestamo.prestamo_id == Prestamo.id)
            .where(RevisionManualPrestamo.estado_revision == "revisado")
        )
        if cedula_trim:
            q_revisados = q_revisados.where(Prestamo.cedula.ilike(f"%{cedula_trim}%"))
        revisados = db.scalar(q_revisados) or 0
    porcentaje = (revisados / total * 100) if total > 0 else 0.0

    return ResumenRevisionManual(
        total_prestamos=total,
        prestamos_revisados=revisados,
        prestamos_pendientes=total - revisados,
        porcentaje_completado=round(porcentaje, 1),
        prestamos=prestamos_detalles,
    )


@router.put("/prestamos/{prestamo_id}/confirmar")
def confirmar_prestamo_revisado(
    prestamo_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Marca un préstamo como revisado (confirma TODO: cliente, préstamo, pagos)."""
    actor = _actor_revision_manual(current_user)
    prestamo = db.get(Prestamo, prestamo_id)
    if not prestamo:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")

    if prestamo_estado_exige_fecha_aprobacion(prestamo.estado) and prestamo.fecha_aprobacion is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "No se puede confirmar la revisión: el préstamo no tiene fecha de aprobación. "
                "Debe ingresarla manualmente antes de cerrar."
            ),
        )

    rev_manual = db.execute(
        select(RevisionManualPrestamo).where(RevisionManualPrestamo.prestamo_id == prestamo_id)
    ).scalars().first()
    
    if not rev_manual:
        rev_manual = RevisionManualPrestamo(
            prestamo_id=prestamo_id,
            estado_revision="revisado",
            usuario_revision_email=current_user.get("email") if isinstance(current_user, dict) else getattr(current_user, "email", None),
            fecha_revision=datetime.now(),
        )
        db.add(rev_manual)
    else:
        rev_manual.estado_revision = "revisado"
        rev_manual.usuario_revision_email = current_user.get("email") if isinstance(current_user, dict) else getattr(current_user, "email", None)
        rev_manual.fecha_revision = datetime.now()
    
    _aplicar_saldo_cero_si_corresponde(db, prestamo)
    _commit_revision_seguro(
        db,
        operacion="confirmar_prestamo_revisado",
        actor=actor,
        tabla_principal="revision_manual_prestamos+prestamos",
        id_principal=prestamo_id,
        resumen_campos=["estado_revision=revisado", "saldo_cero_reglas_si_aplica"],
    )
    return {
        "mensaje": "Usted ha auditado todos los términos de este préstamo por lo que no podrá editar de nuevo",
        "prestamo_id": prestamo_id,
        "estado": "revisado"
    }


@router.put("/prestamos/{prestamo_id}/iniciar-revision")
def iniciar_revision_prestamo(
    prestamo_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Inicia edición de un préstamo (cambia estado a 'revisando')."""
    actor = _actor_revision_manual(current_user)
    prestamo = db.get(Prestamo, prestamo_id)
    if not prestamo:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")
    
    rev_manual = db.execute(
        select(RevisionManualPrestamo).where(RevisionManualPrestamo.prestamo_id == prestamo_id)
    ).scalars().first()
    
    if not rev_manual:
        rev_manual = RevisionManualPrestamo(
            prestamo_id=prestamo_id,
            estado_revision="revisando",
        )
        db.add(rev_manual)
    else:
        prev = (rev_manual.estado_revision or "").strip().lower()
        if prev == "revisado" and not _usuario_es_admin_revision_manual(current_user):
            logger.warning(
                "revision_manual iniciar_revision rechazado prestamo_id=%s ya_revisado",
                prestamo_id,
            )
            raise HTTPException(
                status_code=403,
                detail=(
                    "La revisión de este préstamo ya fue cerrada (Visto). "
                    "Solo un administrador puede volver a ponerla en revisión."
                ),
            )
        rev_manual.estado_revision = "revisando"
    
    _commit_revision_seguro(
        db,
        operacion="iniciar_revision_prestamo",
        actor=actor,
        tabla_principal="revision_manual_prestamos",
        id_principal=prestamo_id,
        resumen_campos=["estado_revision=revisando"],
    )
    return {"mensaje": "Iniciada revisión manual", "prestamo_id": prestamo_id, "estado": "revisando"}


@router.put("/clientes/{cliente_id}")
def editar_cliente_revision(
    cliente_id: int,
    prestamo_id: Optional[int] = Query(
        None,
        description="ID del préstamo en contexto (editor revisión manual); valida coherencia y bloqueo si ya revisado",
    ),
    update_data: ClienteUpdateData = Body(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Edita datos del cliente y actualiza tabla de revisión manual."""
    actor = _actor_revision_manual(current_user)
    cliente = db.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    if prestamo_id is not None:
        pr = db.get(Prestamo, prestamo_id)
        if not pr or pr.cliente_id != cliente_id:
            raise HTTPException(
                status_code=400,
                detail="prestamo_id no corresponde a este cliente",
            )
        _validar_permiso_edicion(db, prestamo_id, current_user, actor)
    
    # Registrar cambios antiguos para auditoría
    cambios_dict = {}
    
    # Actualizar cliente solo si se proporcionan nuevos valores
    if update_data.nombres is not None and update_data.nombres.strip():
        cambios_dict['nombres'] = (cliente.nombres, update_data.nombres)
        cliente.nombres = update_data.nombres
    
    if update_data.telefono is not None and update_data.telefono.strip():
        cambios_dict['telefono'] = (cliente.telefono, update_data.telefono)
        cliente.telefono = update_data.telefono
    
    if update_data.email is not None and update_data.email.strip():
        cambios_dict['email'] = (cliente.email, update_data.email)
        cliente.email = update_data.email
    
    if update_data.direccion is not None and update_data.direccion.strip():
        cambios_dict['direccion'] = (cliente.direccion, update_data.direccion)
        cliente.direccion = update_data.direccion
    
    if update_data.ocupacion is not None and update_data.ocupacion.strip():
        cambios_dict['ocupacion'] = (cliente.ocupacion, update_data.ocupacion)
        cliente.ocupacion = update_data.ocupacion
    
    if update_data.estado is not None and update_data.estado.strip():
        estado_val = update_data.estado.strip().upper()
        try:
            permitidos = db.execute(select(EstadoCliente.valor)).scalars().all()
            if permitidos and estado_val not in permitidos:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        "Estado de cliente no permitido. "
                        f"Valores en catálogo: {sorted(permitidos)}"
                    ),
                )
        except HTTPException:
            raise
        except Exception:
            pass
        cambios_dict['estado'] = (cliente.estado, estado_val)
        cliente.estado = estado_val

    if update_data.fecha_nacimiento is not None:
        try:
            fecha_nac = datetime.strptime(update_data.fecha_nacimiento, "%Y-%m-%d").date()
            cambios_dict['fecha_nacimiento'] = (str(cliente.fecha_nacimiento), str(fecha_nac))
            cliente.fecha_nacimiento = fecha_nac
        except ValueError:
            pass

    if update_data.notas is not None:
        cambios_dict['notas'] = (cliente.notas, update_data.notas)
        cliente.notas = update_data.notas
    
    if not cambios_dict:
        return {"mensaje": "No hay cambios que guardar", "cliente_id": cliente_id}
    
    cliente.fecha_actualizacion = datetime.now()
    
    # Marcar en tabla de revisión que se editó cliente
    prestamos = db.execute(
        select(Prestamo).where(Prestamo.cliente_id == cliente_id)
    ).scalars().all()
    
    for prestamo in prestamos:
        rev_manual = db.execute(
            select(RevisionManualPrestamo).where(RevisionManualPrestamo.prestamo_id == prestamo.id)
        ).scalars().first()
        
        if rev_manual:
            rev_manual.cliente_editado = True
            rev_manual.actualizado_en = datetime.now()
    
    _commit_revision_seguro(
        db,
        operacion="editar_cliente_revision",
        actor=actor,
        tabla_principal="clientes",
        id_principal=cliente_id,
        resumen_campos=list(cambios_dict.keys()),
    )

    usuario_id = getattr(current_user, "id", None)
    if usuario_id:
        try:
            registrar_cambio(
                db=db,
                usuario_id=usuario_id,
                modulo="Revisión Manual",
                tipo_cambio="ACTUALIZAR",
                descripcion=f"Edición de cliente #{cliente_id} en revisión manual (préstamo #{prestamo_id})",
                registro_id=cliente_id,
                tabla_afectada="clientes",
                campos_anteriores={k: v[0] for k, v in cambios_dict.items()},
                campos_nuevos={k: v[1] for k, v in cambios_dict.items()},
            )
            db.commit()
        except Exception:
            logger.warning("revision_manual: no se pudo registrar auditoría edición cliente id=%s", cliente_id)

    return {
        "mensaje": "Cliente actualizado exitosamente",
        "cliente_id": cliente_id,
        "cambios": {k: {"anterior": v[0], "nuevo": v[1]} for k, v in cambios_dict.items()}
    }


def _mutar_prestamo_desde_update_data_revision(
    db: Session,
    prestamo: Prestamo,
    prestamo_id: int,
    update_data: PrestamoUpdateData,
) -> dict:
    """
    Aplica campos del body al ORM prestamo; no commit.
    Devuelve cambios_dict (vacío si nada cambió vs valores ya en memoria).
    """
    cambios_dict: dict = {}

    if update_data.total_financiamiento is not None and update_data.total_financiamiento >= 0:
        cambios_dict["total_financiamiento"] = (
            float(prestamo.total_financiamiento),
            update_data.total_financiamiento,
        )
        prestamo.total_financiamiento = update_data.total_financiamiento

    if update_data.numero_cuotas is not None and update_data.numero_cuotas >= 1:
        if update_data.numero_cuotas != prestamo.numero_cuotas:
            bloqueo_plazo = prestamo_bloquea_nuevas_cuotas_o_cambio_plazo(db, prestamo)
            if bloqueo_plazo:
                raise HTTPException(status_code=400, detail=bloqueo_plazo)
        cambios_dict["numero_cuotas"] = (prestamo.numero_cuotas, update_data.numero_cuotas)
        prestamo.numero_cuotas = update_data.numero_cuotas

    if update_data.tasa_interes is not None and update_data.tasa_interes >= 0:
        cambios_dict["tasa_interes"] = (float(prestamo.tasa_interes), update_data.tasa_interes)
        prestamo.tasa_interes = update_data.tasa_interes

    if update_data.producto is not None and update_data.producto.strip():
        cambios_dict["producto"] = (prestamo.producto, update_data.producto)
        prestamo.producto = update_data.producto

    if update_data.observaciones is not None:
        cambios_dict["observaciones"] = (prestamo.observaciones, update_data.observaciones)
        prestamo.observaciones = update_data.observaciones

    if update_data.nombres is not None and update_data.nombres.strip():
        cambios_dict["nombres"] = (prestamo.nombres, update_data.nombres.strip())
        prestamo.nombres = update_data.nombres.strip()

    if update_data.fecha_requerimiento is not None:
        try:
            fecha_req = datetime.strptime(update_data.fecha_requerimiento, "%Y-%m-%d").date()
            cambios_dict["fecha_requerimiento"] = (str(prestamo.fecha_requerimiento), str(fecha_req))
            prestamo.fecha_requerimiento = fecha_req
        except ValueError:
            pass

    if update_data.modalidad_pago is not None and update_data.modalidad_pago.strip():
        cambios_dict["modalidad_pago"] = (
            prestamo.modalidad_pago,
            update_data.modalidad_pago.strip().upper(),
        )
        prestamo.modalidad_pago = update_data.modalidad_pago.strip().upper()

    if update_data.cuota_periodo is not None and update_data.cuota_periodo >= 0:
        cambios_dict["cuota_periodo"] = (float(prestamo.cuota_periodo or 0), update_data.cuota_periodo)
        prestamo.cuota_periodo = update_data.cuota_periodo

    if _body_tiene_fecha_iso_no_vacia(update_data.fecha_base_calculo) and not _body_tiene_fecha_iso_no_vacia(
        update_data.fecha_aprobacion
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Indique fecha_aprobacion (YYYY-MM-DD) de forma explícita. "
                "No se actualiza la base de cálculo ni la amortización sin fecha de aprobación ingresada manualmente."
            ),
        )

    if update_data.fecha_aprobacion is not None:
        s_fa = (update_data.fecha_aprobacion or "").strip()
        if not s_fa:
            raise HTTPException(
                status_code=400,
                detail="La fecha de aprobación no puede estar vacía; indique una fecha válida (YYYY-MM-DD).",
            )
        try:
            fecha_ap = datetime.strptime(s_fa, "%Y-%m-%d")
            cambios_dict["fecha_aprobacion"] = (str(prestamo.fecha_aprobacion), str(fecha_ap))
            prestamo.fecha_aprobacion = fecha_ap
            fecha_base_nueva = fecha_ap.date()
            cambios_dict["fecha_base_calculo"] = (str(prestamo.fecha_base_calculo), str(fecha_base_nueva))
            prestamo.fecha_base_calculo = fecha_base_nueva
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail="fecha_aprobacion inválida; use formato YYYY-MM-DD.",
            ) from exc

    if update_data.estado is not None and update_data.estado.strip():
        cambios_dict["estado"] = (prestamo.estado, update_data.estado.strip().upper())
        prestamo.estado = update_data.estado.strip().upper()

    if update_data.concesionario is not None:
        cambios_dict["concesionario"] = (prestamo.concesionario, update_data.concesionario or "")
        prestamo.concesionario = update_data.concesionario or ""

    if update_data.analista is not None and update_data.analista.strip():
        cambios_dict["analista"] = (prestamo.analista, update_data.analista.strip())
        prestamo.analista = update_data.analista.strip()

    if update_data.modelo_vehiculo is not None:
        cambios_dict["modelo_vehiculo"] = (prestamo.modelo_vehiculo, update_data.modelo_vehiculo or "")
        prestamo.modelo_vehiculo = update_data.modelo_vehiculo or ""

    if update_data.valor_activo is not None and update_data.valor_activo >= 0:
        cambios_dict["valor_activo"] = (float(prestamo.valor_activo or 0), update_data.valor_activo)
        prestamo.valor_activo = update_data.valor_activo

    if update_data.usuario_proponente is not None and update_data.usuario_proponente.strip():
        cambios_dict["usuario_proponente"] = (
            prestamo.usuario_proponente,
            update_data.usuario_proponente.strip(),
        )
        prestamo.usuario_proponente = update_data.usuario_proponente.strip()

    if update_data.usuario_aprobador is not None:
        cambios_dict["usuario_aprobador"] = (
            prestamo.usuario_aprobador,
            update_data.usuario_aprobador or "",
        )
        prestamo.usuario_aprobador = update_data.usuario_aprobador or ""

    return cambios_dict


@router.put("/prestamos/{prestamo_id}")
def editar_prestamo_revision(
    prestamo_id: int,
    update_data: PrestamoUpdateData = Body(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Edita datos del préstamo y actualiza tabla de revisión manual."""
    actor = _actor_revision_manual(current_user)
    prestamo = db.get(Prestamo, prestamo_id)
    if not prestamo:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")

    _validar_permiso_edicion(db, prestamo_id, current_user, actor)

    # Misma regla que PUT prestamos: comparar fecha base de amortización antes/después.
    from app.api.v1.endpoints.prestamos import _fecha_para_amortizacion

    fecha_base_amort_antes = _fecha_para_amortizacion(prestamo)

    cambios_dict = _mutar_prestamo_desde_update_data_revision(db, prestamo, prestamo_id, update_data)

    if not cambios_dict:
        return {"mensaje": "No hay cambios que guardar", "prestamo_id": prestamo_id}

    rellenar_fecha_aprobacion_desde_base_si_falta(prestamo)
    alinear_fecha_aprobacion_y_base_calculo(prestamo)

    if prestamo_estado_exige_fecha_aprobacion(prestamo.estado) and prestamo.fecha_aprobacion is None:
        raise HTTPException(
            status_code=400,
            detail="Falta la fecha de aprobación. Los préstamos aprobados, desembolsados o liquidados deben tener fecha de aprobación.",
        )

    # Coherencia: fecha de aprobación debe ser >= fecha de requerimiento
    _req = getattr(prestamo, "fecha_requerimiento", None)
    _ap = getattr(prestamo, "fecha_aprobacion", None)
    if _req and _ap:
        req_date = _req.date() if hasattr(_req, "date") and callable(getattr(_req, "date", None)) else _req
        ap_date = _ap.date() if hasattr(_ap, "date") and callable(getattr(_ap, "date", None)) else _ap
        if req_date and ap_date and ap_date < req_date:
            raise HTTPException(
                status_code=400,
                detail=f"La fecha de aprobación ({ap_date}) debe ser igual o posterior a la fecha de requerimiento ({req_date}).",
            )

    try:
        asegurar_prestamo_alineado_con_cliente(db, prestamo)
    except PrestamoCedulaClienteError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    prestamo.fecha_actualizacion = datetime.now()

    marcar_o_crear_prestamo_editado_en_revision_manual(db, prestamo_id)

    from app.services.finiquito_caso_cleanup import (
        eliminar_finiquito_casos_si_prestamo_no_liquidado,
    )

    eliminar_finiquito_casos_si_prestamo_no_liquidado(
        db, prestamo_id, prestamo.estado
    )

    _commit_revision_seguro(
        db,
        operacion="editar_prestamo_revision",
        actor=actor,
        tabla_principal="prestamos",
        id_principal=prestamo_id,
        resumen_campos=list(cambios_dict.keys()),
    )

    resultado_recalc = None
    # Préstamo APROBADO o LIQUIDADO con cuotas: si cambió fecha_aprobacion/fecha_base_calculo, persistir nuevas fechas de vencimiento en cuotas (BD).
    if (prestamo.estado or "").strip().upper() in ("APROBADO", "LIQUIDADO"):
        existentes = (
            db.scalar(select(func.count()).select_from(Cuota).where(Cuota.prestamo_id == prestamo_id)) or 0
        )
        fecha_base = _fecha_para_amortizacion(prestamo)
        if existentes > 0 and fecha_base and fecha_base != fecha_base_amort_antes:
            from app.api.v1.endpoints.prestamos import _recalcular_fechas_vencimiento_cuotas

            logger.info(
                "[revision_manual] editar_prestamo: fecha base amortización %s -> %s; recalculando %s cuota(s), prestamo_id=%s",
                fecha_base_amort_antes,
                fecha_base,
                existentes,
                prestamo_id,
            )
            resultado_recalc = _recalcular_fechas_vencimiento_cuotas(db, prestamo, fecha_base)
            _fallback_uid = db.execute(text("SELECT id FROM public.usuarios ORDER BY id LIMIT 1")).scalar() or 1
            db.add(
                Auditoria(
                    usuario_id=_fallback_uid,
                    accion="RECALCULO_FECHAS_AMORTIZACION",
                    entidad="prestamos",
                    entidad_id=prestamo_id,
                    detalles=(
                        "Recalculo automatico de fechas de cuotas (revision_manual PUT prestamos). "
                        f"Fecha base anterior: {fecha_base_amort_antes}, nueva: {fecha_base}. "
                        f"Cuotas actualizadas: {resultado_recalc.get('actualizadas', 0)}"
                    ),
                    exito=True,
                )
            )
            db.commit()

    usuario_id = getattr(current_user, "id", None)
    if usuario_id:
        try:
            registrar_cambio(
                db=db,
                usuario_id=usuario_id,
                modulo="Revisión Manual",
                tipo_cambio="ACTUALIZAR",
                descripcion=f"Edición de préstamo #{prestamo_id} en revisión manual",
                registro_id=prestamo_id,
                tabla_afectada="prestamos",
                campos_anteriores={k: v[0] for k, v in cambios_dict.items()},
                campos_nuevos={k: v[1] for k, v in cambios_dict.items()},
            )
            db.commit()
        except Exception:
            logger.warning("revision_manual: no se pudo registrar auditoría edición préstamo id=%s", prestamo_id)

    out: dict = {
        "mensaje": "Préstamo actualizado exitosamente",
        "prestamo_id": prestamo_id,
        "cambios": {k: {"anterior": v[0], "nuevo": v[1]} for k, v in cambios_dict.items()},
    }
    if resultado_recalc is not None:
        out["recalculo_cuotas"] = resultado_recalc
    return out


@router.post("/prestamos/{prestamo_id}/guardar-prestamo-y-reconstruir-cuotas")
def guardar_prestamo_y_reconstruir_cuotas(
    prestamo_id: int,
    update_data: PrestamoUpdateData = Body(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Una sola transacción en BD: aplica el mismo cuerpo que PUT /prestamos/{id}
    y reconstruye la tabla de cuotas desde la fila préstamo (sin hueco entre guardado y cuotas).
    """
    actor = _actor_revision_manual(current_user)
    prestamo = db.get(Prestamo, prestamo_id)
    if not prestamo:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")

    _validar_permiso_edicion(db, prestamo_id, current_user, actor)

    from app.api.v1.endpoints.prestamos import (
        _reconstruir_tabla_cuotas_desde_prestamo_en_sesion,
    )

    cambios_dict = _mutar_prestamo_desde_update_data_revision(db, prestamo, prestamo_id, update_data)

    if not cambios_dict:
        prestamo.fecha_actualizacion = datetime.now()
        marcar_o_crear_prestamo_editado_en_revision_manual(db, prestamo_id)
    else:
        rellenar_fecha_aprobacion_desde_base_si_falta(prestamo)
        alinear_fecha_aprobacion_y_base_calculo(prestamo)

        if prestamo_estado_exige_fecha_aprobacion(prestamo.estado) and prestamo.fecha_aprobacion is None:
            raise HTTPException(
                status_code=400,
                detail="Falta la fecha de aprobación. Los préstamos aprobados, desembolsados o liquidados deben tener fecha de aprobación.",
            )

        _req = getattr(prestamo, "fecha_requerimiento", None)
        _ap = getattr(prestamo, "fecha_aprobacion", None)
        if _req and _ap:
            req_date = _req.date() if hasattr(_req, "date") and callable(getattr(_req, "date", None)) else _req
            ap_date = _ap.date() if hasattr(_ap, "date") and callable(getattr(_ap, "date", None)) else _ap
            if req_date and ap_date and ap_date < req_date:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"La fecha de aprobación ({ap_date}) debe ser igual o posterior a la fecha de "
                        f"requerimiento ({req_date})."
                    ),
                )

        try:
            asegurar_prestamo_alineado_con_cliente(db, prestamo)
        except PrestamoCedulaClienteError as e:
            raise HTTPException(status_code=400, detail=str(e)) from e

        prestamo.fecha_actualizacion = datetime.now()
        marcar_o_crear_prestamo_editado_en_revision_manual(db, prestamo_id)

        from app.services.finiquito_caso_cleanup import eliminar_finiquito_casos_si_prestamo_no_liquidado

        eliminar_finiquito_casos_si_prestamo_no_liquidado(db, prestamo_id, prestamo.estado)

    try:
        stats = _reconstruir_tabla_cuotas_desde_prestamo_en_sesion(db, prestamo_id)
    except HTTPException:
        db.rollback()
        raise

    creadas = int(stats.get("cuotas_creadas") or 0)
    pagos_aplicados = int(stats.get("pagos_con_aplicacion") or 0)
    elim = {k: v for k, v in stats.items() if k not in ("message", "cuotas_creadas", "pagos_con_aplicacion")}

    _fallback_uid = db.execute(text("SELECT id FROM public.usuarios ORDER BY id LIMIT 1")).scalar() or 1
    uid_audit = getattr(current_user, "id", None) or _fallback_uid

    db.add(
        Auditoria(
            usuario_id=int(uid_audit),
            accion="REVISION_MANUAL_GUARDAR_Y_RECONSTRUIR_CUOTAS",
            entidad="prestamos",
            entidad_id=prestamo_id,
            detalles=(
                "Revisión manual: préstamo y tabla de cuotas en una transacción. "
                f"Campos préstamo: {list(cambios_dict.keys()) if cambios_dict else 'sin cambios en fila'}. "
                f"Cuotas creadas: {creadas}. Pagos con nueva aplicación: {pagos_aplicados}. "
                f"Eliminadas (rowcount): {elim}"
            ),
            exito=True,
        )
    )

    _commit_revision_seguro(
        db,
        operacion="guardar_prestamo_y_reconstruir_cuotas",
        actor=actor,
        tabla_principal="prestamos",
        id_principal=prestamo_id,
        resumen_campos=(list(cambios_dict.keys()) if cambios_dict else []) + ["reconstruccion_cuotas"],
    )

    usuario_id = getattr(current_user, "id", None)
    if usuario_id:
        try:
            registrar_cambio(
                db=db,
                usuario_id=usuario_id,
                modulo="Revisión Manual",
                tipo_cambio="ACTUALIZAR",
                descripcion=(
                    f"Guardar préstamo y reconstruir cuotas #{prestamo_id}: "
                    f"{creadas} cuota(s); pagos con nueva aplicación: {pagos_aplicados}."
                ),
                registro_id=prestamo_id,
                tabla_afectada="prestamos,cuotas",
                campos_anteriores={k: v[0] for k, v in cambios_dict.items()} if cambios_dict else None,
                campos_nuevos={
                    **({k: v[1] for k, v in cambios_dict.items()} if cambios_dict else {}),
                    "reconstruccion": stats,
                },
            )
        except Exception:
            logger.warning(
                "revision_manual: no se pudo registrar_cambio guardar_y_reconstruir prestamo_id=%s",
                prestamo_id,
            )

    return {
        "mensaje": "Préstamo guardado y tabla de cuotas reconstruida en una sola operación.",
        "prestamo_id": prestamo_id,
        "cambios": {k: {"anterior": v[0], "nuevo": v[1]} for k, v in cambios_dict.items()},
        "reconstruccion_cuotas": stats,
    }


@router.delete("/prestamos/{prestamo_id}")
def eliminar_prestamo_revision(
    prestamo_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Elimina un préstamo y todos sus datos asociados de la BD:
    - Cuotas (instalaciones del crédito)
    - Pagos (registros de pago del crédito)
    - Revisión manual
    - Préstamo
    """
    actor = _actor_revision_manual(current_user)
    prestamo = db.get(Prestamo, prestamo_id)
    if not prestamo:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")

    # 1. Eliminar cuotas asociadas (antes que pagos, cuotas referencian pagos)
    cuotas = db.execute(select(Cuota).where(Cuota.prestamo_id == prestamo_id)).scalars().all()
    for cuota in cuotas:
        db.delete(cuota)

    # 2. Eliminar pagos asociados al crédito
    pagos = db.execute(select(Pago).where(Pago.prestamo_id == prestamo_id)).scalars().all()
    for pago in pagos:
        db.delete(pago)

    # 3. Eliminar registro de revisión manual
    rev_manual = db.execute(
        select(RevisionManualPrestamo).where(RevisionManualPrestamo.prestamo_id == prestamo_id)
    ).scalars().first()
    if rev_manual:
        db.delete(rev_manual)

    # 4. Eliminar préstamo
    db.delete(prestamo)
    n_cuotas = len(cuotas)
    n_pagos = len(pagos)
    _commit_revision_seguro(
        db,
        operacion="eliminar_prestamo_revision",
        actor=actor,
        tabla_principal="prestamos",
        id_principal=prestamo_id,
        resumen_campos=[f"cuotas_eliminadas={n_cuotas}", f"pagos_eliminados={n_pagos}"],
    )

    return {
        "mensaje": "Préstamo eliminado de la BD (préstamo, cuotas y pagos)",
        "prestamo_id": prestamo_id,
    }


@router.get("/pagos/{cedula}")
def get_pagos_por_cedula(
    cedula: str,
    db: Session = Depends(get_db),
):
    """Obtiene lista de pagos por cédula para edición."""
    prestamos = db.execute(
        select(Prestamo).where(Prestamo.cedula == cedula)
    ).scalars().all()
    
    prestamo_ids = [p.id for p in prestamos]
    if not prestamo_ids:
        raise HTTPException(status_code=404, detail="No hay préstamos para esta cédula")
    
    # Obtener cuotas y pagos
    cuotas = db.execute(
        select(Cuota).where(Cuota.prestamo_id.in_(prestamo_ids)).order_by(Cuota.fecha_vencimiento.desc())
    ).scalars().all()
    
    resultado = []
    for cuota in cuotas:
        resultado.append({
            "cuota_id": cuota.id,
            "prestamo_id": cuota.prestamo_id,
            "numero_cuota": cuota.numero_cuota,
            "monto": str(cuota.monto),
            "fecha_vencimiento": cuota.fecha_vencimiento.isoformat() if cuota.fecha_vencimiento else None,
            "fecha_pago": cuota.fecha_pago.isoformat() if cuota.fecha_pago else None,
            "total_pagado": str(cuota.total_pagado) if cuota.total_pagado else "0",
            "estado": cuota.estado,
        })
    
    return resultado


@router.put("/cuotas/{cuota_id}")
def editar_cuota_revision(
    cuota_id: int,
    update_data: CuotaUpdateData = Body(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Edita datos de una cuota (fecha_pago, cantidad, estado) y registra en revisión manual."""
    actor = _actor_revision_manual(current_user)
    cuota = db.get(Cuota, cuota_id)
    if not cuota:
        raise HTTPException(status_code=404, detail="Cuota no encontrada")

    _validar_permiso_edicion(db, cuota.prestamo_id, current_user, actor)
    
    cambios_dict = {}
    
    # Validar y actualizar fecha_pago
    if update_data.fecha_pago is not None:
        try:
            fecha_pago = datetime.strptime(update_data.fecha_pago, "%Y-%m-%d").date()
            cambios_dict['fecha_pago'] = (str(cuota.fecha_pago), str(fecha_pago))
            cuota.fecha_pago = fecha_pago
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha_pago inválido (YYYY-MM-DD)")

    # Validar y actualizar fecha_vencimiento
    if update_data.fecha_vencimiento is not None:
        try:
            fecha_venc = datetime.strptime(update_data.fecha_vencimiento, "%Y-%m-%d").date()
            cambios_dict['fecha_vencimiento'] = (str(cuota.fecha_vencimiento), str(fecha_venc))
            cuota.fecha_vencimiento = fecha_venc
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha_vencimiento inválido (YYYY-MM-DD)")

    # Validar y actualizar monto
    if update_data.monto is not None and update_data.monto >= 0:
        cambios_dict['monto'] = (float(cuota.monto or 0), update_data.monto)
        cuota.monto = update_data.monto

    # Validar y actualizar observaciones
    if update_data.observaciones is not None:
        cambios_dict['observaciones'] = (cuota.observaciones, update_data.observaciones)
        cuota.observaciones = update_data.observaciones
    
    # Validar y actualizar total_pagado
    if update_data.total_pagado is not None and update_data.total_pagado >= 0:
        cambios_dict['total_pagado'] = (float(cuota.total_pagado or 0), update_data.total_pagado)
        cuota.total_pagado = update_data.total_pagado
    
    # Validar y actualizar estado
    if update_data.estado is not None:
        # [A1] Normalizar siempre a MAYÚSCULAS antes de persistir
        estado_normalizado = update_data.estado.upper()
        estados_validos = [
            "PENDIENTE",
            "PARCIAL",
            "VENCIDO",
            "MORA",
            "PAGADO",
            "PAGO_ADELANTADO",
            "CANCELADA",
        ]
        if estado_normalizado not in estados_validos:
            raise HTTPException(status_code=400, detail=f"Estado inválido. Válidos: {estados_validos}")
        cambios_dict['estado'] = (cuota.estado, estado_normalizado)
        cuota.estado = estado_normalizado
    
    if not cambios_dict:
        return {"mensaje": "No hay cambios que guardar", "cuota_id": cuota_id}
    
    cuota.actualizado_en = datetime.now()
    
    # Marcar en tabla de revisión que se editó pago
    rev_manual = db.execute(
        select(RevisionManualPrestamo).where(RevisionManualPrestamo.prestamo_id == cuota.prestamo_id)
    ).scalars().first()
    
    if rev_manual:
        rev_manual.pagos_editados = True
        rev_manual.actualizado_en = datetime.now()
    else:
        rev_manual = RevisionManualPrestamo(
            prestamo_id=cuota.prestamo_id,
            estado_revision="revisando",
            pagos_editados=True,
        )
        db.add(rev_manual)
    
    _commit_revision_seguro(
        db,
        operacion="editar_cuota_revision",
        actor=actor,
        tabla_principal="cuotas",
        id_principal=cuota_id,
        resumen_campos=list(cambios_dict.keys()),
    )

    usuario_id = getattr(current_user, "id", None)
    if usuario_id:
        try:
            registrar_cambio(
                db=db,
                usuario_id=usuario_id,
                modulo="Revisión Manual",
                tipo_cambio="ACTUALIZAR",
                descripcion=f"Edición de cuota #{cuota_id} (préstamo #{cuota.prestamo_id}) en revisión manual",
                registro_id=cuota_id,
                tabla_afectada="cuotas",
                campos_anteriores={k: v[0] for k, v in cambios_dict.items()},
                campos_nuevos={k: v[1] for k, v in cambios_dict.items()},
            )
            db.commit()
        except Exception:
            logger.warning("revision_manual: no se pudo registrar auditoría edición cuota id=%s", cuota_id)

    return {
        "mensaje": "Cuota actualizada exitosamente (cambio parcial guardado)",
        "cuota_id": cuota_id,
        "cambios": {k: {"anterior": v[0], "nuevo": v[1]} for k, v in cambios_dict.items()}
    }


@router.delete("/prestamos/{prestamo_id}/cuotas/{cuota_id}")
def eliminar_cuota_revision(
    prestamo_id: int,
    cuota_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Elimina una cuota del préstamo (cuota_pagos y caches relacionados vía ON DELETE CASCADE). Marca revisión manual."""
    actor = _actor_revision_manual(current_user)
    cuota = db.get(Cuota, cuota_id)
    if not cuota or cuota.prestamo_id != prestamo_id:
        raise HTTPException(status_code=404, detail="Cuota no encontrada")

    _validar_permiso_edicion(db, prestamo_id, current_user, actor)

    db.delete(cuota)

    rev_manual = db.execute(
        select(RevisionManualPrestamo).where(RevisionManualPrestamo.prestamo_id == prestamo_id)
    ).scalars().first()

    if rev_manual:
        rev_manual.pagos_editados = True
        rev_manual.actualizado_en = datetime.now()
    else:
        rev_manual = RevisionManualPrestamo(
            prestamo_id=prestamo_id,
            estado_revision="revisando",
            pagos_editados=True,
        )
        db.add(rev_manual)

    _commit_revision_seguro(
        db,
        operacion="eliminar_cuota_revision",
        actor=actor,
        tabla_principal="cuotas",
        id_principal=cuota_id,
        resumen_campos=[f"prestamo_id={prestamo_id}"],
    )
    return {"mensaje": "Cuota eliminada", "cuota_id": cuota_id}


@router.get("/resumen-rapido")
def get_resumen_rapido_revision(db: Session = Depends(get_db)):
    """Resumen rápido: préstamos pendientes y revisando."""
    q_pendiente = select(func.count()).select_from(RevisionManualPrestamo).where(
        RevisionManualPrestamo.estado_revision == "pendiente"
    )
    q_revisando = select(func.count()).select_from(RevisionManualPrestamo).where(
        RevisionManualPrestamo.estado_revision == "revisando"
    )
    q_revisado = select(func.count()).select_from(RevisionManualPrestamo).where(
        RevisionManualPrestamo.estado_revision == "revisado"
    )
    q_en_espera = select(func.count()).select_from(RevisionManualPrestamo).where(
        RevisionManualPrestamo.estado_revision == "en_espera"
    )
    
    pendientes = db.scalar(q_pendiente) or 0
    revisando = db.scalar(q_revisando) or 0
    revisados = db.scalar(q_revisado) or 0
    en_espera = db.scalar(q_en_espera) or 0
    total = pendientes + revisando + revisados + en_espera
    
    return {
        "total_pendientes": pendientes,
        "total_revisando": revisando,
        "total_en_espera": en_espera,
        "total_revisados": revisados,
        "total": total,
        "porcentaje_completado": (revisados / total * 100) if total > 0 else 0.0
    }


class CambiarEstadoRevisionSchema(BaseModel):
    # Estados: revisando | en_espera | rechazado | revisado
    nuevo_estado: str
    observaciones: Optional[str] = None
    motivo_rechazo: Optional[str] = None


@router.patch("/prestamos/{prestamo_id}/estado-revision")
def cambiar_estado_revision(
    prestamo_id: int,
    payload: CambiarEstadoRevisionSchema,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """
    Cambia el estado de revisión de un préstamo.
    Flujo:
    - pendiente (⚠️) → revisando (?) : cualquier usuario al abrir formulario
    - revisando (?)  → revisando    : guardar cambios (guarda en BD, sigue revisando)
    - revisando (?)  → rechazado (✕): solo marca, pide motivo, no guarda cambios de formulario
    - revisando (?)  → revisado (✓) : guardar y cerrar (guarda todo, finaliza)
    - revisado (✓)   → revisando (?) : solo administrador reabre (el operario no puede salir de Visto)
    - rechazado (✕)  → revisando (?) : reabrir para corregir
    """
    actor = _actor_revision_manual(current_user)
    es_admin = _usuario_es_admin_revision_manual(current_user)

    ESTADOS_VALIDOS = {"revisando", "en_espera", "rechazado", "revisado"}
    if payload.nuevo_estado not in ESTADOS_VALIDOS:
        raise HTTPException(
            status_code=400,
            detail=f"Estado inválido. Permitidos: {', '.join(sorted(ESTADOS_VALIDOS))}"
        )

    if payload.nuevo_estado == "rechazado" and not (payload.motivo_rechazo or "").strip():
        raise HTTPException(
            status_code=400,
            detail="Debe proporcionar un motivo_rechazo para rechazar un préstamo."
        )

    rev_manual = db.execute(
        select(RevisionManualPrestamo).where(RevisionManualPrestamo.prestamo_id == prestamo_id)
    ).scalars().first()

    estado_actual = (rev_manual.estado_revision or "pendiente").strip().lower() if rev_manual else "pendiente"
    usuario_id = getattr(current_user, "id", None)
    usuario_email = getattr(current_user, "email", None)

    if estado_actual == "revisado" and payload.nuevo_estado != "revisado":
        if not es_admin:
            raise HTTPException(
                status_code=403,
                detail=(
                    "Solo un administrador puede cambiar el estado de una revisión cerrada (Visto); "
                    "por ejemplo reabrir como «En revisión» para que un operario vuelva a editar."
                ),
            )

    if not rev_manual:
        rev_manual = RevisionManualPrestamo(
            prestamo_id=prestamo_id,
            estado_revision=payload.nuevo_estado,
            usuario_revision_id=usuario_id,
            usuario_revision_email=usuario_email,
            observaciones=payload.observaciones,
            motivo_rechazo=payload.motivo_rechazo if payload.nuevo_estado == "rechazado" else None,
        )
        db.add(rev_manual)
    else:
        rev_manual.estado_revision = payload.nuevo_estado
        rev_manual.usuario_revision_id = usuario_id
        rev_manual.usuario_revision_email = usuario_email
        if payload.observaciones:
            rev_manual.observaciones = payload.observaciones

        if payload.nuevo_estado == "rechazado":
            rev_manual.motivo_rechazo = payload.motivo_rechazo
        elif payload.nuevo_estado == "revisado":
            rev_manual.fecha_revision = datetime.now()
            rev_manual.motivo_rechazo = None
        elif payload.nuevo_estado == "revisando":
            # Reapertura desde revisado o rechazado → limpiar cierre anterior
            rev_manual.fecha_revision = None
            rev_manual.motivo_rechazo = None

    rev_manual.actualizado_en = datetime.now()

    _commit_revision_seguro(
        db,
        operacion="cambiar_estado_revision",
        actor=actor,
        tabla_principal="revision_manual_prestamos",
        id_principal=prestamo_id,
        resumen_campos=[f"estado_revision={estado_actual}→{payload.nuevo_estado}"],
    )

    # Auditoría en registro_cambios
    if usuario_id:
        try:
            registrar_cambio(
                db=db,
                usuario_id=usuario_id,
                modulo="Revisión Manual",
                tipo_cambio="ACTUALIZAR",
                descripcion=f"Estado revisión manual: {estado_actual} → {payload.nuevo_estado}",
                registro_id=prestamo_id,
                tabla_afectada="revision_manual_prestamos",
                campos_anteriores={"estado_revision": estado_actual},
                campos_nuevos={
                    "estado_revision": payload.nuevo_estado,
                    "motivo_rechazo": payload.motivo_rechazo,
                },
            )
            db.commit()
        except Exception:
            logger.warning("revision_manual: no se pudo registrar auditoría de cambio de estado prestamo_id=%s", prestamo_id)

    return {
        "prestamo_id": prestamo_id,
        "estado_anterior": estado_actual,
        "nuevo_estado": payload.nuevo_estado,
        "mensaje": f"Estado actualizado de '{estado_actual}' a '{payload.nuevo_estado}'",
    }


# Estados de cliente: ver GET /api/v1/clientes/estados (tabla estados_cliente)


def _fecha_nacimiento_para_input(val) -> str:
    """Formato YYYY-MM-DD para input HTML date (evita ISO con componente de hora)."""
    if val is None:
        return ""
    if isinstance(val, datetime):
        return val.date().isoformat()
    if isinstance(val, date):
        return val.isoformat()
    s = str(val).strip()
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return s


@router.get("/prestamos/{prestamo_id}/detalle")
def get_detalle_prestamo_revision(
    prestamo_id: int,
    db: Session = Depends(get_db),
):
    """Obtiene datos completos de un préstamo para edición (cliente, préstamo, cuotas)."""
    prestamo = db.get(Prestamo, prestamo_id)
    if not prestamo:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")
    
    cliente = db.get(Cliente, prestamo.cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    rev_row = db.execute(
        select(RevisionManualPrestamo).where(RevisionManualPrestamo.prestamo_id == prestamo_id)
    ).scalars().first()
    estado_revision = "pendiente"
    fecha_revision_iso = None
    usuario_revision_email = None
    if rev_row:
        estado_revision = (rev_row.estado_revision or "pendiente").strip().lower()
        if rev_row.fecha_revision:
            fecha_revision_iso = rev_row.fecha_revision.isoformat()
        usuario_revision_email = rev_row.usuario_revision_email
    
    # Obtener cuotas
    cuotas = db.execute(
        select(Cuota).where(Cuota.prestamo_id == prestamo_id).order_by(Cuota.numero_cuota)
    ).scalars().all()
    
    def _norm_codigo_estado(raw: Optional[str], default: str) -> str:
        if raw is None or not str(raw).strip():
            return default
        return str(raw).strip().upper()

    cuotas_data = [
        {
            "cuota_id": c.id,
            "numero_cuota": c.numero_cuota,
            "monto": to_finite_float_or_zero(c.monto),
            "fecha_vencimiento": c.fecha_vencimiento.isoformat() if c.fecha_vencimiento else None,
            "fecha_pago": c.fecha_pago.isoformat() if c.fecha_pago else None,
            "total_pagado": to_finite_float_or_zero(c.total_pagado),
            "estado": _norm_codigo_estado(c.estado, "PENDIENTE"),
            "observaciones": c.observaciones or "",
            "saldo_capital_inicial": to_finite_float_or_zero(c.saldo_capital_inicial),
            "saldo_capital_final": to_finite_float_or_zero(c.saldo_capital_final),
        }
        for c in cuotas
    ]

    def _dt_iso(dt):
        """Convierte datetime/date a ISO format. Usa la versión centralizada."""
        return format_datetime_iso(dt)

    return {
        "revision": {
            "estado_revision": estado_revision,
            "fecha_revision": fecha_revision_iso,
            "usuario_revision_email": usuario_revision_email,
        },
        "cliente": {
            "cliente_id": cliente.id,
            "nombres": cliente.nombres,
            "cedula": cliente.cedula,
            "telefono": cliente.telefono or "",
            "email": cliente.email or "",
            "direccion": cliente.direccion or "",
            "ocupacion": cliente.ocupacion or "",
            "estado": _norm_codigo_estado(cliente.estado, ""),
            "fecha_nacimiento": _fecha_nacimiento_para_input(cliente.fecha_nacimiento),
            "notas": cliente.notas or "",
        },
        "prestamo": {
            "prestamo_id": prestamo.id,
            "cliente_id": prestamo.cliente_id,
            "cedula": prestamo.cedula or "",
            "nombres": prestamo.nombres or "",
            "total_financiamiento": to_finite_float_or_zero(prestamo.total_financiamiento),
            "numero_cuotas": prestamo.numero_cuotas or 0,
            "tasa_interes": to_finite_float_or_zero(prestamo.tasa_interes),
            "producto": prestamo.producto or "",
            "observaciones": prestamo.observaciones or "",
            "fecha_requerimiento": _dt_iso(prestamo.fecha_requerimiento),
            "modalidad_pago": prestamo.modalidad_pago or "",
            "cuota_periodo": to_finite_float_or_zero(prestamo.cuota_periodo),
            "fecha_base_calculo": _dt_iso(prestamo.fecha_base_calculo),
            "fecha_aprobacion": _dt_iso(prestamo.fecha_aprobacion),
            "estado": _norm_codigo_estado(prestamo.estado, ""),
            "concesionario": prestamo.concesionario or "",
            "analista": prestamo.analista or "",
            "modelo_vehiculo": prestamo.modelo_vehiculo or "",
            "valor_activo": to_finite_float(prestamo.valor_activo) if prestamo.valor_activo is not None else None,
            "usuario_proponente": prestamo.usuario_proponente or "",
            "usuario_aprobador": prestamo.usuario_aprobador or "",
        },
        "cuotas": cuotas_data,
    }


@router.put("/prestamos/{prestamo_id}/finalizar-revision")
def finalizar_revision_prestamo(
    prestamo_id: int,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Finaliza edición (Guardar y Cerrar) → marca como revisado."""
    actor = _actor_revision_manual(current_user)
    prestamo = db.get(Prestamo, prestamo_id)
    if not prestamo:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")

    if prestamo_estado_exige_fecha_aprobacion(prestamo.estado) and prestamo.fecha_aprobacion is None:
        raise HTTPException(
            status_code=400,
            detail=(
                "No se puede finalizar la revisión: falta la fecha de aprobación en el préstamo. "
                "Ingrese la fecha manualmente y guarde antes de cerrar."
            ),
        )

    rev_manual = db.execute(
        select(RevisionManualPrestamo).where(RevisionManualPrestamo.prestamo_id == prestamo_id)
    ).scalars().first()
    
    if not rev_manual:
        rev_manual = RevisionManualPrestamo(
            prestamo_id=prestamo_id,
            estado_revision="revisado",
            usuario_revision_email=current_user.get("email") if isinstance(current_user, dict) else getattr(current_user, "email", None),
            fecha_revision=datetime.now(),
        )
        db.add(rev_manual)
    else:
        rev_manual.estado_revision = "revisado"
        rev_manual.usuario_revision_email = current_user.get("email") if isinstance(current_user, dict) else getattr(current_user, "email", None)
        rev_manual.fecha_revision = datetime.now()
    
    _aplicar_saldo_cero_si_corresponde(db, prestamo)
    _commit_revision_seguro(
        db,
        operacion="finalizar_revision_prestamo",
        actor=actor,
        tabla_principal="revision_manual_prestamos+prestamos",
        id_principal=prestamo_id,
        resumen_campos=["estado_revision=revisado", "saldo_cero_reglas_si_aplica"],
    )
    return {
        "mensaje": "Usted ha auditado todos los términos de este préstamo por lo que no podrá editar de nuevo",
        "prestamo_id": prestamo_id,
        "estado": "revisado"
    }


# ----- Solicitudes de reapertura (operario en Visto → cola para administrador) -----


def _require_admin_para_autorizaciones_reapertura(current_user: Any) -> None:
    if not _usuario_es_admin_revision_manual(current_user):
        raise HTTPException(
            status_code=403,
            detail="Solo un administrador puede consultar o resolver autorizaciones de reapertura.",
        )


class SolicitarReaperturaRevisionBody(BaseModel):
    mensaje: Optional[str] = Field(None, max_length=2000)


class SolicitudReaperturaPendienteOut(BaseModel):
    id: int
    prestamo_id: int
    cedula: str
    nombres_cliente: str
    solicitante_nombre: str
    solicitante_apellido: str
    solicitante_email: Optional[str] = None
    mensaje: Optional[str] = None
    creado_en: str


class SolicitarReaperturaRevisionResponse(BaseModel):
    solicitud_id: int
    ya_registrada: bool
    mensaje: str


class ResolverSolicitudReaperturaBody(BaseModel):
    nota: Optional[str] = Field(None, max_length=2000)


@router.post(
    "/prestamos/{prestamo_id}/solicitar-reapertura-revision",
    response_model=SolicitarReaperturaRevisionResponse,
)
def solicitar_reapertura_revision_manual(
    prestamo_id: int,
    payload: SolicitarReaperturaRevisionBody = Body(default=SolicitarReaperturaRevisionBody()),
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """
    Operario u otro usuario no administrador: registra que necesita que un administrador reabra
    la revisión (préstamo en Visto / revisado). El administrador ve la cola en el módulo Autorizaciones.
    """
    actor = _actor_revision_manual(current_user)
    if _usuario_es_admin_revision_manual(current_user):
        raise HTTPException(
            status_code=400,
            detail="Los administradores pueden reabrir la revisión directamente; no deben usar esta solicitud.",
        )

    usuario_id = getattr(current_user, "id", None)
    usuario_email = getattr(current_user, "email", None)

    rev = db.execute(
        select(RevisionManualPrestamo).where(RevisionManualPrestamo.prestamo_id == prestamo_id)
    ).scalars().first()
    estado_rev = (rev.estado_revision or "pendiente").strip().lower() if rev else "pendiente"
    if not rev or estado_rev != "revisado":
        raise HTTPException(
            status_code=400,
            detail="Solo puede solicitar autorización cuando la revisión manual está cerrada en Visto (revisado).",
        )

    existente = db.execute(
        select(RevisionManualSolicitudReapertura).where(
            RevisionManualSolicitudReapertura.prestamo_id == prestamo_id,
            _solicitud_reapertura_estado_pendiente_sql(RevisionManualSolicitudReapertura.estado),
        )
    ).scalars().first()
    if existente:
        return SolicitarReaperturaRevisionResponse(
            solicitud_id=existente.id,
            ya_registrada=True,
            mensaje="Ya hay una solicitud pendiente para este préstamo. Un administrador la verá en Autorizaciones.",
        )

    msg = (payload.mensaje or "").strip() or None
    sol = RevisionManualSolicitudReapertura(
        prestamo_id=prestamo_id,
        solicitante_usuario_id=usuario_id if isinstance(usuario_id, int) else None,
        solicitante_email=usuario_email if isinstance(usuario_email, str) else None,
        mensaje=msg,
        estado="pendiente",
    )
    db.add(sol)
    _commit_revision_seguro(
        db,
        operacion="solicitar_reapertura_revision_manual",
        actor=actor,
        tabla_principal="revision_manual_solicitudes_reapertura",
        id_principal=prestamo_id,
        resumen_campos=[f"solicitud_prestamo_id={prestamo_id}"],
    )

    if isinstance(usuario_id, int):
        try:
            registrar_cambio(
                db=db,
                usuario_id=usuario_id,
                modulo="Revisión Manual",
                tipo_cambio="CREAR",
                descripcion=f"Solicitud de reapertura (Visto) préstamo #{prestamo_id}",
                registro_id=sol.id,
                tabla_afectada="revision_manual_solicitudes_reapertura",
                campos_anteriores=None,
                campos_nuevos={"prestamo_id": prestamo_id, "estado": "pendiente"},
            )
            db.commit()
        except Exception:
            logger.warning(
                "revision_manual: no se pudo registrar auditoría solicitud reapertura prestamo_id=%s",
                prestamo_id,
            )

    nom_solicitante = (
        current_user.get("nombre")
        if isinstance(current_user, dict)
        else getattr(current_user, "nombre", None)
    )
    ue = usuario_email if isinstance(usuario_email, str) else ""
    solicitante_etiqueta = f"{(nom_solicitante or '').strip()} {ue}".strip() or actor

    try:
        if getattr(sol, "id", None) is None:
            db.refresh(sol)
    except Exception:
        logger.warning("revision_manual: refresh solicitud reapertura para id falló prestamo_id=%s", prestamo_id)

    sid = getattr(sol, "id", None)
    if isinstance(sid, int):
        try:
            notify_admins_nueva_solicitud_reapertura(
                db,
                prestamo_id=prestamo_id,
                solicitante_etiqueta=solicitante_etiqueta,
                mensaje_opcional=msg,
                solicitud_id=sid,
            )
        except Exception:
            logger.exception(
                "revision_manual: aviso por correo a administradores falló (solicitud ok) prestamo_id=%s",
                prestamo_id,
            )
    else:
        logger.warning(
            "revision_manual: solicitud sin id tras commit; no se envía correo a admins prestamo_id=%s",
            prestamo_id,
        )

    return SolicitarReaperturaRevisionResponse(
        solicitud_id=sol.id,
        ya_registrada=False,
        mensaje=(
            "Solicitud registrada. Si el correo del sistema está configurado, los administradores reciben un aviso. "
            "Pueden aprobarla en Administración → Autorizaciones (revisión manual)."
        ),
    )


@router.get(
    "/autorizaciones-reapertura/pendientes",
    response_model=List[SolicitudReaperturaPendienteOut],
)
def listar_solicitudes_reapertura_pendientes(
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """Solo administrador: cola de solicitudes para reabrir revisiones en Visto."""
    _require_admin_para_autorizaciones_reapertura(current_user)

    SolUser = aliased(User)
    try:
        rows = db.execute(
            select(
                RevisionManualSolicitudReapertura,
                Prestamo.cedula,
                Prestamo.nombres,
                SolUser.nombre,
                SolUser.email,
            )
            .join(Prestamo, Prestamo.id == RevisionManualSolicitudReapertura.prestamo_id)
            .outerjoin(SolUser, SolUser.id == RevisionManualSolicitudReapertura.solicitante_usuario_id)
            .where(_solicitud_reapertura_estado_pendiente_sql(RevisionManualSolicitudReapertura.estado))
            .order_by(RevisionManualSolicitudReapertura.creado_en.desc())
        ).all()
    except ProgrammingError as exc:
        msg = str(getattr(exc, "orig", exc) or exc).lower()
        if "revision_manual_solicitudes_reapertura" in msg or "does not exist" in msg or "no such table" in msg:
            logger.exception(
                "revision_manual listar_solicitudes_reapertura: tabla ausente; migración 051 pendiente"
            )
            raise HTTPException(
                status_code=503,
                detail=(
                    "Falta la tabla de solicitudes de reapertura en la base de datos. "
                    "Ejecute la migración Alembic 051 (revision_manual_solicitudes_reapertura)."
                ),
            ) from exc
        raise

    out: List[SolicitudReaperturaPendienteOut] = []
    for sol, ced, nom_cli, sn, se in rows:
        creado = sol.creado_en.isoformat() if sol.creado_en else ""
        sn_clean = (sn or "").strip()
        if sn_clean:
            parts = sn_clean.rsplit(" ", 1)
            sol_nom = parts[0]
            sol_ape = parts[1] if len(parts) > 1 else ""
        else:
            sol_nom = ""
            sol_ape = ""
        out.append(
            SolicitudReaperturaPendienteOut(
                id=sol.id,
                prestamo_id=sol.prestamo_id,
                cedula=ced or "",
                nombres_cliente=nom_cli or "",
                solicitante_nombre=sol_nom or "—",
                solicitante_apellido=sol_ape,
                solicitante_email=se if se else (sol.solicitante_email or None),
                mensaje=sol.mensaje,
                creado_en=creado,
            )
        )
    return out


@router.patch("/autorizaciones-reapertura/{solicitud_id}/aprobar")
def aprobar_solicitud_reapertura_revision(
    solicitud_id: int,
    payload: ResolverSolicitudReaperturaBody = Body(default=ResolverSolicitudReaperturaBody()),
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """Administrador: aprueba y reabre la revisión manual (Visto → En revisión)."""
    _require_admin_para_autorizaciones_reapertura(current_user)
    actor = _actor_revision_manual(current_user)
    admin_id = getattr(current_user, "id", None)
    admin_email = getattr(current_user, "email", None)

    sol = db.get(RevisionManualSolicitudReapertura, solicitud_id)
    if not sol or (sol.estado or "").strip().lower() != "pendiente":
        raise HTTPException(status_code=404, detail="Solicitud no encontrada o ya resuelta.")

    rev = db.execute(
        select(RevisionManualPrestamo).where(RevisionManualPrestamo.prestamo_id == sol.prestamo_id)
    ).scalars().first()
    if not rev:
        raise HTTPException(status_code=409, detail="No existe registro de revisión manual para este préstamo.")
    estado_rev = (rev.estado_revision or "").strip().lower()
    if estado_rev != "revisado":
        raise HTTPException(
            status_code=409,
            detail="El préstamo ya no está en Visto (revisado). Revise el estado actual antes de aprobar.",
        )

    rev.estado_revision = "revisando"
    rev.fecha_revision = None
    rev.motivo_rechazo = None
    rev.usuario_revision_id = admin_id if isinstance(admin_id, int) else None
    rev.usuario_revision_email = admin_email if isinstance(admin_email, str) else None
    rev.actualizado_en = datetime.now()

    nota = (payload.nota or "").strip() or None
    sol.estado = "aprobada"
    sol.resuelto_por_usuario_id = admin_id if isinstance(admin_id, int) else None
    sol.resuelto_en = datetime.now()
    sol.nota_resolucion = nota
    sol.actualizado_en = datetime.now()

    _commit_revision_seguro(
        db,
        operacion="aprobar_solicitud_reapertura_revision",
        actor=actor,
        tabla_principal="revision_manual_solicitudes_reapertura",
        id_principal=solicitud_id,
        resumen_campos=[f"prestamo_id={sol.prestamo_id}", "reabrir=revisando"],
    )

    if isinstance(admin_id, int):
        try:
            registrar_cambio(
                db=db,
                usuario_id=admin_id,
                modulo="Revisión Manual",
                tipo_cambio="ACTUALIZAR",
                descripcion=f"Aprobó solicitud reapertura #{solicitud_id} → préstamo #{sol.prestamo_id} en revisión",
                registro_id=sol.prestamo_id,
                tabla_afectada="revision_manual_solicitudes_reapertura",
                campos_anteriores={"estado": "pendiente"},
                campos_nuevos={"estado": "aprobada", "prestamo_id": sol.prestamo_id},
            )
            db.commit()
        except Exception:
            logger.warning(
                "revision_manual: no se pudo registrar auditoría aprobar solicitud id=%s",
                solicitud_id,
            )

    operario_email: Optional[str] = None
    if isinstance(sol.solicitante_usuario_id, int):
        u_sol = db.get(User, sol.solicitante_usuario_id)
        if u_sol and isinstance(u_sol.email, str) and "@" in u_sol.email.strip():
            operario_email = u_sol.email.strip()
    if not operario_email and isinstance(sol.solicitante_email, str):
        se = sol.solicitante_email.strip()
        if "@" in se:
            operario_email = se
    admin_etiqueta = (
        admin_email if isinstance(admin_email, str) and admin_email.strip() else actor
    )
    try:
        notify_operario_solicitud_reapertura_aprobada(
            prestamo_id=sol.prestamo_id,
            operario_email=operario_email,
            admin_etiqueta=admin_etiqueta,
        )
    except Exception:
        logger.exception(
            "revision_manual: aviso por correo al operario falló (aprobación ok) prestamo_id=%s",
            sol.prestamo_id,
        )

    return {
        "mensaje": "Solicitud aprobada. La revisión quedó en «En revisión».",
        "prestamo_id": sol.prestamo_id,
        "solicitud_id": solicitud_id,
        "nuevo_estado_revision": "revisando",
    }


@router.patch("/autorizaciones-reapertura/{solicitud_id}/rechazar")
def rechazar_solicitud_reapertura_revision(
    solicitud_id: int,
    payload: ResolverSolicitudReaperturaBody = Body(default=ResolverSolicitudReaperturaBody()),
    db: Session = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    """Administrador: rechaza la solicitud; el préstamo permanece en Visto (revisado)."""
    _require_admin_para_autorizaciones_reapertura(current_user)
    actor = _actor_revision_manual(current_user)
    admin_id = getattr(current_user, "id", None)

    sol = db.get(RevisionManualSolicitudReapertura, solicitud_id)
    if not sol or (sol.estado or "").strip().lower() != "pendiente":
        raise HTTPException(status_code=404, detail="Solicitud no encontrada o ya resuelta.")

    nota = (payload.nota or "").strip() or None
    sol.estado = "rechazada"
    sol.resuelto_por_usuario_id = admin_id if isinstance(admin_id, int) else None
    sol.resuelto_en = datetime.now()
    sol.nota_resolucion = nota
    sol.actualizado_en = datetime.now()

    _commit_revision_seguro(
        db,
        operacion="rechazar_solicitud_reapertura_revision",
        actor=actor,
        tabla_principal="revision_manual_solicitudes_reapertura",
        id_principal=solicitud_id,
        resumen_campos=[f"prestamo_id={sol.prestamo_id}"],
    )

    if isinstance(admin_id, int):
        try:
            registrar_cambio(
                db=db,
                usuario_id=admin_id,
                modulo="Revisión Manual",
                tipo_cambio="ACTUALIZAR",
                descripcion=f"Rechazó solicitud reapertura #{solicitud_id} (préstamo #{sol.prestamo_id})",
                registro_id=sol.prestamo_id,
                tabla_afectada="revision_manual_solicitudes_reapertura",
                campos_anteriores={"estado": "pendiente"},
                campos_nuevos={"estado": "rechazada"},
            )
            db.commit()
        except Exception:
            logger.warning(
                "revision_manual: no se pudo registrar auditoría rechazar solicitud id=%s",
                solicitud_id,
            )

    return {
        "mensaje": "Solicitud rechazada. La revisión sigue en Visto (revisado).",
        "prestamo_id": sol.prestamo_id,
        "solicitud_id": solicitud_id,
    }
