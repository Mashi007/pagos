"""

Endpoints para pagos_con_errores: pagos con errores de validación desde Carga Masiva.

Revisar Pagos y front apuntan a esta tabla. No se mezclan con pagos que cumplen validadores.

"""

import logging

from datetime import date, datetime, time as dt_time

from typing import Any, Optional

from zoneinfo import ZoneInfo



from fastapi import APIRouter, Depends, Query, HTTPException, Body

from pydantic import BaseModel, field_validator

from sqlalchemy import and_, delete, exists, func, or_, select

from sqlalchemy.orm import Session



from app.core.database import get_db

from app.core.deps import get_current_user

from app.models.pago_con_error import PagoConError
from app.models.pago import Pago
from app.models.prestamo import Prestamo

from app.schemas.auth import UserResponse

from app.core.documento import (
    compose_numero_documento_almacenado,
    normalize_codigo_documento,
    normalize_documento,
    split_numero_documento_almacenado,
)
from app.services.pago_numero_documento import (
    numero_documento_ya_registrado,
    primer_pago_cartera_por_documento,
)


logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(get_current_user)])

_USUARIO_REGISTRO_FALLBACK = "import-masivo@sistema.rapicredit.com"


def _usuario_registro_desde_current_user(current_user: Optional[Any]) -> str:

    """Email o identificador estable para auditoría (misma idea que POST /pagos)."""

    if current_user is None:

        return _USUARIO_REGISTRO_FALLBACK

    email = getattr(current_user, "email", None)

    if isinstance(email, str) and email.strip():

        return email.strip()[:255]

    uid = getattr(current_user, "id", None)

    if uid is not None:

        return f"user_id:{uid}@{_USUARIO_REGISTRO_FALLBACK}"[:255]

    return _USUARIO_REGISTRO_FALLBACK





class PagoConErrorCreate(BaseModel):

    cedula_cliente: str

    prestamo_id: Optional[int] = None

    fecha_pago: str

    monto_pagado: float

    numero_documento: Optional[str] = None

    codigo_documento: Optional[str] = None

    institucion_bancaria: Optional[str] = None

    notas: Optional[str] = None

    conciliado: Optional[bool] = False

    errores_descripcion: Optional[list[dict]] = None

    observaciones: Optional[str] = None  # Nombres de campos con problema, separados por coma

    fila_origen: Optional[int] = None





class PagoConErrorUpdate(BaseModel):

    cedula_cliente: Optional[str] = None

    prestamo_id: Optional[int] = None

    fecha_pago: Optional[str] = None

    monto_pagado: Optional[float] = None

    numero_documento: Optional[str] = None

    codigo_documento: Optional[str] = None

    institucion_bancaria: Optional[str] = None

    notas: Optional[str] = None

    conciliado: Optional[bool] = None

    errores_descripcion: Optional[list[dict]] = None

    observaciones: Optional[str] = None





class PagoConErrorBatchBody(BaseModel):

    """Hasta 500 pagos con error en una sola peticion."""

    pagos: list[PagoConErrorCreate]



    @field_validator("pagos")

    @classmethod

    def pagos_limite(cls, v: list) -> list:

        if len(v) > 500:

            raise ValueError("Maximo 500 items por lote.")

        return v





