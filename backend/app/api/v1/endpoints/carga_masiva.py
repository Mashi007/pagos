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
from app.api.deps import get_current_user
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
            return await procesar_clientes(content, file.filename, db, current_user.id)
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

async def procesar_clientes(content: bytes, filename: str, db: Session, usuario_id: int = None):
    """
    Procesar archivo de clientes con validaciones completas y auditoría
    """
    try:
        # 🔍 AUDITORÍA: Registrar inicio de carga masiva
        from app.models.auditoria import Auditoria, TipoAccion
        
        auditoria_inicio = Auditoria.registrar(
            usuario_id=usuario_id,
            accion=TipoAccion.CREAR,
            tabla="Cliente",
            descripcion=f"Inicio de carga masiva de clientes desde archivo: {filename}",
            resultado="EXITOSO"
        )
        db.add(auditoria_inicio)
        db.flush()
        
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
                
                # Crear cliente directamente con el modelo Cliente
                cliente_data = {
                    "cedula": cedula,
                    "nombres": nombre,
                    "apellidos": "",  # No disponible en el archivo
                    "telefono": telefono if telefono != 'error' else "",
                    "email": email if email != 'error' else "",
                    "direccion": "",  # No disponible en el archivo
                    "estado": "ACTIVO",
                    "activo": True,
                    "fecha_registro": datetime.utcnow(),
                    "usuario_registro": "CARGA_MASIVA"
                }

                # Verificar si ya existe
                existing_cliente = db.query(Cliente).filter(
                    Cliente.cedula == cedula
                ).first()

                if existing_cliente:
                    # Actualizar cliente existente
                    for key, value in cliente_data.items():
                        if key not in ['cedula', 'fecha_registro']:  # No actualizar cédula ni fecha de registro
                            setattr(existing_cliente, key, value)
                    existing_cliente.fecha_actualizacion = datetime.utcnow()
                else:
                    # Crear nuevo cliente
                    new_cliente = Cliente(**cliente_data)
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
                
                # Buscar cliente por cédula para articular el pago
                cliente = db.query(Cliente).filter(Cliente.cedula == cedula).first()
                
                if not cliente:
                    errores_detallados.append({
                        'row': index + 2,
                        'cedula': cedula,
                        'error': 'Cliente no encontrado con esta cédula',
                        'data': row.to_dict(),
                        'tipo': 'pago'
                    })
                    continue
                
                # Crear registro de pago usando el modelo Pago
                from app.models.pago import Pago
                
                pago_data = {
                    "prestamo_id": 1,  # Por ahora usar préstamo por defecto
                    "numero_cuota": 1,
                    "codigo_pago": f"PAGO_{cedula}_{index}",
                    "monto_cuota_programado": monto_pagado,
                    "monto_pagado": monto_pagado,
                    "monto_total": monto_pagado,
                    "fecha_pago": fecha if fecha else datetime.utcnow().date(),
                    "fecha_vencimiento": fecha if fecha else datetime.utcnow().date(),
                    "metodo_pago": "TRANSFERENCIA",
                    "numero_operacion": documento_pago,
                    "estado": "CONFIRMADO",
                    "tipo_pago": "NORMAL",
                    "observaciones": f"Importado desde Excel - {filename}"
                }
                
                # Crear nuevo pago
                new_pago = Pago(**pago_data)
                db.add(new_pago)
                
                # Actualizar estado del cliente si es necesario
                if cliente.estado_financiero == "MORA":
                    cliente.estado_financiero = "AL_DIA"
                    cliente.dias_mora = 0
                
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

