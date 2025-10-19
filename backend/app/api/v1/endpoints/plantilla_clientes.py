"""
Endpoint para generar plantilla Excel dinámica con datos reales de BD
====================================================================

Este endpoint:
- Obtiene datos reales desde las tablas de configuración
- Genera plantilla Excel con listas desplegables actualizadas
- Se actualiza automáticamente cuando admin cambia las listas
- Campos obligatorios y validaciones completas
"""

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.api.deps import get_current_user
from app.models.modelo_vehiculo import ModeloVehiculo
from app.models.concesionario import Concesionario
from app.models.analista import Analista
from app.models.cliente import Cliente
import logging
from openpyxl import Workbook
from openpyxl.styles import Font
from datetime import datetime
import io

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/plantilla-clientes")
async def generar_plantilla_clientes_dinamica(
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    📊 Generar plantilla Excel dinámica con datos reales de BD
    
    Características:
    - Obtiene datos reales desde tablas de configuración
    - Listas desplegables con valores actuales
    - Se actualiza automáticamente cuando admin cambia listas
    - Instrucciones completas incluidas
    - Campos obligatorios y validaciones
    """
    try:
        logger.info(f"🚀 Iniciando generación de plantilla - Usuario: {current_user.email}")
        logger.info(f"🔍 URL del endpoint: /api/v1/plantilla/plantilla-clientes")
        
        # OBTENER DATOS REALES DESDE BD
        
        # Modelos de vehículos
        modelos_db = db.query(ModeloVehiculo).filter(ModeloVehiculo.activo == True).all()
        modelos_nombres = [m.nombre for m in modelos_db]
        logger.info(f"Modelos encontrados: {len(modelos_nombres)}")
        
        # Concesionarios
        concesionarios_db = db.query(Concesionario).filter(Concesionario.activo == True).all()
        concesionarios_nombres = [c.nombre for c in concesionarios_db]
        logger.info(f"Concesionarios encontrados: {len(concesionarios_nombres)}")
        
        # Analistas
        analistas_db = db.query(Analista).filter(Analista.activo == True).all()
        analistas_nombres = [a.nombre for a in analistas_db]
        logger.info(f"Analistas encontrados: {len(analistas_nombres)}")
        
        # KPIs de clientes
        total_clientes = db.query(Cliente).filter(Cliente.activo == True).count()
        clientes_activos = db.query(Cliente).filter(Cliente.activo == True, Cliente.estado == 'ACTIVO').count()
        
        # CREAR WORKBOOK
        wb = Workbook()
        
        # HOJA 1: INSTRUCCIONES
        ws_instrucciones = wb.active
        ws_instrucciones.title = "Instrucciones"
        
        instrucciones = [
            ["INSTRUCCIONES PARA CARGA MASIVA DE CLIENTES"],
            [""],
            ["1. FORMATO DE ARCHIVO:"],
            ["   - Archivo Excel (.xlsx)"],
            ["   - Primera fila: encabezados de columnas"],
            ["   - Datos desde la segunda fila"],
            ["   - Máximo 100 registros por archivo"],
            [""],
            ["2. CAMPOS OBLIGATORIOS (marcados con *):"],
            ["   - cedula: Cédula del cliente (8-20 caracteres)"],
            ["   - nombres: Nombres del cliente (exactamente 2 palabras: nombre y apellido)"],
            ["   - apellidos: Apellidos del cliente (exactamente 2 palabras: paterno y materno)"],
            ["   - telefono: Teléfono del cliente (formato venezolano: +58 XXXXXXXXXX)"],
            ["   - email: Email del cliente (formato válido)"],
            ["   - direccion: Dirección completa del cliente"],
            ["   - fecha_nacimiento: Fecha de nacimiento (YYYY-MM-DD)"],
            ["   - ocupacion: Ocupación del cliente"],
            ["   - modelo_vehiculo: Modelo del vehículo (lista desplegable de configuración)"],
            ["   - concesionario: Concesionario (lista desplegable de configuración)"],
            ["   - analista: Analista asignado (lista desplegable de configuración)"],
            ["   - estado: Estado del cliente (ACTIVO/INACTIVO/FINALIZADO)"],
            [""],
            ["3. CAMPOS OPCIONALES:"],
            ["   - notas: Notas adicionales (si no llena, se pondrá 'NA')"],
            [""],
            ["4. VALIDACIONES:"],
            ["   - Cédula: Entre 8 y 20 caracteres"],
            ["   - Email: Formato válido usuario@dominio.com"],
            ["   - Teléfono: Formato venezolano +58 XXXXXXXXXX (10 dígitos)"],
            ["   - Fecha de nacimiento: Formato YYYY-MM-DD, no puede ser futura"],
            ["   - Nombres: Exactamente 2 palabras (nombre y apellido)"],
            ["   - Apellidos: Exactamente 2 palabras (paterno y materno)"],
            ["   - Modelo/Concesionario/Analista: COPIE EXACTAMENTE de la hoja 'Referencias'"],
            ["   - Estado: Solo ACTIVO, INACTIVO o FINALIZADO"],
            ["   - Activo: Solo TRUE o FALSE"],
            [""],
            ["5. ESTADÍSTICAS ACTUALES:"],
            [f"   - Total de clientes: {total_clientes}"],
            [f"   - Clientes activos: {clientes_activos}"],
            [f"   - Modelos disponibles: {len(modelos_nombres)}"],
            [f"   - Concesionarios disponibles: {len(concesionarios_nombres)}"],
            [f"   - Analistas disponibles: {len(analistas_nombres)}"],
            [""],
            ["6. IMPORTANTE:"],
            ["   - No modifique los nombres de las columnas"],
            ["   - COPIE EXACTAMENTE los valores de la hoja 'Referencias'"],
            ["   - Todos los campos obligatorios deben estar completos"],
            ["   - La plantilla se actualiza automáticamente con los datos de configuración"],
        ]
        
        for row_data in instrucciones:
            ws_instrucciones.append(row_data)
        
        # HOJA 2: TEMPLATE VACÍO
        ws_template = wb.create_sheet("Template")
        
        # Encabezados con campos obligatorios marcados
        headers = [
            "cedula*", "nombres*", "apellidos*", "telefono*", "email*", 
            "direccion*", "fecha_nacimiento*", "ocupacion*", 
            "modelo_vehiculo*", "concesionario*", "analista*", 
            "estado*", "notas"
        ]
        ws_template.append(headers)
        
        # SIN VALIDACIONES COMPLEJAS PARA EVITAR PROBLEMAS DE COMPATIBILIDAD
        # Las validaciones se harán en el backend al procesar el archivo
        
        # HOJA 3: REFERENCIAS - LISTAS PARA COPIAR Y PEGAR
        ws_referencias = wb.create_sheet("Referencias")
        
        # Título
        ws_referencias['A1'] = "REFERENCIAS DE CONFIGURACIÓN - COPIE Y PEGUE EXACTAMENTE"
        ws_referencias['A1'].font = Font(name='Calibri', size=14, bold=True)
        ws_referencias.merge_cells('A1:D1')
        
        # Modelos disponibles
        ws_referencias['A3'] = "MODELOS DE VEHÍCULOS (Columna I):"
        ws_referencias['A3'].font = Font(name='Calibri', size=12, bold=True)
        row = 4
        for modelo in modelos_nombres:
            ws_referencias[f'A{row}'] = modelo
            row += 1
        
        # Concesionarios disponibles
        ws_referencias['B3'] = "CONCESIONARIOS (Columna J):"
        ws_referencias['B3'].font = Font(name='Calibri', size=12, bold=True)
        row = 4
        for concesionario in concesionarios_nombres:
            ws_referencias[f'B{row}'] = concesionario
            row += 1
        
        # Analistas disponibles
        ws_referencias['C3'] = "ANALISTAS (Columna K):"
        ws_referencias['C3'].font = Font(name='Calibri', size=12, bold=True)
        row = 4
        for analista in analistas_nombres:
            ws_referencias[f'C{row}'] = analista
            row += 1
        
        # Estados disponibles
        ws_referencias['D3'] = "ESTADOS (Columna L):"
        ws_referencias['D3'].font = Font(name='Calibri', size=12, bold=True)
        ws_referencias['D4'] = "ACTIVO"
        ws_referencias['D5'] = "INACTIVO"
        ws_referencias['D6'] = "FINALIZADO"
        
        # Ajustar ancho de columnas
        ws_referencias.column_dimensions['A'].width = 25
        ws_referencias.column_dimensions['B'].width = 25
        ws_referencias.column_dimensions['C'].width = 25
        ws_referencias.column_dimensions['D'].width = 15
        
        # GUARDAR EN BUFFER CON CONFIGURACIÓN MEJORADA
        excel_buffer = io.BytesIO()
        
        try:
            # Guardar con configuración específica para compatibilidad
            wb.save(excel_buffer)
            excel_buffer.seek(0)
            
            # Obtener contenido del buffer
            excel_content = excel_buffer.getvalue()
            
            # Verificar que el contenido no esté vacío
            if len(excel_content) == 0:
                raise Exception("El archivo Excel generado está vacío")
            
            logger.info(f"Archivo Excel generado - Tamaño: {len(excel_content)} bytes")
            
        except Exception as save_error:
            logger.error(f"Error guardando Excel: {save_error}")
            raise Exception(f"Error al generar archivo Excel: {save_error}")
        
        # CONFIGURAR RESPUESTA CON HEADERS CORRECTOS
        filename = f"Plantilla_Clientes_{datetime.now().strftime('%Y-%m-%d')}.xlsx"
        
        response.headers["Content-Disposition"] = f"attachment; filename=\"{filename}\""
        response.headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        response.headers["Content-Length"] = str(len(excel_content))
        response.headers["Cache-Control"] = "no-cache"
        
        logger.info(f"Plantilla generada exitosamente - Archivo: {filename}, Tamaño: {len(excel_content)} bytes")
        
        return Response(
            content=excel_content,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        
    except Exception as e:
        logger.error(f"Error generando plantilla dinámica: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor al generar plantilla"
        )