def _pago_con_error_to_response(
    row: PagoConError,
    db: Optional[Session] = None,
) -> dict:

    fp = row.fecha_pago

    fecha_pago_str = fp.date().isoformat() if hasattr(fp, "date") and fp else (fp.isoformat() if fp else "")

    _nb, _nc = split_numero_documento_almacenado(row.numero_documento)

    out = {

        "id": row.id,

        "cedula_cliente": row.cedula_cliente or "",

        "prestamo_id": row.prestamo_id,

        "fecha_pago": fecha_pago_str,

        "monto_pagado": float(row.monto_pagado) if row.monto_pagado is not None else 0,

        "numero_documento": _nb or (row.numero_documento or ""),

        "codigo_documento": _nc or "",

        "institucion_bancaria": row.institucion_bancaria,

        "estado": row.estado or "PENDIENTE",

        "fecha_registro": row.fecha_registro.isoformat() if row.fecha_registro else None,

        "fecha_conciliacion": row.fecha_conciliacion.isoformat() if row.fecha_conciliacion else None,

        "conciliado": bool(row.conciliado),

        "verificado_concordancia": getattr(row, "verificado_concordancia", None) or None,

        "usuario_registro": row.usuario_registro or "",

        "notas": row.notas,

        "documento_nombre": getattr(row, "documento_nombre", None),

        "documento_tipo": getattr(row, "documento_tipo", None),

        "documento_ruta": getattr(row, "documento_ruta", None),

        "errores_descripcion": row.errores_descripcion,

        "observaciones": getattr(row, "observaciones", None) or "",

        "fila_origen": row.fila_origen,

    }

    if db is not None:

        dup_pid, dup_prid = primer_pago_cartera_por_documento(
            db, row.numero_documento
        )

        out["duplicado_documento_en_pagos"] = dup_pid is not None

        out["duplicado_en_cartera_pago_id"] = dup_pid

        out["duplicado_en_cartera_prestamo_id"] = dup_prid

    else:

        out["duplicado_documento_en_pagos"] = False

        out["duplicado_en_cartera_pago_id"] = None

        out["duplicado_en_cartera_prestamo_id"] = None

    return out





@router.get("", response_model=dict)

