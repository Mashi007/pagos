from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List, Optional
import pandas as pd
import io
import os
from datetime import datetime

from app.db.session import get_db
from app.models.cliente import Cliente
from app.schemas.cliente import ClienteCreate
from app.core.security import get_current_user
from app.models.user import User

router = APIRouter()

@router.post("/upload")
async def cargar_archivo_excel(
    file: UploadFile = File(...),
    type: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cargar archivo Excel para importar datos masivamente
    """
    try:
        # Validar tipo de archivo
        if not file.filename.endswith(('.xlsx', '.xls', '.csv')):
            raise HTTPException(
                status_code=400, 
                detail="Solo se permiten archivos Excel (.xlsx, .xls) o CSV (.csv)"
            )

        # Validar tamaño (máximo 10MB)
        if file.size > 10 * 1024 * 1024:
            raise HTTPException(
                status_code=413,
                detail="El archivo excede el límite de tamaño permitido (10MB)"
            )

        # Leer el archivo
        content = await file.read()
        
        # Procesar según el tipo
        if type == "clientes":
            return await procesar_clientes(content, file.filename, db)
        elif type == "prestamos":
            return await procesar_prestamos(content, file.filename, db)
        elif type == "pagos":
            return await procesar_pagos(content, file.filename, db)
                        else:
            raise HTTPException(
                status_code=400,
                detail="Tipo de datos no válido"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar el archivo: {str(e)}"
        )

async def procesar_clientes(content: bytes, filename: str, db: Session):
    """
    Procesar archivo de clientes
    """
    try:
        # Leer Excel/CSV
        if filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content))
        else:
            df = pd.read_excel(io.BytesIO(content))

        # Validar columnas requeridas
        required_columns = ['cedula', 'nombre', 'apellido', 'telefono']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Faltan columnas requeridas: {', '.join(missing_columns)}"
            )

        # Procesar datos
        total_records = len(df)
        processed_records = 0
        errors = []
        
        for index, row in df.iterrows():
            try:
                # Crear cliente
                cliente_data = ClienteCreate(
                    cedula=str(row['cedula']),
                    nombre=str(row['nombre']),
                    apellido=str(row['apellido']),
                    telefono=str(row['telefono']),
                    email=str(row.get('email', '')),
                    direccion=str(row.get('direccion', '')),
                    monto_prestamo=float(row.get('monto_prestamo', 0)),
                    estado=str(row.get('estado', 'ACTIVO'))
                )

                # Verificar si ya existe
                existing_cliente = db.query(Cliente).filter(
                    Cliente.cedula == cliente_data.cedula
                ).first()

                if existing_cliente:
                    # Actualizar cliente existente
                    for key, value in cliente_data.dict().items():
                        setattr(existing_cliente, key, value)
                    existing_cliente.updated_at = datetime.utcnow()
                else:
                    # Crear nuevo cliente
                    new_cliente = Cliente(**cliente_data.dict())
                    db.add(new_cliente)

                processed_records += 1
                
            except Exception as e:
                errors.append(f"Fila {index + 1}: {str(e)}")

        # Guardar cambios
        db.commit()
        
        return {
            "success": True,
            "message": "Archivo procesado exitosamente",
            "data": {
                "totalRecords": total_records,
                "processedRecords": processed_records,
                "errors": len(errors),
                "fileName": filename,
                "details": errors[:10]  # Primeros 10 errores
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar clientes: {str(e)}"
        )

async def procesar_prestamos(content: bytes, filename: str, db: Session):
    """
    Procesar archivo de préstamos
    """
    # Implementar lógica para préstamos
    return {
        "success": True,
        "message": "Procesamiento de préstamos en desarrollo",
        "data": {
            "totalRecords": 0,
            "processedRecords": 0,
            "errors": 0,
            "fileName": filename
        }
    }

async def procesar_pagos(content: bytes, filename: str, db: Session):
    """
    Procesar archivo de pagos
    """
    # Implementar lógica para pagos
    return {
        "success": True,
        "message": "Procesamiento de pagos en desarrollo",
        "data": {
            "totalRecords": 0,
            "processedRecords": 0,
            "errors": 0,
            "fileName": filename
        }
    }

@router.get("/template/{type}")
async def descargar_template(type: str):
    """
    Descargar template Excel para carga masiva
    """
    try:
        # Crear template según el tipo
        if type == "clientes":
        template_data = {
                'cedula': ['12345678', '87654321', '11223344'],
                'nombre': ['Juan', 'María', 'Carlos'],
                'apellido': ['Pérez', 'García', 'López'],
                'telefono': ['3001234567', '3007654321', '3009988776'],
                'email': ['juan@email.com', 'maria@email.com', 'carlos@email.com'],
                'direccion': ['Calle 123 #45-67', 'Carrera 78 #12-34', 'Avenida 56 #89-01'],
                'monto_prestamo': [500000, 750000, 300000],
                'fecha_prestamo': ['2024-01-15', '2024-01-20', '2024-01-25'],
                'estado': ['ACTIVO', 'ACTIVO', 'ACTIVO']
            }
        else:
            raise HTTPException(
                status_code=400,
                detail="Tipo de template no válido"
            )

        # Crear DataFrame
        df = pd.DataFrame(template_data)
        
        # Crear archivo Excel en memoria
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Template', index=False)

        output.seek(0)

        # Crear respuesta
        filename = f"template_{type}_rapicredit.xlsx"
        
        return FileResponse(
            path=output,
            filename=filename,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al generar template: {str(e)}"
        )

@router.get("/historial")
async def obtener_historial_cargas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Obtener historial de cargas masivas
    """
    # Implementar lógica para obtener historial
    return {
        "success": True,
        "data": [
            {
                "id": 1,
                "fileName": "clientes_enero.xlsx",
                "type": "clientes",
                "totalRecords": 150,
                "processedRecords": 148,
                "errors": 2,
                "createdAt": "2024-01-15T10:30:00Z",
                "createdBy": current_user.email
            }
        ]
    }