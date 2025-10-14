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

        # Mapear columnas del archivo venezolano a nuestro esquema
        column_mapping = {
            'CEDULA IDENT': 'cedula',
            'CEDULA IDENTIDAD': 'cedula', 
            'NOMBRE': 'nombre',
            'MOVIL': 'telefono',
            'CORREO ELECTRONICO': 'email'
        }
        
        # Renombrar columnas según el mapeo
        df = df.rename(columns=column_mapping)
        
        # Validar columnas requeridas
        required_columns = ['cedula', 'nombre']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Faltan columnas requeridas: {', '.join(missing_columns)}. Columnas disponibles: {list(df.columns)}"
            )

        # Procesar datos
        total_records = len(df)
        processed_records = 0
        errors = []
        errores_detallados = []
        
        for index, row in df.iterrows():
            try:
                # Limpiar datos
                cedula = str(row['cedula']).strip()
                nombre = str(row['nombre']).strip()
                telefono = str(row.get('telefono', '')).strip()
                email = str(row.get('email', '')).strip()
                
                # Validaciones específicas
                errores_validacion = []
                
                # Validar cédula venezolana
                if not cedula.startswith('V') or len(cedula) < 8:
                    errores_validacion.append('Formato de cédula inválido - debe empezar con V y tener al menos 8 caracteres')
                
                # Validar teléfono
                if telefono and telefono != 'error':
                    if not (telefono.startswith('+5804') or telefono.startswith('04')):
                        errores_validacion.append('Formato de teléfono inválido - debe empezar con +5804 o 04')
                
                # Validar email
                if email and email != 'error':
                    if '@' not in email or '.' not in email.split('@')[-1]:
                        errores_validacion.append('Formato de email inválido')
                
                # Saltar filas con datos de error
                if telefono == 'error' or email == 'error':
                    errores_detallados.append({
                        'row': index + 2,
                        'cedula': cedula,
                        'error': 'Datos marcados como "error" - móvil y/o email inválidos',
                        'data': row.to_dict(),
                        'tipo': 'cliente'
                    })
                    continue
                
                # Si hay errores de validación, agregar a la lista detallada
                if errores_validacion:
                    errores_detallados.append({
                        'row': index + 2,
                        'cedula': cedula,
                        'error': '; '.join(errores_validacion),
                        'data': row.to_dict(),
                        'tipo': 'cliente'
                    })
                    continue
                
                # Crear cliente
                cliente_data = ClienteCreate(
                    cedula=cedula,
                    nombre=nombre,
                    apellido="",  # No disponible en el archivo
                    telefono=telefono if telefono != 'error' else "",
                    email=email if email != 'error' else "",
                    direccion="",  # No disponible en el archivo
                    monto_prestamo=0,  # Se asignará después
                    estado="ACTIVO"
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
                errores_detallados.append({
                    'row': index + 2,
                    'cedula': str(row.get('cedula', 'N/A')),
                    'error': f'Error inesperado: {str(e)}',
                    'data': row.to_dict(),
                    'tipo': 'cliente'
                })

        # Guardar cambios
        db.commit()
        
        return {
            "success": True,
            "message": f"Procesados {processed_records} de {total_records} registros de clientes",
            "data": {
                "totalRecords": total_records,
                "processedRecords": processed_records,
                "errors": len(errores_detallados),
                "fileName": filename,
                "type": "clientes",
                "details": errors[:10]  # Primeros 10 errores
            },
            "erroresDetallados": errores_detallados
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar clientes: {str(e)}"
        )

async def procesar_pagos(content: bytes, filename: str, db: Session):
    """
    Procesar archivo de pagos con formato venezolano
    """
    try:
        # Leer Excel/CSV
        if filename.endswith('.csv'):
            df = pd.read_csv(io.BytesIO(content))
        else:
            df = pd.read_excel(io.BytesIO(content))

        # Mapear columnas del archivo venezolano a nuestro esquema
        column_mapping = {
            'CEDULA IDENTIDAD': 'cedula',
            'Fecha': 'fecha',
            'VIONTO PAGADCCHA': 'monto_pagado',  # Columna con nombre extraño
            'MONTO PAGADO': 'monto_pagado',
            'PAGO CUOT': 'fecha_pago_cuota',
            'DOCUMENTO PAGO': 'documento_pago'
        }
        
        # Renombrar columnas según el mapeo
        df = df.rename(columns=column_mapping)
        
        # Validar columnas requeridas
        required_columns = ['cedula', 'monto_pagado']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Faltan columnas requeridas: {', '.join(missing_columns)}. Columnas disponibles: {list(df.columns)}"
            )

        # Procesar datos
        total_records = len(df)
        processed_records = 0
        errors = []
        errores_detallados = []
        
        for index, row in df.iterrows():
            try:
                # Limpiar datos
                cedula = str(row['cedula']).strip()
                monto_pagado = float(row['monto_pagado'])
                fecha = str(row.get('fecha', ''))
                documento_pago = str(row.get('documento_pago', ''))
                
                # Validaciones específicas
                errores_validacion = []
                
                # Validar cédula venezolana
                if not cedula.startswith('V') or len(cedula) < 8:
                    errores_validacion.append('Formato de cédula inválido - debe empezar con V y tener al menos 8 caracteres')
                
                # Validar monto
                if monto_pagado <= 0:
                    errores_validacion.append('Monto debe ser mayor a 0')
                
                # Buscar cliente por cédula
                cliente = db.query(Cliente).filter(Cliente.cedula == cedula).first()
                
                if not cliente:
                    errores_detallados.append({
                        'row': index + 2,
                        'cedula': cedula,
                        'error': f'Cliente con cédula {cedula} no encontrado - debe cargar primero el archivo de clientes',
                        'data': row.to_dict(),
                        'tipo': 'pago'
                    })
                    continue
                
                # Si hay errores de validación, agregar a la lista detallada
                if errores_validacion:
                    errores_detallados.append({
                        'row': index + 2,
                        'cedula': cedula,
                        'error': '; '.join(errores_validacion),
                        'data': row.to_dict(),
                        'tipo': 'pago'
                    })
                    continue
                
                # Crear pago
                pago_data = {
                    "cliente_id": cliente.id,
                    "monto": monto_pagado,
                    "fecha_pago": fecha if fecha else None,
                    "metodo_pago": "TRANSFERENCIA",
                    "estado": "CONFIRMADO",
                    "referencia": documento_pago,
                    "observaciones": f"Importado desde Excel - {filename}"
                }
                
                # Crear registro de pago (usando el modelo Pago si existe)
                # Por ahora, actualizamos el monto del préstamo del cliente
                if cliente.monto_prestamo:
                    cliente.monto_prestamo -= monto_pagado
                    if cliente.monto_prestamo <= 0:
                        cliente.estado = "PAGADO"
                else:
                    cliente.monto_prestamo = -monto_pagado  # Saldo a favor
                
                db.commit()
                processed_records += 1
                
            except Exception as e:
                errores_detallados.append({
                    'row': index + 2,
                    'cedula': str(row.get('cedula', 'N/A')),
                    'error': f'Error inesperado: {str(e)}',
                    'data': row.to_dict(),
                    'tipo': 'pago'
                })
        
        return {
            "success": True,
            "message": f"Procesados {processed_records} de {total_records} registros de pagos",
            "data": {
                "totalRecords": total_records,
                "processedRecords": processed_records,
                "errors": len(errores_detallados),
                "fileName": filename,
                "type": "pagos",
                "details": errors[:10]  # Solo los primeros 10 errores
            },
            "erroresDetallados": errores_detallados
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al procesar pagos: {str(e)}"
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