"""
Endpoint para conciliación masiva de pagos desde Excel
"""

import logging
from datetime import datetime
from typing import List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.pago import Pago
from app.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)


def _validar_archivo_conciliacion(filename: Optional[str]) -> None:
    """Valida que el archivo sea Excel"""
    if not filename or not filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="El archivo debe ser Excel (.xlsx o .xls)")


def _validar_columnas_conciliacion(df, required_columns: list[str]) -> None:
    """Valida que el DataFrame contenga todas las columnas requeridas"""
    if not all(col in df.columns for col in required_columns):
        raise HTTPException(
            status_code=400,
            detail=f"El archivo debe contener exactamente 2 columnas: {', '.join(required_columns)}",
        )


def _validar_numero_documento(numero_documento: str) -> bool:
    """Valida que el número de documento no esté vacío"""
    if not numero_documento or numero_documento.lower() in ["nan", "none", ""]:
        return False
    return True


def _conciliar_pago(pago: Pago, db: Session, numero_documento: str) -> bool:
    """Concilia un pago si no está ya conciliado. Returns: True si se concilió, False si ya estaba conciliado"""
    if pago.conciliado:
        logger.info(f"ℹ️ [conciliacion] Pago ID {pago.id} ya estaba conciliado (documento: {numero_documento})")
        return False

    pago.conciliado = True
    pago.fecha_conciliacion = datetime.now()

    if hasattr(pago, "verificado_concordancia"):
        pago.verificado_concordancia = "SI"

    db.commit()
    db.refresh(pago)
    logger.info(f"✅ [conciliacion] Pago ID {pago.id} conciliado (documento: {numero_documento})")
    return True


def _procesar_fila_conciliacion(
    row, index: int, db: Session, documentos_procesados: set
) -> tuple[int, list[str], list[str]]:
    """
    Procesa una fila del Excel de conciliación.
    Returns: (pagos_conciliados, pagos_no_encontrados, errores)
    """
    try:
        numero_documento = str(row["Número de Documento"]).strip()

        if not _validar_numero_documento(numero_documento):
            return (0, [], [f"Fila {index + 2}: Número de documento vacío"])

        if numero_documento in documentos_procesados:
            return (0, [], [])
        documentos_procesados.add(numero_documento)

        pago = db.query(Pago).filter(Pago.numero_documento == numero_documento).first()

        if pago:
            conciliado = _conciliar_pago(pago, db, numero_documento)
            return (1 if conciliado else 0, [], [])
        else:
            logger.warning(f"⚠️ [conciliacion] Documento no encontrado: {numero_documento}")
            return (0, [numero_documento], [])

    except Exception as e:
        logger.error(f"❌ [conciliacion] Error procesando fila {index + 2}: {e}", exc_info=True)
        return (0, [], [f"Fila {index + 2}: {str(e)}"])


@router.post("/conciliacion/upload")
async def upload_conciliacion_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Procesar conciliación masiva desde archivo Excel

    Formato esperado (2 columnas):
    - Fecha de Depósito
    - Número de Documento

    El sistema compara el número de documento del Excel con los pagos existentes.
    Si encuentra una coincidencia exacta, marca el pago como conciliado.
    """
    try:
        _validar_archivo_conciliacion(file.filename)

        contents = await file.read()
        df = pd.read_excel(contents)

        required_columns = ["Fecha de Depósito", "Número de Documento"]
        _validar_columnas_conciliacion(df, required_columns)

        logger.info(f"📊 [conciliacion] Procesando {len(df)} registros de conciliación")

        pagos_conciliados = 0
        pagos_no_encontrados = []
        errores = []
        documentos_procesados = set()

        for index, row in df.iterrows():
            conciliados, no_encontrados, fila_errores = _procesar_fila_conciliacion(row, index, db, documentos_procesados)
            pagos_conciliados += conciliados
            pagos_no_encontrados.extend(no_encontrados)
            errores.extend(fila_errores)

        logger.info(
            f"📊 [conciliacion] Resultados: {pagos_conciliados} conciliados, "
            f"{len(pagos_no_encontrados)} no encontrados, {len(errores)} errores"
        )

        return {
            "pagos_conciliados": pagos_conciliados,
            "pagos_no_encontrados": len(pagos_no_encontrados),
            "documentos_no_encontrados": pagos_no_encontrados[:20],
            "errores": len(errores),
            "errores_detalle": errores[:10],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [conciliacion] Error procesando archivo: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando archivo de conciliación: {str(e)}",
        )