def listar_pagos_con_errores(

    page: int = Query(1, ge=1),

    per_page: int = Query(20, ge=1, le=100),

    cedula: Optional[str] = Query(None),

    estado: Optional[str] = Query(None),

    fecha_desde: Optional[str] = Query(None),

    fecha_hasta: Optional[str] = Query(None),
    fecha_pago: Optional[str] = Query(None),
    numero_documento: Optional[str] = Query(None),
    tipo_revision: Optional[str] = Query(None),

    conciliado: Optional[str] = Query(None),
    include_exportados: bool = Query(False),

    db: Session = Depends(get_db),

):

    """Listado paginado de pagos con errores (Revisar Pagos). Por defecto oculta exportados/archivados."""

    try:

        q = select(PagoConError)

        count_q = select(func.count()).select_from(PagoConError)

        if conciliado and conciliado.strip().lower() == "si":

            q = q.where(PagoConError.conciliado == True)

            count_q = count_q.where(PagoConError.conciliado == True)

        elif conciliado and conciliado.strip().lower() == "no":

            q = q.where(or_(PagoConError.conciliado == False, PagoConError.conciliado.is_(None)))

            count_q = count_q.where(or_(PagoConError.conciliado == False, PagoConError.conciliado.is_(None)))

        # Por defecto ocultar pagos ya exportados/archivados para no mezclar backlog operativo con histórico.
        if not include_exportados:
            q = q.where(or_(PagoConError.estado.is_(None), PagoConError.estado != "EXPORTADO_REVISION"))
            count_q = count_q.where(or_(PagoConError.estado.is_(None), PagoConError.estado != "EXPORTADO_REVISION"))

        if cedula and cedula.strip():

            q = q.where(PagoConError.cedula_cliente.ilike(f"%{cedula.strip()}%"))

            count_q = count_q.where(PagoConError.cedula_cliente.ilike(f"%{cedula.strip()}%"))

        if estado and estado.strip():

            q = q.where(PagoConError.estado == estado.strip().upper())

            count_q = count_q.where(PagoConError.estado == estado.strip().upper())

        if fecha_desde:

            try:

                fd = date.fromisoformat(fecha_desde)

                q = q.where(PagoConError.fecha_pago >= datetime.combine(fd, dt_time.min))

                count_q = count_q.where(PagoConError.fecha_pago >= datetime.combine(fd, dt_time.min))

            except ValueError:

                pass

        if fecha_hasta:

            try:

                fh = date.fromisoformat(fecha_hasta)

                q = q.where(PagoConError.fecha_pago <= datetime.combine(fh, dt_time.max))

                count_q = count_q.where(PagoConError.fecha_pago <= datetime.combine(fh, dt_time.max))

            except ValueError:

                pass

        if fecha_pago:
            try:
                fe = date.fromisoformat(fecha_pago)
                q = q.where(PagoConError.fecha_pago >= datetime.combine(fe, dt_time.min))
                q = q.where(PagoConError.fecha_pago <= datetime.combine(fe, dt_time.max))
                count_q = count_q.where(PagoConError.fecha_pago >= datetime.combine(fe, dt_time.min))
                count_q = count_q.where(PagoConError.fecha_pago <= datetime.combine(fe, dt_time.max))
            except ValueError:
                pass

        if numero_documento and numero_documento.strip():
            doc_raw = numero_documento.strip()
            doc_norm = normalize_documento(doc_raw)
            q_doc = or_(
                PagoConError.numero_documento.ilike(f"%{doc_raw}%"),
                func.upper(func.trim(func.coalesce(PagoConError.numero_documento, ""))).like(
                    f"%{doc_norm}%"
                ),
            )
            q = q.where(q_doc)
            count_q = count_q.where(q_doc)

        if tipo_revision and tipo_revision.strip():
            tipo = tipo_revision.strip().lower()
            hoy = date.today()
            doc_key = func.upper(func.trim(func.coalesce(PagoConError.numero_documento, "")))
            fecha_key = func.date(PagoConError.fecha_pago)
            dup_subq = (
                select(
                    fecha_key.label("fecha_pago"),
                    doc_key.label("doc_key"),
                )
                .where(doc_key != "")
                .group_by(fecha_key, doc_key)
                .having(func.count(PagoConError.id) > 1)
                .subquery()
            )

            if tipo in {"duplicado", "duplicados", "duplicado_fecha_numero"}:
                dup_cond = and_(
                    func.date(PagoConError.fecha_pago) == dup_subq.c.fecha_pago,
                    doc_key == dup_subq.c.doc_key,
                )
                q = q.join(dup_subq, dup_cond)
                count_q = count_q.join(dup_subq, dup_cond)
            elif tipo in {"irreal", "irreales"}:
                total_pagos_prestamo = (
                    select(func.coalesce(func.sum(Pago.monto_pagado), 0))
                    .where(Pago.prestamo_id == PagoConError.prestamo_id)
                    .scalar_subquery()
                )
                sobrepagado_cond = and_(
                    PagoConError.prestamo_id.is_not(None),
                    exists(
                        select(1).where(
                            Prestamo.id == PagoConError.prestamo_id,
                            or_(
                                total_pagos_prestamo > func.coalesce(Prestamo.total_financiamiento, 0),
                                (total_pagos_prestamo + func.coalesce(PagoConError.monto_pagado, 0))
                                > func.coalesce(Prestamo.total_financiamiento, 0),
                            ),
                        )
                    ),
                )
                irreal_cond = or_(
                    PagoConError.monto_pagado <= 0,
                    func.date(PagoConError.fecha_pago) > hoy,
                    sobrepagado_cond,
                )
                q = q.where(irreal_cond)
                count_q = count_q.where(irreal_cond)
            elif tipo in {"anomalo", "anomalos", "anómalo", "anómalos"}:
                anomalo_cond = or_(
                    func.coalesce(func.trim(PagoConError.observaciones), "") != "",
                    PagoConError.errores_descripcion.is_not(None),
                )
                q = q.where(anomalo_cond)
                count_q = count_q.where(anomalo_cond)

        total = db.scalar(count_q) or 0

        q = q.order_by(PagoConError.fecha_registro.desc().nullslast(), PagoConError.id.desc())

        q = q.offset((page - 1) * per_page).limit(per_page)

        rows = db.execute(q).scalars().all()

        items = [_pago_con_error_to_response(r, db) for r in rows]

        total_pages = (total + per_page - 1) // per_page if total else 0

        return {

            "pagos": items,

            "total": total,

            "page": page,

            "per_page": per_page,

            "total_pages": total_pages,

        }

    except Exception as e:

        logger.exception("Error en GET /pagos/con-errores: %s", e)

        db.rollback()

        raise HTTPException(status_code=500, detail=str(e)) from e





@router.post("", response_model=dict, status_code=201)

