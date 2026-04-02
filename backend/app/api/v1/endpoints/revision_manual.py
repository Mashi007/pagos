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
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.deps import get_current_user
from app.constants.prestamo_estados import prestamo_estado_exige_fecha_aprobacion
from app.services.prestamos.fechas_prestamo_coherencia import (
    alinear_fecha_aprobacion_y_base_calculo,
)
from app.core.serializers import to_float, format_datetime_iso
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.models.cuota import Cuota
from app.models.pago import Pago
from app.models.revision_manual_prestamo import RevisionManualPrestamo
from app.models.auditoria import Auditoria
from app.models.estado_cliente import EstadoCliente
from app.api.v1.endpoints.pagos import aplicar_pagos_pendientes_prestamo
from app.services.prestamo_estado_coherencia import prestamo_bloquea_nuevas_cuotas_o_cambio_plazo
from app.services.prestamos.prestamo_cedula_cliente_coherencia import (
    PrestamoCedulaClienteError,
    asegurar_prestamo_alineado_con_cliente,
)
from app.services.registro_cambios_service import registrar_cambio

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])


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
        raise HTTPException(
            status_code=500,
            detail="Error al persistir en la base de datos. Los cambios no se aplicaron.",
        ) from exc
    logger.info(
        "revision_manual BD_GUARDADO operacion=%s tabla=%s id=%s actor=%s campos=%s",
        operacion,
        tabla_principal,
        id_principal,
        actor,
        resumen_campos or [],
    )


