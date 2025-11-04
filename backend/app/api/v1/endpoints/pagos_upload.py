"""
Endpoint para carga masiva de pagos desde Excel
"""

import logging
from datetime import datetime
from decimal import Decimal
from typing import Optional

import pandas as pd  # type: ignore[import-untyped]
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile  # type: ignore[import-untyped]
from openpyxl import load_workbook  # type: ignore[import-untyped]
from sqlalchemy import func  # type: ignore[import-untyped]
from sqlalchemy.orm import Session  # type: ignore[import-untyped]

from app.api.deps import get_current_user, get_db
from app.models.cliente import Cliente
from app.models.pago import Pago
from app.models.pago_staging import PagoStaging  # Para insertar en staging
from app.models.user import User

router = APIRouter()
logger = logging.getLogger(__name__)


def _validar_archivo_excel_pagos(filename: Optional[str]):
    """Valida que el archivo sea Excel"""
    if not filename or not filename.endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="El archivo debe ser Excel (.xlsx o .xls)")


def _validar_columnas_pagos(df: pd.DataFrame):
    """Valida que el DataFrame contenga las columnas requeridas"""
    # Aceptar ambos formatos: español y el formato del Excel del usuario
    required_columns_espanol = [
        "Cédula de Identidad",
        "Fecha de Pago",
        "Monto Pagado",
        "Número de Documento",
    ]
    required_columns_excel = [
        "cedula_cliente",
        "monto_pagado",  # También aceptar "monto_pagad" (truncado)
        "fecha_pago",
        "numero_documento",
    ]

    # Verificar si tiene las columnas en español
    tiene_espanol = all(col in df.columns for col in required_columns_espanol)
    # Verificar si tiene las columnas del Excel del usuario
    tiene_excel = all(
        col in df.columns or (col == "monto_pagado" and "monto_pagad" in df.columns) for col in required_columns_excel
    )

    if not (tiene_espanol or tiene_excel):
        raise HTTPException(
            status_code=400,
            detail=f"El archivo debe contener las columnas: {', '.join(required_columns_excel)} o {', '.join(required_columns_espanol)}",
        )


def _procesar_fila_pago(row: pd.Series, index: int, db: Session, current_user: User) -> tuple[Optional[dict], Optional[str]]:
    """Procesa una fila del Excel y retorna (resultado, error)"""
    try:
        # Detectar formato de columnas (español o Excel del usuario)
        if "cedula_cliente" in row.index:
            cedula = str(row["cedula_cliente"]).strip()
        elif "Cédula de Identidad" in row.index:
            cedula = str(row["Cédula de Identidad"]).strip()
        else:
            return None, f"Fila {index + 2}: Columna 'cedula_cliente' o 'Cédula de Identidad' no encontrada"

        # Fecha de pago - aceptar ambos formatos
        if "fecha_pago" in row.index:
            fecha_pago_str = str(row["fecha_pago"])
        elif "Fecha de Pago" in row.index:
            fecha_pago_str = str(row["Fecha de Pago"])
        else:
            return None, f"Fila {index + 2}: Columna 'fecha_pago' o 'Fecha de Pago' no encontrada"

        # Monto pagado - aceptar monto_pagad (truncado) o monto_pagado
        if "monto_pagado" in row.index:
            monto_pagado = Decimal(str(row["monto_pagado"]))
        elif "monto_pagad" in row.index:  # Versión truncada
            monto_pagado = Decimal(str(row["monto_pagad"]))
        elif "Monto Pagado" in row.index:
            monto_pagado = Decimal(str(row["Monto Pagado"]))
        else:
            return None, f"Fila {index + 2}: Columna 'monto_pagado' o 'Monto Pagado' no encontrada"

        # Número de documento
        if "numero_documento" in row.index:
            numero_documento = str(row["numero_documento"]).strip()
        elif "Número de Documento" in row.index:
            numero_documento = str(row["Número de Documento"]).strip()
        else:
            return None, f"Fila {index + 2}: Columna 'numero_documento' o 'Número de Documento' no encontrada"

        # Validar cliente existe
        cliente = db.query(Cliente).filter(Cliente.cedula == cedula).first()
        if not cliente:
            return None, f"Fila {index + 2}: Cliente con cédula {cedula} no encontrado"

        # Parsear fecha - manejar múltiples formatos
        try:
            # Intentar parsear con diferentes formatos
            # Formato del Excel del usuario: MM/DD/YYYY (ej: 9/11/2025, 5/12/2025)
            fecha_pago = pd.to_datetime(fecha_pago_str, dayfirst=False).to_pydatetime()
        except Exception as e:
            # Intentar formato alternativo
            try:
                fecha_pago = pd.to_datetime(fecha_pago_str, format="%m/%d/%Y").to_pydatetime()
            except Exception:
                return None, f"Fila {index + 2}: Fecha inválida ({fecha_pago_str}). Formato esperado: MM/DD/YYYY o YYYY-MM-DD"

        # ⚠️ IMPORTANTE: Insertar en pagos_staging (donde el dashboard consulta)
        # pagos_staging tiene fecha_pago y monto_pagado como TEXT

        # ✅ VERIFICAR CONCILIACIÓN: Si el numero_documento ya existe EXACTAMENTE, marcar como conciliado
        # Normalizar numero_documento (trim espacios) para comparación exacta
        numero_documento_normalizado = numero_documento.strip()

        # Buscar con comparación exacta (case-sensitive, sin espacios)
        pago_existente = (
            db.query(PagoStaging).filter(func.trim(PagoStaging.numero_documento) == numero_documento_normalizado).first()
        )

        conciliado = False
        fecha_conciliacion = None
        if pago_existente:
            # Si ya existe un pago con este número de documento EXACTAMENTE, marcarlo como conciliado
            conciliado = True
            fecha_conciliacion = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logger.info(
                f"✅ [carga_masiva] Número de documento '{numero_documento_normalizado}' "
                f"coincide EXACTAMENTE - marcando como conciliado"
            )

        pago_staging = PagoStaging(
            cedula_cliente=cedula,
            cedula=cedula,  # Columna alternativa
            prestamo_id=None,  # TODO: Buscar préstamo del cliente
            fecha_pago=fecha_pago,  # SQLAlchemy maneja la conversión si es necesario
            fecha_registro=datetime.now(),
            monto_pagado=monto_pagado,  # SQLAlchemy maneja la conversión si es necesario
            numero_documento=numero_documento_normalizado,  # ✅ Guardar normalizado (sin espacios)
            institucion_bancaria=None,
            estado="PAGADO",
            usuario_registro=current_user.email,
            conciliado=conciliado,  # ✅ Marcar como conciliado si el documento ya existe
            fecha_conciliacion=fecha_conciliacion,  # ✅ Fecha de conciliación si está conciliado
            activo=True,
        )

        db.add(pago_staging)
        db.commit()
        db.refresh(pago_staging)

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