def crear_pago_con_error(

    payload: PagoConErrorCreate,

    db: Session = Depends(get_db),

    current_user: UserResponse = Depends(get_current_user),

):

    """Crea un pago con errores desde Carga Masiva (Revisar Pagos)."""

    try:

        fecha_ts = datetime.strptime(payload.fecha_pago, "%Y-%m-%d").replace(hour=0, minute=0, second=0, microsecond=0)

    except ValueError:

        raise HTTPException(status_code=400, detail="fecha_pago debe ser YYYY-MM-DD")

    num_norm = compose_numero_documento_almacenado(

        payload.numero_documento,

        getattr(payload, "codigo_documento", None),

    )

    if num_norm and numero_documento_ya_registrado(db, num_norm):

        raise HTTPException(

            status_code=409,

            detail="Ya existe un pago o registro en revisión con la misma combinación comprobante + código.",

        )

    ref = (num_norm or (payload.numero_documento or "").strip() or "N/A")[:100]

    usuario_registro = _usuario_registro_desde_current_user(current_user)

    row = PagoConError(

        cedula_cliente=payload.cedula_cliente.strip(),

        prestamo_id=payload.prestamo_id,

        fecha_pago=fecha_ts,

        monto_pagado=payload.monto_pagado,

        numero_documento=num_norm,

        institucion_bancaria=payload.institucion_bancaria.strip() if payload.institucion_bancaria else None,

        estado="PENDIENTE",

        conciliado=payload.conciliado if payload.conciliado is not None else False,

        usuario_registro=usuario_registro,

        notas=payload.notas,

        referencia_pago=ref,

        errores_descripcion=payload.errores_descripcion,

        observaciones=(payload.observaciones or "").strip() or None,

        fila_origen=payload.fila_origen,

    )

    db.add(row)

    db.commit()

    db.refresh(row)

    return _pago_con_error_to_response(row, db)





@router.post("/batch", response_model=dict, status_code=201)

def crear_pagos_con_error_batch(

    body: PagoConErrorBatchBody,

    db: Session = Depends(get_db),

    current_user: UserResponse = Depends(get_current_user),

):

    """Crea varios pagos con errores en una sola transaccion (Guardar todos desde Carga Masiva)."""

    results: list[dict] = []

    try:

        usuario_registro = _usuario_registro_desde_current_user(current_user)

        for payload in body.pagos:

            try:

                fecha_ts = datetime.strptime(payload.fecha_pago, "%Y-%m-%d").replace(

                    hour=0, minute=0, second=0, microsecond=0

                )

            except ValueError:

                results.append({"success": False, "error": "fecha_pago debe ser YYYY-MM-DD", "payload_index": len(results)})

                continue

            num_norm = compose_numero_documento_almacenado(

                payload.numero_documento,

                getattr(payload, "codigo_documento", None),

            )

            if num_norm and numero_documento_ya_registrado(db, num_norm):

                results.append(

                    {

                        "success": False,

                        "error": "Ya existe un pago o registro con la misma combinación comprobante + código.",

                        "payload_index": len(results),

                    }

                )

                continue

            ref = (num_norm or (payload.numero_documento or "").strip() or "N/A")[:100]

            row = PagoConError(

                cedula_cliente=(payload.cedula_cliente or "").strip(),

                prestamo_id=payload.prestamo_id,

                fecha_pago=fecha_ts,

                monto_pagado=payload.monto_pagado,

                numero_documento=num_norm,

                institucion_bancaria=(payload.institucion_bancaria or "").strip() or None if payload.institucion_bancaria else None,

                estado="PENDIENTE",

                conciliado=payload.conciliado if payload.conciliado is not None else False,

                usuario_registro=usuario_registro,

                notas=payload.notas,

                referencia_pago=ref,

                errores_descripcion=payload.errores_descripcion,

                observaciones=(payload.observaciones or "").strip() or None if payload.observaciones else None,

                fila_origen=payload.fila_origen,

            )

            db.add(row)

            db.flush()

            db.refresh(row)

            results.append({"success": True, "pago": _pago_con_error_to_response(row, db)})

        db.commit()

        ok = sum(1 for r in results if r.get("success"))

        return {"results": results, "ok_count": ok, "fail_count": len(results) - ok}

    except Exception as e:

        db.rollback()

        logger.exception("Error en POST /pagos/con-errores/batch: %s", e)

        raise HTTPException(status_code=500, detail=str(e)) from e





