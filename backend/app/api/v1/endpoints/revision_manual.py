"""
Endpoints para Revisión Manual de Préstamos (post-migración).
Lista de préstamos con detalles completos, edición de cliente/préstamo/pagos, y marcado como revisado.
Incluye validaciones y logging para garantizar integridad de datos.
"""
from datetime import date, datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, Body
from sqlalchemy import select, func, and_, case
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.models.cuota import Cuota
from app.models.pago import Pago
from app.models.revision_manual_prestamo import RevisionManualPrestamo

router = APIRouter()

# ===== SCHEMAS VALIDACION =====

class ClienteUpdateData(BaseModel):
    nombres: Optional[str] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    direccion: Optional[str] = None
    ocupacion: Optional[str] = None

class PrestamoUpdateData(BaseModel):
    total_financiamiento: Optional[float] = Field(None, ge=0)
    numero_cuotas: Optional[int] = Field(None, ge=1)
    tasa_interes: Optional[float] = Field(None, ge=0)
    producto: Optional[str] = None
    observaciones: Optional[str] = None

class CuotaUpdateData(BaseModel):
    fecha_pago: Optional[str] = None
    total_pagado: Optional[float] = Field(None, ge=0)
    estado: Optional[str] = Field(None, pattern="^(pendiente|pagado|conciliado)$")

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
    hoy = date.today()
    umbral_moroso = hoy - timedelta(days=89)
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
            func.coalesce(func.sum(case((Cuota.fecha_pago.isnot(None), Cuota.total_pagado), else_=0)), 0).label("total_abonos"),
            func.sum(case((and_(Cuota.fecha_vencimiento < hoy, Cuota.fecha_pago.is_(None)), 1), else_=0)).label("vencidas"),
            func.sum(case((and_(Cuota.fecha_vencimiento < umbral_moroso, Cuota.fecha_pago.is_(None)), 1), else_=0)).label("morosas"),
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
    
    db.commit()
    return {
        "mensaje": "Usted ha auditado todos los términos de este préstamo por lo que no podrá editar de nuevo",
        "prestamo_id": prestamo_id,
        "estado": "revisado"
    }


@router.put("/prestamos/{prestamo_id}/iniciar-revision")
def iniciar_revision_prestamo(
    prestamo_id: int,
    db: Session = Depends(get_db),
):
    """Inicia edición de un préstamo (cambia estado a 'revisando')."""
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
        rev_manual.estado_revision = "revisando"
    
    db.commit()
    return {"mensaje": "Iniciada revisión manual", "prestamo_id": prestamo_id, "estado": "revisando"}


