"""
Endpoint para conciliación masiva de pagos desde Excel
"""

import logging
from datetime import datetime
from typing import List

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.pago import Pago
from app.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)


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
        # Validar extensión
        if not file.filename.endswith((".xlsx", ".xls")):
            raise HTTPException(
                status_code=400, detail="El archivo debe ser Excel (.xlsx o .xls)"
            )

        # Leer archivo Excel
        contents = await file.read()
        df = pd.read_excel(contents)

        # Validar columnas requeridas (2 columnas exactas)
        required_columns = [
            "Fecha de Depósito",
            "Número de Documento",
        ]
        
        # Verificar que todas las columnas requeridas existan
        if not all(col in df.columns for col in required_columns):
            raise HTTPException(
                status_code=400,
                detail=f"El archivo debe contener exactamente 2 columnas: {', '.join(required_columns)}",
            )

        logger.info(f"📊 [conciliacion] Procesando {len(df)} registros de conciliación")

        # Procesar cada fila del Excel
        pagos_conciliados = 0
        pagos_no_encontrados = []
        errores = []
        documentos_procesados = set()  # Para evitar duplicados en el mismo archivo

        for index, row in df.iterrows():
            try:
                numero_documento = str(row["Número de Documento"]).strip()
                
                # Validar que el número de documento no esté vacío
                if not numero_documento or numero_documento.lower() in ['nan', 'none', '']:
                    errores.append(f"Fila {index + 2}: Número de documento vacío")
                    continue

                # Evitar procesar el mismo documento dos veces en el mismo archivo
                if numero_documento in documentos_procesados:
                    continue
                documentos_procesados.add(numero_documento)

                # Buscar pago por número de documento (coincidencia exacta)
                pago = (
                    db.query(Pago)
                    .filter(Pago.numero_documento == numero_documento)
                    .first()
                )

                if pago:
                    # Verificar que el pago no esté ya conciliado
                    if not pago.conciliado:
                        # Marcar como conciliado
                        pago.conciliado = True
                        pago.fecha_conciliacion = datetime.now()
                        
                        # Marcar como verificado en concordancia (SI) cuando coincide el número de documento
                        if hasattr(pago, 'verificado_concordancia'):
                            pago.verificado_concordancia = 'SI'
                        
                        db.commit()
                        db.refresh(pago)
                        
                        pagos_conciliados += 1
                        logger.info(f"✅ [conciliacion] Pago ID {pago.id} conciliado (documento: {numero_documento})")
                    else:
                        logger.info(f"ℹ️ [conciliacion] Pago ID {pago.id} ya estaba conciliado (documento: {numero_documento})")
                else:
                    # Documento no encontrado en el sistema
                    pagos_no_encontrados.append(numero_documento)
                    logger.warning(f"⚠️ [conciliacion] Documento no encontrado: {numero_documento}")

            except Exception as e:
                logger.error(f"❌ [conciliacion] Error procesando fila {index + 2}: {e}", exc_info=True)
                errores.append(f"Fila {index + 2}: {str(e)}")

        logger.info(
            f"📊 [conciliacion] Resultados: {pagos_conciliados} conciliados, "
            f"{len(pagos_no_encontrados)} no encontrados, {len(errores)} errores"
        )

        return {
            "pagos_conciliados": pagos_conciliados,
            "pagos_no_encontrados": len(pagos_no_encontrados),
            "documentos_no_encontrados": pagos_no_encontrados[:20],  # Mostrar solo primeros 20
            "errores": len(errores),
            "errores_detalle": errores[:10],  # Mostrar solo primeros 10 errores
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ [conciliacion] Error procesando archivo: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error procesando archivo de conciliación: {str(e)}"
        )