class EliminarPorDescargaBody(BaseModel):

    ids: list[int]





@router.post("/eliminar-por-descarga", response_model=dict)

def eliminar_por_descarga(payload: EliminarPorDescargaBody = Body(...), db: Session = Depends(get_db)):

    """Elimina de pagos_con_errores los registros descargados (borrado en lote). La lista se vacia y se rellena al enviar desde Carga Masiva."""

    valid_ids = [p for p in payload.ids if isinstance(p, int) and p > 0]

    if not valid_ids:

        return {"eliminados": 0, "mensaje": "No hay IDs"}

    result = db.execute(delete(PagoConError).where(PagoConError.id.in_(valid_ids)))

    eliminados = result.rowcount

    db.commit()

    return {"eliminados": eliminados, "mensaje": f"{eliminados} eliminados de pagos_con_errores"}


@router.post("/archivar-por-descarga", response_model=dict)
def archivar_por_descarga(
    payload: EliminarPorDescargaBody = Body(...),
    db: Session = Depends(get_db),
    current_user: UserResponse = Depends(get_current_user),
):
    """Marca como EXPORTADO_REVISION en vez de borrar, para trazabilidad y auditoría."""
    valid_ids = [p for p in payload.ids if isinstance(p, int) and p > 0]
    if not valid_ids:
        return {"archivados": 0, "mensaje": "No hay IDs"}

    usuario = _usuario_registro_desde_current_user(current_user)
    marca = datetime.now(ZoneInfo("America/Caracas")).isoformat(timespec="seconds")
    rows = db.execute(select(PagoConError).where(PagoConError.id.in_(valid_ids))).scalars().all()
    archivados = 0
    for row in rows:
        row.estado = "EXPORTADO_REVISION"
        nota = f"Exportado a revisión ({marca}) por {usuario}"
        row.observaciones = f'{(row.observaciones or "").strip()} | {nota}'.strip(" |")
        archivados += 1
    db.commit()
    return {"archivados": archivados, "mensaje": f"{archivados} pago(s) archivado(s) para revisión"}





@router.get("/export", response_model=list)

def exportar_pagos_con_errores(

    cedula: Optional[str] = Query(None),

    fecha_desde: Optional[str] = Query(None),

    fecha_hasta: Optional[str] = Query(None),

    db: Session = Depends(get_db),

):

    """Exporta todos los pagos con errores para Excel (100% de datos). El archivado se realiza aparte."""

    q = select(PagoConError).order_by(

        PagoConError.fecha_registro.desc().nullslast(), PagoConError.id.desc()

    )

    if cedula and cedula.strip():

        q = q.where(PagoConError.cedula_cliente.ilike(f"%{cedula.strip()}%"))

    if fecha_desde:

        try:

            fd = date.fromisoformat(fecha_desde)

            q = q.where(PagoConError.fecha_pago >= datetime.combine(fd, dt_time.min))

        except ValueError:

            pass

    if fecha_hasta:

        try:

            fh = date.fromisoformat(fecha_hasta)

            q = q.where(PagoConError.fecha_pago <= datetime.combine(fh, dt_time.max))

        except ValueError:

            pass

    rows = db.execute(q).scalars().all()

    return [_pago_con_error_to_response(r, db) for r in rows]





@router.post("/mover-a-pagos", response_model=dict)