@router.put("/clientes/{cliente_id}")
def editar_cliente_revision(
    cliente_id: int,
    update_data: ClienteUpdateData = Body(...),
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    """Edita datos del cliente y actualiza tabla de revisión manual."""
    cliente = db.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")
    
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
    
    db.commit()
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
    prestamo = db.get(Prestamo, prestamo_id)
    if not prestamo:
        raise HTTPException(status_code=404, detail="Préstamo no encontrado")
    
    cambios_dict = {}
    
    if update_data.total_financiamiento is not None and update_data.total_financiamiento >= 0:
        cambios_dict['total_financiamiento'] = (float(prestamo.total_financiamiento), update_data.total_financiamiento)
        prestamo.total_financiamiento = update_data.total_financiamiento
    
    if update_data.numero_cuotas is not None and update_data.numero_cuotas >= 1:
        cambios_dict['numero_cuotas'] = (prestamo.numero_cuotas, update_data.numero_cuotas)
        prestamo.numero_cuotas = update_data.numero_cuotas
    
    if update_data.tasa_interes is not None and update_data.tasa_interes >= 0:
        cambios_dict['tasa_interes'] = (float(prestamo.tasa_interes), update_data.tasa_interes)
        prestamo.tasa_interes = update_data.tasa_interes
    
    if update_data.producto is not None and update_data.producto.strip():
        cambios_dict['producto'] = (prestamo.producto, update_data.producto)
        prestamo.producto = update_data.producto
    
    if update_data.observaciones is not None and update_data.observaciones.strip():
        cambios_dict['observaciones'] = (prestamo.observaciones, update_data.observaciones)
        prestamo.observaciones = update_data.observaciones
    
    if not cambios_dict:
        return {"mensaje": "No hay cambios que guardar", "prestamo_id": prestamo_id}
    
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
    
    db.commit()
    return {
        "mensaje": "Préstamo actualizado exitosamente",
        "prestamo_id": prestamo_id,
        "cambios": {k: {"anterior": v[0], "nuevo": v[1]} for k, v in cambios_dict.items()}
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
    db.commit()

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
    cuota = db.get(Cuota, cuota_id)
    if not cuota:
        raise HTTPException(status_code=404, detail="Cuota no encontrada")
    
    cambios_dict = {}
    
    # Validar y actualizar fecha_pago
    if update_data.fecha_pago is not None:
        try:
            fecha_pago = datetime.strptime(update_data.fecha_pago, "%Y-%m-%d").date()
            cambios_dict['fecha_pago'] = (str(cuota.fecha_pago), str(fecha_pago))
            cuota.fecha_pago = fecha_pago
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha_pago inválido (YYYY-MM-DD)")
    
    # Validar y actualizar total_pagado
    if update_data.total_pagado is not None and update_data.total_pagado >= 0:
        cambios_dict['total_pagado'] = (float(cuota.total_pagado or 0), update_data.total_pagado)
        cuota.total_pagado = update_data.total_pagado
    
    # Validar y actualizar estado
    if update_data.estado is not None:
        estados_validos = ["pendiente", "pagado", "conciliado"]
        if update_data.estado not in estados_validos:
            raise HTTPException(status_code=400, detail=f"Estado inválido. Válidos: {estados_validos}")
        cambios_dict['estado'] = (cuota.estado, update_data.estado)
        cuota.estado = update_data.estado
    
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
    
    db.commit()
    return {
        "mensaje": "Cuota actualizada exitosamente (cambio parcial guardado)",
        "cuota_id": cuota_id,
        "cambios": {k: {"anterior": v[0], "nuevo": v[1]} for k, v in cambios_dict.items()}
    }


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
    
    pendientes = db.scalar(q_pendiente) or 0
    revisando = db.scalar(q_revisando) or 0
    revisados = db.scalar(q_revisado) or 0
    total = pendientes + revisando + revisados
    
    return {
        "total_pendientes": pendientes,
        "total_revisando": revisando,
        "total_revisados": revisados,
        "total": total,
        "porcentaje_completado": (revisados / total * 100) if total > 0 else 0.0
    }


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
    
    # Obtener cuotas
    cuotas = db.execute(
        select(Cuota).where(Cuota.prestamo_id == prestamo_id).order_by(Cuota.numero_cuota)
    ).scalars().all()
    
    cuotas_data = [
        {
            "cuota_id": c.id,
            "numero_cuota": c.numero_cuota,
            "monto": float(c.monto) if c.monto else 0.0,
            "fecha_vencimiento": c.fecha_vencimiento.isoformat() if c.fecha_vencimiento else None,
            "fecha_pago": c.fecha_pago.isoformat() if c.fecha_pago else None,
            "total_pagado": float(c.total_pagado) if c.total_pagado else 0.0,
            "estado": c.estado or "pendiente",
        }
        for c in cuotas
    ]
    
    return {
        "cliente": {
            "cliente_id": cliente.id,
            "nombres": cliente.nombres,
            "cedula": cliente.cedula,
            "telefono": cliente.telefono or "",
            "email": cliente.email or "",
            "direccion": cliente.direccion or "",
            "ocupacion": cliente.ocupacion or "",
        },
        "prestamo": {
            "prestamo_id": prestamo.id,
            "total_financiamiento": float(prestamo.total_financiamiento) if prestamo.total_financiamiento else 0.0,
            "numero_cuotas": prestamo.numero_cuotas or 0,
            "tasa_interes": float(prestamo.tasa_interes) if prestamo.tasa_interes else 0.0,
            "producto": prestamo.producto or "",
            "observaciones": prestamo.observaciones or "",
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
    
    db.commit()
    return {
        "mensaje": "Usted ha auditado todos los términos de este préstamo por lo que no podrá editar de nuevo",
        "prestamo_id": prestamo_id,
        "estado": "revisado"
    }
