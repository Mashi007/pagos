import io
import logging
from datetime import datetime

import pandas as pd
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.pago import Pago
from app.models.user import User
from app.schemas.conciliacion import ConciliacionCreate, ConciliacionResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/template-conciliacion")
async def generar_template_conciliacion(current_user: User = Depends(get_current_user)):
    """Generar template Excel para conciliación bancaria"""
    try:
        logger.info(f"Usuario {current_user.email} generando template de conciliación")

        # Crear workbook
        from openpyxl import Workbook
        from openpyxl.worksheet.datavalidation import DataValidation

        wb = Workbook()

        # HOJA 1: INSTRUCCIONES
        ws_instrucciones = wb.active
        ws_instrucciones.title = "Instrucciones"

        instrucciones = [
            ["INSTRUCCIONES PARA CONCILIACIÓN BANCARIA"],
            [""],
            ["1. FORMATO DE ARCHIVO:"],
            ["   - Archivo Excel (.xlsx)"],
            ["   - Primera fila: encabezados de columnas"],
            ["   - Datos desde la segunda fila"],
            ["   - Máximo 100 registros por archivo"],
            [""],
            ["2. COLUMNAS REQUERIDAS:"],
            ["   - fecha: Fecha real del pago (formato YYYY-MM-DD)"],
            ["   - numero_documento: Número de documento del pago"],
            [""],
            ["3. PROCESO DE CONCILIACIÓN:"],
            ["   - El sistema compara el número de documento con la base de datos"],
            ["   - Si hay coincidencia EXACTA: se marca como CONCILIADO"],
            ["   - Si NO hay coincidencia: se marca como PENDIENTE"],
            [""],
            ["4. VALIDACIONES:"],
            ["   - Fecha debe estar en formato YYYY-MM-DD"],
            ["   - Número de documento debe coincidir EXACTAMENTE"],
            ["   - No se permiten caracteres especiales adicionales"],
            [""],
            ["5. EJEMPLOS DE DATOS VÁLIDOS:"],
            ["   - fecha: '2024-01-15'"],
            ["   - numero_documento: 'DOC001234'"],
            [""],
            ["6. NOTAS IMPORTANTES:"],
            ["   - No eliminar las columnas"],
            ["   - No cambiar el orden de las columnas"],
            ["   - Usar solo caracteres ASCII"],
            ["   - Verificar que los números de documento sean exactos"],
            ["   - Un archivo por vez"],
            [""],
            ["7. RESULTADO:"],
            ["   - Los pagos conciliados aparecerán en el resumen"],
            ["   - Los pendientes requerirán revisión manual"],
            [""],
            ["8. DESCONCILIACIÓN:"],
            ["   - Se puede desconciliar un pago ya conciliado"],
            ["   - Requiere formulario con justificación"],
            ["   - Se registra en auditoría"],
            [""],
            ["FECHA DE GENERACIÓN: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
            ["GENERADO POR: " + current_user.email],
        ]

        # Agregar instrucciones a la hoja
        for i, instruccion in enumerate(instrucciones, 1):
            ws_instrucciones.cell(row=i, column=1, value=instruccion[0])

        # HOJA 2: TEMPLATE VACÍA
        ws_template = wb.create_sheet("Template_Conciliacion")

        # Encabezados
        encabezados = ["fecha", "numero_documento"]
        for i, encabezado in enumerate(encabezados, 1):
            ws_template.cell(row=1, column=i, value=encabezado)

        # Ejemplo de datos
        ejemplo = ["2024-01-15", "DOC001234"]
        for i, valor in enumerate(ejemplo, 1):
            ws_template.cell(row=2, column=i, value=valor)

        # Aplicar validaciones
        # Validación para fecha (formato YYYY-MM-DD)
        dv_fecha = DataValidation(
            type="date", formula1="2020-01-01", formula2="2030-12-31"
        )
        dv_fecha.add("A2:A100")
        ws_template.add_data_validation(dv_fecha)

        # Guardar en memoria
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)

        logger.info("Template de conciliación generado exitosamente")

        return {
            "success": True,
            "message": "Template generado exitosamente",
            "filename": f"Template_Conciliacion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            "content": output.getvalue(),
        }

    except Exception as e:
        logger.error(f"Error generando template de conciliación: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}",
        )