def mover_a_pagos_normales(

    payload: EliminarPorDescargaBody = Body(...),

    db: Session = Depends(get_db),

):

    """Mueve pagos corregidos de pagos_con_errores a pagos (y los elimina de con_errores). Aplica cada pago a cuotas (cascada) para que préstamos y estado de cuenta se actualicen."""

    ids = payload.ids

    if not ids:

        logger.info("mover_a_pagos_normales: lista vacía de IDs")
        return {"movidos": 0, "mensaje": "No hay IDs"}

    logger.info(f"mover_a_pagos_normales: iniciando con {len(ids)} pago(s): {ids}")

    from app.models.pago import Pago

    from app.api.v1.endpoints.pagos import _aplicar_pago_a_cuotas_interno



    movidos = 0

    cuotas_aplicadas = 0
    
    errores_procesamiento = []

    for idx, pid in enumerate(ids, start=1):

        if not isinstance(pid, int) or pid <= 0:

            logger.warning(f"mover_a_pagos_normales: ID inválido (tipo/valor): {pid}")
            continue

        row = db.get(PagoConError, pid)

        if not row:

            logger.warning(f"mover_a_pagos_normales: PagoConError {pid} no encontrado")
            continue

        logger.debug(f"mover_a_pagos_normales: procesando pago {idx}/{len(ids)} (id={pid}, cedula={row.cedula_cliente}, monto={row.monto_pagado})")

        # Validar que no exista duplicado en tabla pagos
        numero_documento_normalizado = row.numero_documento or ""
        duplicado_existe = False

        if numero_documento_normalizado:
            from app.services.pago_numero_documento import numero_documento_ya_registrado
            duplicado_existe = numero_documento_ya_registrado(
                db,
                numero_documento_normalizado,
                exclude_pago_con_error_id=pid,
            )
            if duplicado_existe:
                logger.warning(f"mover_a_pagos_normales: pago {pid} tiene documento duplicado en tabla pagos: {numero_documento_normalizado}")
                errores_procesamiento.append(f"Pago {pid}: documento '{numero_documento_normalizado}' ya existe en tabla pagos")
                continue  # Saltar este pago, no mover

        # «Guardar y procesar» = intención explícita de pasar a cartera. Si hay préstamo y monto,
        # forzamos validación cartera (conciliado + verificado SI) para que la columna Cartera y la
        # cascada queden alineadas con el estado final. Sin préstamo respetamos la fila origen.
        debe_validar_cartera = bool(row.prestamo_id) and float(row.monto_pagado or 0) > 0
        if debe_validar_cartera:
            conciliado = True
        else:
            conciliado = bool(row.conciliado) if row.conciliado is not None else False

        ahora = datetime.now(ZoneInfo("America/Caracas")) if conciliado else None

        pago = Pago(

            cedula_cliente=row.cedula_cliente,

            prestamo_id=row.prestamo_id,

            fecha_pago=row.fecha_pago,

            monto_pagado=row.monto_pagado,

            numero_documento=row.numero_documento or "",

            institucion_bancaria=row.institucion_bancaria,

            estado=row.estado or "PENDIENTE",

            conciliado=conciliado,

            fecha_conciliacion=ahora,

            verificado_concordancia="SI" if conciliado else "",

            notas=row.notas,

            referencia_pago=row.referencia_pago or row.numero_documento or "N/A",

        )

        db.add(pago)

        db.flush()

        db.refresh(pago)
        
        nuevo_pago_id = pago.id
        cc_aplicadas = 0
        cp_aplicadas = 0

        if pago.prestamo_id and float(pago.monto_pagado or 0) > 0:

            try:

                cc, cp = _aplicar_pago_a_cuotas_interno(pago, db)
                cc_aplicadas = cc
                cp_aplicadas = cp

                if cc > 0 or cp > 0:

                    pago.estado = "PAGADO"

                    cuotas_aplicadas += cc + cp
                    
                    logger.info(f"mover_a_pagos_normales: pago id={nuevo_pago_id} aplicado a {cc} cuota(s) completa(s), {cp} parcial(es)")

                else:
                    
                    logger.warning(f"mover_a_pagos_normales: pago id={nuevo_pago_id} no se aplicó a ninguna cuota (prestamo={pago.prestamo_id})")

            except Exception as e:

                logger.error(f"mover_a_pagos_normales: error aplicando pago id={nuevo_pago_id} a cuotas: {str(e)}", exc_info=True)
                errores_procesamiento.append(f"Pago {pid}: {str(e)}")

        db.delete(row)
        
        logger.debug(f"mover_a_pagos_normales: pago id={pid} eliminado de pagos_con_errores, creado pago id={nuevo_pago_id}")

        movidos += 1

    db.commit()
    
    logger.info(f"mover_a_pagos_normales: COMPLETADO - {movidos} pago(s) movido(s), {cuotas_aplicadas} cuota(s) aplicada(s)")
    
    respuesta = {
        "movidos": movidos,
        "cuotas_aplicadas": cuotas_aplicadas,
        "mensaje": f"{movidos} pagos movidos a tabla pagos; cuotas aplicadas: {cuotas_aplicadas}"
    }
    
    if errores_procesamiento:
        logger.warning(f"mover_a_pagos_normales: errores durante procesamiento: {errores_procesamiento}")
        respuesta["errores"] = errores_procesamiento
        respuesta["mensaje"] += f" ({len(errores_procesamiento)} error(es))"

    return respuesta