def _forbid_si_prestamo_revision_cerrada(db: Session, prestamo_id: int) -> None:
    """Evita mutar préstamo/cuotas si la revisión manual ya se cerró como revisado."""
    rev = db.execute(
        select(RevisionManualPrestamo).where(RevisionManualPrestamo.prestamo_id == prestamo_id)
    ).scalars().first()
    if rev and (rev.estado_revision or "").strip().lower() == "revisado":
        logger.warning(
            "revision_manual EDICION_RECHAZADA prestamo_id=%s motivo=revisado_cerrado",
            prestamo_id,
        )
        raise HTTPException(
            status_code=403,
            detail="Este préstamo ya fue revisado y cerrado; no admite más ediciones en revisión manual.",
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
    - ✓ REVISADO: Nadie puede editar (solo admin desde BD)
    - ❓ REVISANDO: Solo admin
    - ⚠️ PENDIENTE, ❌ EN ESPERA: Todos
    """
    rev = db.execute(
        select(RevisionManualPrestamo).where(RevisionManualPrestamo.prestamo_id == prestamo_id)
    ).scalars().first()
    
    if not rev:
        # Si no existe registro de revisión, permitir
        return
    
    estado = (rev.estado_revision or "").strip().lower()
    rol_user = (getattr(current_user, "rol", "") or "").strip().lower()
    es_admin = rol_user == "admin"
    
    # ✓ REVISADO: Nadie puede editar
    if estado == "revisado":
        logger.warning(
            "revision_manual EDICION_RECHAZADA prestamo_id=%s motivo=revisado_cerrado actor=%s",
            prestamo_id,
            actor,
        )
        raise HTTPException(
            status_code=403,
            detail="Este préstamo ya fue revisado y cerrado; no admite más ediciones.",
        )
    
    # ❓ REVISANDO: Solo admin
    if estado == "revisando" and not es_admin:
        logger.warning(
            "revision_manual EDICION_RECHAZADA prestamo_id=%s motivo=revisando_solo_admin actor=%s",
            prestamo_id,
            actor,
        )
        raise HTTPException(
            status_code=403,
            detail="Este préstamo está en revisión. Solo administradores pueden editar en este estado. Contacta con tu administrador.",
        )


# ===== SCHEMAS VALIDACION =====

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


def _aplicar_saldo_cero_si_corresponde(db: Session, prestamo: Prestamo) -> None:
    """
    Si total_prestamo = total_abonos (saldo cero) para ESTE préstamo, aplicar:
    - préstamo.estado: se mantiene (APROBADO, no FINALIZADO, para no romper reportes/KPIs)
    - cliente.estado = FINALIZADO (solo para este caso)
    - todos los pagos: conciliado=True, fecha_conciliacion=now
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

    # 6. Construir respuesta
    prestamos_detalles: List[PrestamoDetalleRevision] = []
    for prestamo, estado_rev, fecha_rev in rows:
        estado_revision = estado_rev if estado_rev else "pendiente"
        fecha_revision = fecha_rev.isoformat() if fecha_rev else None
        agg = agg_map.get(prestamo.id, {"abonos": 0.0, "vencidas": 0, "morosas": 0})
        total_prestamo = _safe_float(prestamo.total_financiamiento)
        saldo = total_prestamo - agg["abonos"]
        prestamos_detalles.append(
            PrestamoDetalleRevision(
                prestamo_id=prestamo.id,
                cliente_id=prestamo.cliente_id,
                cedula=prestamo.cedula or "",
                nombres=prestamo.nombres or "",
                total_prestamo=total_prestamo,
                total_abonos=agg["abonos"],
                saldo=saldo,
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
        if prev == "revisado":
            logger.warning(
                "revision_manual iniciar_revision rechazado prestamo_id=%s ya_revisado",
                prestamo_id,
            )
            raise HTTPException(
                status_code=403,
                detail="La revisión de este préstamo ya fue cerrada; no se puede volver a iniciar.",
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

    cambios_dict = {}
    
    if update_data.total_financiamiento is not None and update_data.total_financiamiento >= 0:
        cambios_dict['total_financiamiento'] = (float(prestamo.total_financiamiento), update_data.total_financiamiento)
        prestamo.total_financiamiento = update_data.total_financiamiento
    
    if update_data.numero_cuotas is not None and update_data.numero_cuotas >= 1:
        if update_data.numero_cuotas != prestamo.numero_cuotas:
            bloqueo_plazo = prestamo_bloquea_nuevas_cuotas_o_cambio_plazo(db, prestamo)
            if bloqueo_plazo:
                raise HTTPException(status_code=400, detail=bloqueo_plazo)
        cambios_dict['numero_cuotas'] = (prestamo.numero_cuotas, update_data.numero_cuotas)
        prestamo.numero_cuotas = update_data.numero_cuotas
    
    if update_data.tasa_interes is not None and update_data.tasa_interes >= 0:
        cambios_dict['tasa_interes'] = (float(prestamo.tasa_interes), update_data.tasa_interes)
        prestamo.tasa_interes = update_data.tasa_interes
    
    if update_data.producto is not None and update_data.producto.strip():
        cambios_dict['producto'] = (prestamo.producto, update_data.producto)
        prestamo.producto = update_data.producto
    
    if update_data.observaciones is not None:
        cambios_dict['observaciones'] = (prestamo.observaciones, update_data.observaciones)
        prestamo.observaciones = update_data.observaciones

    # La cedula del prestamo debe coincidir con la del cliente; no se edita aqui (use ficha cliente).

    if update_data.nombres is not None and update_data.nombres.strip():
        cambios_dict['nombres'] = (prestamo.nombres, update_data.nombres.strip())
        prestamo.nombres = update_data.nombres.strip()

    if update_data.fecha_requerimiento is not None:
        try:
            fecha_req = datetime.strptime(update_data.fecha_requerimiento, "%Y-%m-%d").date()
            cambios_dict['fecha_requerimiento'] = (str(prestamo.fecha_requerimiento), str(fecha_req))
            prestamo.fecha_requerimiento = fecha_req
        except ValueError:
            pass

    if update_data.modalidad_pago is not None and update_data.modalidad_pago.strip():
        cambios_dict['modalidad_pago'] = (prestamo.modalidad_pago, update_data.modalidad_pago.strip().upper())
        prestamo.modalidad_pago = update_data.modalidad_pago.strip().upper()

    if update_data.cuota_periodo is not None and update_data.cuota_periodo >= 0:
        cambios_dict['cuota_periodo'] = (float(prestamo.cuota_periodo or 0), update_data.cuota_periodo)
        prestamo.cuota_periodo = update_data.cuota_periodo

    if update_data.fecha_base_calculo is not None:
        try:
            fecha_base = datetime.strptime(update_data.fecha_base_calculo, "%Y-%m-%d").date()
            cambios_dict['fecha_base_calculo'] = (str(prestamo.fecha_base_calculo), str(fecha_base))
            prestamo.fecha_base_calculo = fecha_base
            # Alineacion con fecha de aprobacion (misma fecha calendario)
            prestamo.fecha_aprobacion = datetime.combine(fecha_base, datetime.min.time())
        except ValueError:
            pass

    if update_data.fecha_aprobacion is not None:
        try:
            fecha_ap = datetime.strptime(update_data.fecha_aprobacion, "%Y-%m-%d")
            cambios_dict['fecha_aprobacion'] = (str(prestamo.fecha_aprobacion), str(fecha_ap))
            prestamo.fecha_aprobacion = fecha_ap
            # fecha_base_calculo siempre igual a fecha_aprobacion
            fecha_base_nueva = fecha_ap.date()
            cambios_dict['fecha_base_calculo'] = (str(prestamo.fecha_base_calculo), str(fecha_base_nueva))
            prestamo.fecha_base_calculo = fecha_base_nueva
        except ValueError:
            pass

    if update_data.estado is not None and update_data.estado.strip():
        cambios_dict['estado'] = (prestamo.estado, update_data.estado.strip().upper())
        prestamo.estado = update_data.estado.strip().upper()

    if update_data.concesionario is not None:
        cambios_dict['concesionario'] = (prestamo.concesionario, update_data.concesionario or "")
        prestamo.concesionario = update_data.concesionario or ""

    if update_data.analista is not None and update_data.analista.strip():
        cambios_dict['analista'] = (prestamo.analista, update_data.analista.strip())
        prestamo.analista = update_data.analista.strip()

    if update_data.modelo_vehiculo is not None:
        cambios_dict['modelo_vehiculo'] = (prestamo.modelo_vehiculo, update_data.modelo_vehiculo or "")
        prestamo.modelo_vehiculo = update_data.modelo_vehiculo or ""

    if update_data.valor_activo is not None and update_data.valor_activo >= 0:
        cambios_dict['valor_activo'] = (float(prestamo.valor_activo or 0), update_data.valor_activo)
        prestamo.valor_activo = update_data.valor_activo

    if update_data.usuario_proponente is not None and update_data.usuario_proponente.strip():
        cambios_dict['usuario_proponente'] = (prestamo.usuario_proponente, update_data.usuario_proponente.strip())
        prestamo.usuario_proponente = update_data.usuario_proponente.strip()

    if update_data.usuario_aprobador is not None:
        cambios_dict['usuario_aprobador'] = (prestamo.usuario_aprobador, update_data.usuario_aprobador or "")
        prestamo.usuario_aprobador = update_data.usuario_aprobador or ""
    
    if not cambios_dict:
        return {"mensaje": "No hay cambios que guardar", "prestamo_id": prestamo_id}

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
    
    # Marcar en tabla de revisión que se editó préstamo
    rev_manual = db.execute(
        select(RevisionManualPrestamo).where(RevisionManualPrestamo.prestamo_id == prestamo_id)
    ).scalars().first()
    
    if rev_manual:
        rev_manual.prestamo_editado = True
        rev_manual.actualizado_en = datetime.now()
    else:
        rev_manual = RevisionManualPrestamo(
            prestamo_id=prestamo_id,
            estado_revision="revisando",
            prestamo_editado=True,
        )
        db.add(rev_manual)
    
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
    - revisado (✓)   → revisando (?) : cualquier usuario reabre (visto es nuevo punto de inicio)
    - rechazado (✕)  → revisando (?) : reabrir para corregir
    """
    actor = _actor_revision_manual(current_user)
    rol_user = (getattr(current_user, "rol", "") or "").strip().lower()
    es_admin = rol_user == "admin"

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
            "monto": float(c.monto) if c.monto else 0.0,
            "fecha_vencimiento": c.fecha_vencimiento.isoformat() if c.fecha_vencimiento else None,
            "fecha_pago": c.fecha_pago.isoformat() if c.fecha_pago else None,
            "total_pagado": float(c.total_pagado) if c.total_pagado else 0.0,
            "estado": _norm_codigo_estado(c.estado, "PENDIENTE"),
            "observaciones": c.observaciones or "",
            "saldo_capital_inicial": float(c.saldo_capital_inicial) if c.saldo_capital_inicial else 0.0,
            "saldo_capital_final": float(c.saldo_capital_final) if c.saldo_capital_final else 0.0,
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
            "total_financiamiento": float(prestamo.total_financiamiento) if prestamo.total_financiamiento else 0.0,
            "numero_cuotas": prestamo.numero_cuotas or 0,
            "tasa_interes": float(prestamo.tasa_interes) if prestamo.tasa_interes else 0.0,
            "producto": prestamo.producto or "",
            "observaciones": prestamo.observaciones or "",
            "fecha_requerimiento": _dt_iso(prestamo.fecha_requerimiento),
            "modalidad_pago": prestamo.modalidad_pago or "",
            "cuota_periodo": float(prestamo.cuota_periodo) if prestamo.cuota_periodo else 0.0,
            "fecha_base_calculo": _dt_iso(prestamo.fecha_base_calculo),
            "fecha_aprobacion": _dt_iso(prestamo.fecha_aprobacion),
            "estado": _norm_codigo_estado(prestamo.estado, ""),
            "concesionario": prestamo.concesionario or "",
            "analista": prestamo.analista or "",
            "modelo_vehiculo": prestamo.modelo_vehiculo or "",
            "valor_activo": float(prestamo.valor_activo) if prestamo.valor_activo else None,
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
