"""
Endpoint para carga masiva de pagos desde Excel
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from openpyxl import load_workbook
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.cliente import Cliente
from app.models.pago import Pago
from app.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)


def _validar_archivo_excel_pagos(filename: Optional[str]):
    """Valida que el archivo sea Excel"""
    if not filename or not filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="El archivo debe ser Excel (.xlsx o .xls)")


def _validar_columnas_pagos(df: pd.DataFrame):
    """Valida que el DataFrame contenga las columnas requeridas"""
    required_columns = [
        "Cédula de Identidad",
        "Fecha de Pago",
        "Monto Pagado",
        "Número de Documento",
    ]
    if not all(col in df.columns for col in required_columns):
        raise HTTPException(
            status_code=400,
            detail=f"El archivo debe contener las columnas: {', '.join(required_columns)}",
        )


def _procesar_fila_pago(
    row: pd.Series, index: int, db: Session, current_user: User
) -> tuple[Optional[dict], Optional[str]]:
    """Procesa una fila del Excel y retorna (resultado, error)"""
    try:
        cedula = str(row["Cédula de Identidad"]).strip()
        fecha_pago_str = str(row["Fecha de Pago"])
        monto_pagado = Decimal(str(row["Monto Pagado"]))
        numero_documento = str(row["Número de Documento"]).strip()

        # Validar cliente existe
        cliente = db.query(Cliente).filter(Cliente.cedula == cedula).first()
        if not cliente:
            return None, f"Fila {index + 2}: Cliente con cédula {cedula} no encontrado"

        # Parsear fecha
        try:
            fecha_pago = pd.to_datetime(fecha_pago_str).to_pydatetime()
        except Exception:
            return None, f"Fila {index + 2}: Fecha inválida"

        # Crear pago
        pago = Pago(
            cedula_cliente=cedula,
            prestamo_id=None,  # TODO: Buscar préstamo del cliente
            fecha_pago=fecha_pago,
            fecha_registro=datetime.now(),
            monto_pagado=monto_pagado,
            numero_documento=numero_documento,
            institucion_bancaria=None,
            estado="PAGADO",
            usuario_registro=current_user.email,
            conciliado=False,
            activo=True,
        )

        db.add(pago)
        db.commit()
        db.refresh(pago)

        return {
            "fila": index + 2,
            "cedula": cedula,
            "monto": float(monto_pagado),
            "estado": "Registrado",
        }, None

    except Exception as e:
        db.rollback()
        return None, f"Fila {index + 2}: {str(e)}"


@router.post("/upload")
async def upload_pagos_excel(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Cargar pagos masivamente desde archivo Excel
    Formato esperado:
    - Cédula de Identidad
    - Fecha de Pago
    - Monto Pagado
    - Número de Documento
    """
    try:
        _validar_archivo_excel_pagos(file.filename)

        contents = await file.read()
        df = pd.read_excel(contents)
        _validar_columnas_pagos(df)

        # Procesar cada fila
        resultados = []
        errores = []

        for index, row in df.iterrows():
            resultado, error = _procesar_fila_pago(row, index, db, current_user)
            if resultado:
                resultados.append(resultado)
            if error:
                errores.append(error)

        return {
            "success": len(resultados),
            "errores": len(errores),
            "resultados": resultados,
            "errores_detalle": errores[:10],  # Mostrar solo primeros 10 errores
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en upload_pagos_excel: {e}")
        raise HTTPException(status_code=500, detail=f"Error procesando archivo: {str(e)}")
