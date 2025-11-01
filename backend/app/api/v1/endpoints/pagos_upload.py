"""
Endpoint para carga masiva de pagos desde Excel
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import List

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
        # Validar extensión
        if not file.filename.endswith((".xlsx", ".xls")):
            raise HTTPException(status_code=400, detail="El archivo debe ser Excel (.xlsx o .xls)")

        # Leer archivo Excel
        contents = await file.read()
        df = pd.read_excel(contents)

        # Validar columnas requeridas
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

        # Procesar cada fila
        resultados = []
        errores = []

        for index, row in df.iterrows():
            try:
                cedula = str(row["Cédula de Identidad"]).strip()
                fecha_pago_str = str(row["Fecha de Pago"])
                monto_pagado = Decimal(str(row["Monto Pagado"]))
                numero_documento = str(row["Número de Documento"]).strip()

                # Validar cliente existe
                cliente = db.query(Cliente).filter(Cliente.cedula == cedula).first()
                if not cliente:
                    errores.append(f"Fila {index + 2}: Cliente con cédula {cedula} no encontrado")
                    continue

                # Parsear fecha
                try:
                    fecha_pago = pd.to_datetime(fecha_pago_str).to_pydatetime()
                except Exception:
                    errores.append(f"Fila {index + 2}: Fecha inválida")
                    continue

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

                resultados.append(
                    {
                        "fila": index + 2,
                        "cedula": cedula,
                        "monto": float(monto_pagado),
                        "estado": "Registrado",
                    }
                )

            except Exception as e:
                errores.append(f"Fila {index + 2}: {str(e)}")
                db.rollback()

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