@router.get("/{pago_id}", response_model=dict)

def obtener_pago_con_error(pago_id: int, db: Session = Depends(get_db)):

    row = db.get(PagoConError, pago_id)

    if not row:

        raise HTTPException(status_code=404, detail="Pago con error no encontrado")

    return _pago_con_error_to_response(row, db)





@router.put("/{pago_id}", response_model=dict)

def actualizar_pago_con_error(pago_id: int, payload: PagoConErrorUpdate, db: Session = Depends(get_db)):

    row = db.get(PagoConError, pago_id)

    if not row:

        raise HTTPException(status_code=404, detail="Pago con error no encontrado")

    data = payload.model_dump(exclude_unset=True)

    _doc_touch = "numero_documento" in data or "codigo_documento" in data

    if _doc_touch:

        b0, c0 = split_numero_documento_almacenado(row.numero_documento or "")

        if "numero_documento" in data:

            nb = normalize_documento(data["numero_documento"])

        else:

            nb = normalize_documento(b0)

        if not nb:

            raise HTTPException(status_code=400, detail="numero_documento no puede estar vacío.")

        if "codigo_documento" in data:

            nc = normalize_codigo_documento(data.get("codigo_documento"))

        else:

            nc = normalize_codigo_documento(c0) if c0 else None

        new_stored = compose_numero_documento_almacenado(nb, nc)

        if new_stored and numero_documento_ya_registrado(

            db,

            new_stored,

            exclude_pago_con_error_id=pago_id,

        ):

            raise HTTPException(

                status_code=409,

                detail="Ya existe un pago o registro en revisión con la misma combinación comprobante + código.",

            )

        row.numero_documento = new_stored

        row.referencia_pago = (new_stored or nb or "N/A")[:100]

        data.pop("numero_documento", None)

        data.pop("codigo_documento", None)

    if "cedula_cliente" in data:

        row.cedula_cliente = (data["cedula_cliente"] or "").strip()

    if "prestamo_id" in data:

        row.prestamo_id = data["prestamo_id"]

    if "fecha_pago" in data and data["fecha_pago"] is not None:

        try:

            row.fecha_pago = datetime.strptime(data["fecha_pago"], "%Y-%m-%d").replace(

                hour=0, minute=0, second=0, microsecond=0

            )

        except ValueError:

            raise HTTPException(status_code=400, detail="fecha_pago debe ser YYYY-MM-DD")

    if "monto_pagado" in data:

        row.monto_pagado = data["monto_pagado"]

    if "institucion_bancaria" in data:

        row.institucion_bancaria = (

            data["institucion_bancaria"].strip() if data["institucion_bancaria"] else None

        )

    if "notas" in data:

        row.notas = data["notas"]

    if "conciliado" in data:

        row.conciliado = data["conciliado"]

    if "errores_descripcion" in data:

        row.errores_descripcion = data["errores_descripcion"]

    if "observaciones" in data:

        row.observaciones = (data["observaciones"] or "").strip() or None

    db.commit()

    db.refresh(row)

    return _pago_con_error_to_response(row, db)





@router.delete("/{pago_id}", status_code=204)

def eliminar_pago_con_error(pago_id: int, db: Session = Depends(get_db)):

    row = db.get(PagoConError, pago_id)

    if not row:

        logger.warning(f"eliminar_pago_con_error: PagoConError {pago_id} no encontrado (404)")
        raise HTTPException(status_code=404, detail="Pago con error no encontrado")

    logger.info(f"eliminar_pago_con_error: eliminando pago {pago_id} (cedula={row.cedula_cliente}, monto={row.monto_pagado})")

    db.delete(row)

    db.commit()
    
    logger.info(f"eliminar_pago_con_error: pago {pago_id} eliminado exitosamente de pagos_con_errores")

    return None