@router.post("/procesar-conciliacion")
async def procesar_conciliacion(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Procesar archivo Excel de conciliación bancaria"""
    try:
        logger.info(f"Usuario {current_user.email} procesando conciliación bancaria")

        # Validar tipo de archivo
        if not file.filename.endswith((".xlsx", ".xls")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Archivo debe ser Excel (.xlsx o .xls)",
            )

        # Leer archivo Excel
        file_content = await file.read()
        df = pd.read_excel(io.BytesIO(file_content), sheet_name=1)  # Segunda hoja

        # Validar columnas requeridas
        required_columns = ["fecha", "numero_documento"]
        if not all(col in df.columns for col in required_columns):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Columnas requeridas: {required_columns}",
            )

        # Validar límite de registros
        if len(df) > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Máximo 100 registros por archivo",
            )

        # Procesar cada registro
        resultados = []
        conciliados = 0
        pendientes = 0

        for index, row in df.iterrows():
            fecha = row["fecha"]
            numero_documento = str(row["numero_documento"]).strip()

            # Buscar pago en BD
            pago = (
                db.query(Pago)
                .filter(and_(Pago.activo, Pago.numero_documento == numero_documento))
                .first()
            )

            if pago:
                # Marcar como conciliado
                pago.conciliado = True
                pago.fecha_conciliacion = datetime.now()
                conciliados += 1
                estado = "CONCILIADO"
            else:
                pendientes += 1
                estado = "PENDIENTE"

            resultados.append(
                {
                    "fila": index
                    + 2,  # +2 porque Excel es 1-indexed y primera fila es encabezado
                    "fecha": str(fecha),
                    "numero_documento": numero_documento,
                    "estado": estado,
                    "pago_id": pago.id if pago else None,
                }
            )

        # Guardar cambios
        db.commit()

        logger.info(
            f"Conciliación procesada: {conciliados} conciliados, {pendientes} pendientes"
        )

        return {
            "success": True,
            "message": "Conciliación procesada exitosamente",
            "resumen": {
                "total_registros": len(df),
                "conciliados": conciliados,
                "pendientes": pendientes,
            },
            "resultados": resultados,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error procesando conciliación: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}",
        )


@router.post(
    "/desconciliar-pago",
    response_model=ConciliacionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def desconciliar_pago(
    conciliacion_data: ConciliacionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Desconciliar un pago ya conciliado"""
    try:
        logger.info(
            f"Usuario {current_user.email} desconciliando pago {conciliacion_data.numero_documento_anterior}"
        )

        # Buscar el pago a desconciliar
        pago = (
            db.query(Pago)
            .filter(
                and_(
                    Pago.activo,
                    Pago.numero_documento
                    == conciliacion_data.numero_documento_anterior,
                    Pago.conciliado,
                )
            )
            .first()
        )

        if not pago:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pago no encontrado o no está conciliado",
            )

        # Desconciliar el pago
        pago.conciliado = False
        pago.fecha_conciliacion = None

        # Crear registro de auditoría (simulado - se integrará con módulo de auditoría)
        conciliacion_record = {
            "id": len(db.query(Pago).all()) + 1,  # ID temporal
            "cedula_cliente": conciliacion_data.cedula_cliente,
            "numero_documento_anterior": conciliacion_data.numero_documento_anterior,
            "numero_documento_nuevo": conciliacion_data.numero_documento_nuevo,
            "cedula_nueva": conciliacion_data.cedula_nueva,
            "nota": conciliacion_data.nota,
            "fecha": datetime.now(),
            "responsable": current_user.email,
            "pago_id": pago.id,
        }

        db.commit()

        logger.info(
            f"Pago {conciliacion_data.numero_documento_anterior} desconciliado exitosamente"
        )

        return conciliacion_record

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error desconciliando pago: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}",
        )


@router.get("/estado-conciliacion")
async def obtener_estado_conciliacion(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    """Obtener estado general de conciliación"""
    try:
        # Estadísticas generales
        total_pagos = db.query(Pago).filter(Pago.activo).count()
        pagos_conciliados = (
            db.query(Pago).filter(and_(Pago.activo, Pago.conciliado)).count()
        )
        pagos_pendientes = total_pagos - pagos_conciliados

        # Porcentaje de conciliación
        porcentaje_conciliacion = (
            (pagos_conciliados / total_pagos * 100) if total_pagos > 0 else 0
        )

        return {
            "success": True,
            "estadisticas": {
                "total_pagos": total_pagos,
                "pagos_conciliados": pagos_conciliados,
                "pagos_pendientes": pagos_pendientes,
                "porcentaje_conciliacion": round(porcentaje_conciliacion, 2),
            },
            "fecha_actualizacion": datetime.now(),
        }

    except Exception as e:
        logger.error(f"Error obteniendo estado de conciliación: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error interno del servidor: {str(e)}",
        )
