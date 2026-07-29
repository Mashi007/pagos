"""
API modulo Cobranzas: busqueda por cedula, casos, imagenes y bitacora de acuerdos.
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import Response
from sqlalchemy.exc import ProgrammingError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.cobranza import CobranzaCaso, CobranzaImagen
from app.schemas.auth import UserResponse
from app.schemas.cobranza import (
    CobranzaAcuerdoCreate,
    CobranzaAcuerdoOut,
    CobranzaAcuerdoUpdate,
    CobranzaBuscarResponse,
    CobranzaCasoCreate,
    CobranzaCasoOut,
    CobranzaCasoUpdate,
    CobranzaSesionNotaOut,
    UniversoAnalisisResponse,
    UniversoCedulaIn,
    UniversoCedulasLista,
    UniversoMeta,
)
from app.services.cobranzas import cobranzas_service as svc
from app.services.cobranzas import universo_analisis_service as universo_svc
from app.services.cobranzas.imagen_service import (
    leer_imagen_cobranza,
    persistir_imagen_cobranza,
)
from app.services.cobranzas.nota_adjunto_service import (
    leer_adjunto_nota,
    leer_uploads_nota,
)
from app.services.cobranzas.reportes_cache import ejecutar_actualizacion_reportes

router = APIRouter(dependencies=[Depends(get_current_user)])


def _http_desde_error_cobranzas(exc: Exception) -> HTTPException:
    msg = str(exc).lower()
    if isinstance(exc, ProgrammingError) or "does not exist" in msg or "undefinedcolumn" in msg:
        return HTTPException(
            status_code=503,
            detail=(
                "Esquema de cobranzas incompleto en la base de datos. "
                "Ejecute migracion_cobranza_acuerdos_mensaje_moneda.sql y reinicie el servicio."
            ),
        )
    return HTTPException(status_code=500, detail="Error al procesar cobranzas.")


@router.get("/buscar", response_model=CobranzaBuscarResponse)
def buscar_por_cedula(
    cedula: str = Query(..., min_length=3),
    db: Session = Depends(get_db),
):
    if not universo_svc.cedula_en_universo(db, cedula):
        raise HTTPException(
            status_code=400,
            detail=(
                "Cedula fuera del universo cargado. "
                "Suba el Excel o use una cedula de la lista."
            ),
        )
    return svc.buscar_por_cedula(db, cedula)


@router.get("/casos/{caso_id}", response_model=CobranzaCasoOut)
def obtener_caso(
    caso_id: int,
    db: Session = Depends(get_db),
):
    return svc.obtener_caso_detalle(db, caso_id, sincronizar_acuerdos=True)


@router.post("/casos", response_model=CobranzaCasoOut, status_code=201)
def crear_caso(
    body: CobranzaCasoCreate,
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    return svc.crear_caso(db, body, user_id=user.id)


@router.patch("/casos/{caso_id}", response_model=CobranzaCasoOut)
def actualizar_caso(
    caso_id: int,
    body: CobranzaCasoUpdate,
    db: Session = Depends(get_db),
):
    return svc.actualizar_caso(db, caso_id, body)


@router.post("/notas/sesion", response_model=CobranzaSesionNotaOut, status_code=201)
def abrir_sesion_nota(
    prestamo_id: int = Form(...),
    motivo: str = Form("OTRO"),
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    """Nueva nota en BD al abrir la negociacion (fecha = hoy)."""
    try:
        return svc.abrir_sesion_nota(
            db,
            prestamo_id=prestamo_id,
            motivo=motivo,
            user_id=user.id,
        )
    except HTTPException:
        raise
    except (ProgrammingError, SQLAlchemyError) as e:
        db.rollback()
        raise _http_desde_error_cobranzas(e) from e


@router.patch("/notas/{acuerdo_id}", response_model=CobranzaCasoOut)
async def guardar_nota_sesion(
    acuerdo_id: int,
    mensaje: str = Form(...),
    cantidad: Optional[float] = Form(None),
    moneda: str = Form("USD"),
    archivos: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    """Guarda mensaje, monto y respaldos (tabla cobranza_nota_adjuntos)."""
    try:
        uploads = await leer_uploads_nota(archivos or [])
        return svc.guardar_nota_sesion(
            db,
            acuerdo_id,
            mensaje=mensaje,
            cantidad=cantidad,
            moneda=moneda,
            archivos=uploads,
            user_id=user.id,
        )
    except HTTPException:
        raise
    except (ProgrammingError, SQLAlchemyError) as e:
        db.rollback()
        raise _http_desde_error_cobranzas(e) from e


@router.post("/notas", response_model=CobranzaCasoOut, status_code=201)
async def crear_nota(
    prestamo_id: int = Form(...),
    mensaje: str = Form(...),
    cantidad: Optional[float] = Form(None),
    moneda: str = Form("USD"),
    motivo: str = Form("OTRO"),
    archivos: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    uploads = await leer_uploads_nota(archivos or [])
    return svc.crear_nota(
        db,
        prestamo_id=prestamo_id,
        mensaje=mensaje,
        cantidad=cantidad,
        moneda=moneda,
        motivo=motivo,
        archivos=uploads,
        user_id=user.id,
    )


@router.get("/notas-adjuntos/{adjunto_id}")
def descargar_adjunto_nota(
    adjunto_id: str,
    db: Session = Depends(get_db),
):
    body, ct, nombre = leer_adjunto_nota(db, adjunto_id)
    if not body:
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")
    headers = {}
    if nombre:
        headers["Content-Disposition"] = f'inline; filename="{nombre}"'
    return Response(content=body, media_type=ct or "application/octet-stream", headers=headers)


@router.post(
    "/casos/{caso_id}/acuerdos",
    response_model=CobranzaAcuerdoOut,
    status_code=201,
)
def crear_acuerdo(
    caso_id: int,
    body: CobranzaAcuerdoCreate,
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    return svc.crear_acuerdo(db, caso_id, body, user_id=user.id)


@router.patch(
    "/casos/{caso_id}/acuerdos/{acuerdo_id}",
    response_model=CobranzaAcuerdoOut,
)
def actualizar_acuerdo(
    caso_id: int,
    acuerdo_id: int,
    body: CobranzaAcuerdoUpdate,
    db: Session = Depends(get_db),
):
    return svc.actualizar_acuerdo(db, caso_id, acuerdo_id, body)


@router.post("/casos/{caso_id}/acuerdos/sincronizar-estados", response_model=CobranzaCasoOut)
def sincronizar_acuerdos(
    caso_id: int,
    db: Session = Depends(get_db),
):
    caso = svc._caso_o_404(db, caso_id)
    svc.sincronizar_estados_acuerdos(db, caso)
    return svc.obtener_caso_detalle(db, caso_id, sincronizar_acuerdos=False)


@router.post("/casos/{caso_id}/imagenes")
async def subir_imagen(
    caso_id: int,
    file: UploadFile = File(...),
    descripcion: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    caso = svc._caso_o_404(db, caso_id)
    content = await file.read()
    img_id, url = persistir_imagen_cobranza(
        db,
        caso,
        content,
        file.content_type,
        descripcion=descripcion,
        user_id=user.id,
    )
    db.commit()
    return {"id": img_id, "url": url}


@router.get("/imagenes/{imagen_id}")
def descargar_imagen(
    imagen_id: str,
    db: Session = Depends(get_db),
):
    body, ct = leer_imagen_cobranza(db, imagen_id)
    if not body:
        raise HTTPException(status_code=404, detail="Imagen no encontrada.")
    return Response(content=body, media_type=ct or "application/octet-stream")


@router.delete("/casos/{caso_id}/imagenes/{imagen_id}", status_code=204)
def eliminar_imagen(
    caso_id: int,
    imagen_id: str,
    db: Session = Depends(get_db),
):
    svc._caso_o_404(db, caso_id)
    row = (
        db.query(CobranzaImagen)
        .filter(
            CobranzaImagen.id == imagen_id,
            CobranzaImagen.caso_id == caso_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Imagen no encontrada.")
    db.delete(row)
    db.commit()
    return Response(status_code=204)


@router.post("/universo/upload")
async def upload_universo(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    return await universo_svc.upload_universo_excel(db, file, usuario_id=user.id)


@router.get("/universo", response_model=UniversoMeta)
def get_universo_meta(db: Session = Depends(get_db)):
    return universo_svc.meta_universo(db)


@router.get("/universo/cedulas", response_model=UniversoCedulasLista)
def get_universo_cedulas(db: Session = Depends(get_db)):
    cedulas = universo_svc.listar_cedulas_universo(db)
    return {"cedulas": cedulas, "cantidad": len(cedulas)}


@router.post("/universo/cedulas")
def post_universo_cedula(
    body: UniversoCedulaIn,
    db: Session = Depends(get_db),
    user: UserResponse = Depends(get_current_user),
):
    return universo_svc.agregar_cedula_universo(
        db, body.cedula, usuario_id=user.id
    )


@router.delete("/universo/cedulas")
def delete_universo_cedula(
    cedula: str = Query(...),
    db: Session = Depends(get_db),
):
    return universo_svc.eliminar_cedula_universo(db, cedula)


@router.delete("/universo")
def delete_universo(db: Session = Depends(get_db)):
    return universo_svc.limpiar_universo(db)


@router.get("/universo/analisis", response_model=UniversoAnalisisResponse)
def get_universo_analisis(db: Session = Depends(get_db)):
    return universo_svc.analizar_universo(db)



__all__ = ["router", "ejecutar_actualizacion_reportes"]