@router.post("/corregir-error")
async def corregir_error(
    request: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Corregir un error individual de carga masiva
    """
    try:
        tipo = request.get('tipo')
        cedula = request.get('cedula')
        data = request.get('data')
        
        if tipo == 'cliente':
            # Buscar cliente existente
            cliente = db.query(Cliente).filter(Cliente.cedula == cedula).first()
            if cliente:
                # Actualizar datos del cliente
                for key, value in data.items():
                    if hasattr(cliente, key):
                        setattr(cliente, key, value)
                cliente.fecha_actualizacion = datetime.utcnow()
                db.commit()
                return {"success": True, "message": "Cliente corregido exitosamente"}
            else:
                # Crear nuevo cliente
                cliente_data = {
                    "cedula": cedula,
                    "nombres": data.get('nombre', ''),
                    "apellidos": data.get('apellido', ''),
                    "telefono": data.get('telefono', ''),
                    "email": data.get('email', ''),
                    "direccion": data.get('direccion', ''),
                    "estado": "ACTIVO",
                    "activo": True,
                    "fecha_registro": datetime.utcnow(),
                    "usuario_registro": current_user.email
                }
                new_cliente = Cliente(**cliente_data)
                db.add(new_cliente)
                db.commit()
                return {"success": True, "message": "Cliente creado exitosamente"}
        
        elif tipo == 'pago':
            # Buscar cliente por cédula
            cliente = db.query(Cliente).filter(Cliente.cedula == cedula).first()
            if not cliente:
                return {"success": False, "message": "Cliente no encontrado"}
            
            # Crear pago
            from app.models.pago import Pago
            pago_data = {
                "prestamo_id": 1,  # Por ahora usar préstamo por defecto
                "numero_cuota": 1,
                "codigo_pago": f"PAGO_{cedula}_{datetime.utcnow().timestamp()}",
                "monto_cuota_programado": float(data.get('monto_pagado', 0)),
                "monto_pagado": float(data.get('monto_pagado', 0)),
                "monto_total": float(data.get('monto_pagado', 0)),
                "fecha_pago": datetime.strptime(data.get('fecha_pago', ''), '%d/%m/%Y').date() if data.get('fecha_pago') else datetime.utcnow().date(),
                "fecha_vencimiento": datetime.strptime(data.get('fecha_pago', ''), '%d/%m/%Y').date() if data.get('fecha_pago') else datetime.utcnow().date(),
                "metodo_pago": data.get('metodo_pago', 'TRANSFERENCIA'),
                "numero_operacion": data.get('documento_pago', ''),
                "estado": "CONFIRMADO",
                "tipo_pago": "NORMAL",
                "observaciones": f"Corregido manualmente por {current_user.email}"
            }
            new_pago = Pago(**pago_data)
            db.add(new_pago)
            db.commit()
            return {"success": True, "message": "Pago corregido exitosamente"}
        
        else:
            return {"success": False, "message": "Tipo de corrección no válido"}
            
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al corregir registro: {str(e)}"
        )

@router.post("/reenviar")
async def reenviar_registros(
    request: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Reenviar registros corregidos
    """
    try:
        tipo = request.get('tipo')
        registros = request.get('registros', [])
        
        processed = 0
        errors = []
        
        for registro in registros:
            try:
                if tipo == 'cliente':
                    # Procesar cliente
                    cliente_data = {
                        "cedula": registro.get('cedula'),
                        "nombres": registro.get('nombre', ''),
                        "apellidos": registro.get('apellido', ''),
                        "telefono": registro.get('telefono', ''),
                        "email": registro.get('email', ''),
                        "direccion": registro.get('direccion', ''),
                        "estado": "ACTIVO",
                        "activo": True,
                        "fecha_registro": datetime.utcnow(),
                        "usuario_registro": current_user.email
                    }
                    
                    # Verificar si existe
                    existing = db.query(Cliente).filter(Cliente.cedula == cliente_data['cedula']).first()
                    if existing:
                        for key, value in cliente_data.items():
                            if key not in ['cedula', 'fecha_registro']:
                                setattr(existing, key, value)
                        existing.fecha_actualizacion = datetime.utcnow()
                    else:
                        new_cliente = Cliente(**cliente_data)
                        db.add(new_cliente)
                    
                    processed += 1
                    
                elif tipo == 'pago':
                    # Procesar pago
                    cliente = db.query(Cliente).filter(Cliente.cedula == registro.get('cedula')).first()
                    if cliente:
                        from app.models.pago import Pago
                        pago_data = {
                            "prestamo_id": 1,
                            "numero_cuota": 1,
                            "codigo_pago": f"PAGO_{registro.get('cedula')}_{processed}",
                            "monto_cuota_programado": float(registro.get('monto_pagado', 0)),
                            "monto_pagado": float(registro.get('monto_pagado', 0)),
                            "monto_total": float(registro.get('monto_pagado', 0)),
                            "fecha_pago": datetime.strptime(registro.get('fecha_pago', ''), '%d/%m/%Y').date() if registro.get('fecha_pago') else datetime.utcnow().date(),
                            "fecha_vencimiento": datetime.strptime(registro.get('fecha_pago', ''), '%d/%m/%Y').date() if registro.get('fecha_pago') else datetime.utcnow().date(),
                            "metodo_pago": registro.get('metodo_pago', 'TRANSFERENCIA'),
                            "numero_operacion": registro.get('documento_pago', ''),
                            "estado": "CONFIRMADO",
                            "tipo_pago": "NORMAL",
                            "observaciones": f"Reenviado por {current_user.email}"
                        }
                        new_pago = Pago(**pago_data)
                        db.add(new_pago)
                        processed += 1
                    else:
                        errors.append(f"Cliente no encontrado para cédula: {registro.get('cedula')}")
                        
            except Exception as e:
                errors.append(f"Error procesando registro: {str(e)}")
        
        db.commit()
        
        return {
            "success": True,
            "message": f"Procesados {processed} registros exitosamente",
            "data": {
                "processedRecords": processed,
                "errors": len(errors),
                "details": errors
            }
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error al reenviar registros: {str(e)}"
        )
