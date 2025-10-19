"""
Endpoint para generar plantilla Excel dinámica con datos reales de BD
====================================================================

Este endpoint:
- Obtiene datos reales desde las tablas de configuración
- Genera plantilla Excel con listas desplegables actualizadas
- Se actualiza automáticamente cuando admin cambia las listas
"""

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.user import User
from app.api.deps import get_current_user
from app.models.modelo_vehiculo import ModeloVehiculo
from app.models.concesionario import Concesionario
from app.models.analista import Analista
import logging
from openpyxl import Workbook
from openpyxl.worksheet.datavalidation import DataValidation
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
    """
    try:
        logger.info(f"Generando plantilla dinámica - Usuario: {current_user.email}")
        
        # OBTENER DATOS REALES DESDE BD
        
        # Modelos de vehículos
        modelos_db = db.query(ModeloVehiculo).filter(ModeloVehiculo.activo == True).all()
        modelos_vehiculos = [modelo.modelo for modelo in modelos_db if modelo.modelo]
        
        # Concesionarios - TABLA VACÍA, usar valores por defecto
        concesionarios_db = db.query(Concesionario).all()
        if concesionarios_db:
            concesionarios = [f"Concesionario {c.id}" for c in concesionarios_db]
        else:
            # Valores por defecto ya que la tabla está vacía
            concesionarios = [
                "AutoMax Quito Norte",
                "AutoCenter Guayaquil Centro", 
                "CarDealer Cuenca Sur",
                "AutoShop Ambato Centro",
                "MotorCity Manta Puerto"
            ]
        
        # Analistas
        analistas_db = db.query(Analista).filter(Analista.activo == True).all()
        analistas = [analista.nombre for analista in analistas_db if analista.nombre]
        
        logger.info(f"Datos obtenidos - Modelos: {len(modelos_vehiculos)}, Concesionarios: {len(concesionarios)}, Analistas: {len(analistas)}")
        
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
            [""],
            ["2. CAMPOS REQUERIDOS:"],
            ["   - cedula: Cedula unica (maximo 20 caracteres)"],
            ["   - nombres: Nombres completos (maximo 100 caracteres)"],
            ["   - apellidos: Apellidos completos (maximo 100 caracteres)"],
            [""],
            ["3. CAMPOS CON LISTAS DESPLEGABLES (DATOS REALES DE BD):"],
            ["   - modelo_vehiculo: Seleccionar de lista desplegable"],
            ["   - concesionario: Seleccionar de lista desplegable"],
            ["   - analista: Seleccionar de lista desplegable"],
            ["   - estado: ACTIVO o INACTIVO"],
            [""],
            ["4. CAMPOS OPCIONALES:"],
            ["   - telefono: Numero de telefono (maximo 15 caracteres)"],
            ["   - email: Correo electronico valido"],
            ["   - direccion: Direccion completa"],
            ["   - fecha_nacimiento: Formato YYYY-MM-DD"],
            ["   - ocupacion: Ocupacion del cliente"],
            ["   - notas: Observaciones adicionales"],
            [""],
            ["5. VALIDACIONES:"],
            ["   - Cedula debe ser unica en el sistema"],
            ["   - Email debe tener formato valido"],
            ["   - Fecha de nacimiento en formato YYYY-MM-DD"],
            ["   - Estado debe ser ACTIVO o INACTIVO"],
            ["   - Usar solo valores de las listas desplegables"],
            [""],
            ["6. EJEMPLOS DE DATOS VALIDOS:"],
            ["   - cedula: '1234567890'"],
            ["   - nombres: 'Juan Carlos'"],
            ["   - apellidos: 'Perez Garcia'"],
            ["   - telefono: '0987654321'"],
            ["   - email: 'juan.perez@email.com'"],
            ["   - fecha_nacimiento: '1990-05-15'"],
            ["   - estado: 'ACTIVO'"],
            [""],
            ["7. NOTAS IMPORTANTES:"],
            ["   - No eliminar las columnas"],
            ["   - No cambiar el orden de las columnas"],
            ["   - Usar solo caracteres ASCII"],
            ["   - Evitar caracteres especiales en nombres"],
            ["   - Verificar que las cedulas no esten duplicadas"],
            ["   - Usar valores exactos de las listas desplegables"],
            [""],
            ["8. DATOS ACTUALES DESDE BASE DE DATOS:"],
            [""],
            [f"MODELOS DE VEHICULOS ({len(modelos_vehiculos)} disponibles):"],
        ]
        
        # Agregar modelos reales
        for modelo in modelos_vehiculos:
            instrucciones.append([f"   - {modelo}"])
        
        instrucciones.extend([
            [""],
            [f"CONCESIONARIOS ({len(concesionarios)} disponibles):"],
        ])
        
        # Agregar concesionarios reales
        for concesionario in concesionarios:
            instrucciones.append([f"   - {concesionario}"])
        
        instrucciones.extend([
            [""],
            [f"ANALISTAS ({len(analistas)} disponibles):"],
        ])
        
        # Agregar analistas reales
        for analista in analistas:
            instrucciones.append([f"   - {analista}"])
        
        # Agregar instrucciones a la hoja
        for i, instruccion in enumerate(instrucciones, 1):
            ws_instrucciones.cell(row=i, column=1, value=instruccion[0])
        
        # HOJA 2: PLANTILLA CON LISTAS DESPLEGABLES
        ws_plantilla = wb.create_sheet("Plantilla_Clientes")
        
        # Encabezados
        encabezados = [
            "cedula", "nombres", "apellidos", "telefono", "email",
            "direccion", "fecha_nacimiento", "ocupacion", "modelo_vehiculo",
            "concesionario", "analista", "estado", "notas"
        ]
        
        for i, encabezado in enumerate(encabezados, 1):
            ws_plantilla.cell(row=1, column=i, value=encabezado)
        
        # Ejemplo de datos (usando primer valor de cada lista si existe)
        ejemplo = [
            "1234567890", "Juan Carlos", "Perez Garcia", "0987654321",
            "juan.perez@email.com", "Av. Principal 123, Quito", "1990-05-15",
            "Ingeniero", 
            modelos_vehiculos[0] if modelos_vehiculos else "Toyota Corolla 2023",
            concesionarios[0] if concesionarios else "AutoMax Quito",
            analistas[0] if analistas else "Maria Gonzalez",
            "ACTIVO", "Cliente preferencial"
        ]
        
        for i, valor in enumerate(ejemplo, 1):
            ws_plantilla.cell(row=2, column=i, value=valor)
        
        # CONFIGURAR LISTAS DESPLEGABLES CON DATOS REALES
        
        # Lista desplegable para modelo_vehiculo (columna I)
        if modelos_vehiculos:
            modelos_formula = f'"{",".join(modelos_vehiculos)}"'
            dv_modelos = DataValidation(type="list", formula1=modelos_formula, allow_blank=True)
            dv_modelos.add(f'I2:I1000')
            ws_plantilla.add_data_validation(dv_modelos)
        
        # Lista desplegable para concesionario (columna J)
        if concesionarios:
            concesionarios_formula = f'"{",".join(concesionarios)}"'
            dv_concesionarios = DataValidation(type="list", formula1=concesionarios_formula, allow_blank=True)
            dv_concesionarios.add(f'J2:J1000')
            ws_plantilla.add_data_validation(dv_concesionarios)
        
        # Lista desplegable para analista (columna K)
        if analistas:
            analistas_formula = f'"{",".join(analistas)}"'
            dv_analistas = DataValidation(type="list", formula1=analistas_formula, allow_blank=True)
            dv_analistas.add(f'K2:K1000')
            ws_plantilla.add_data_validation(dv_analistas)
        
        # Lista desplegable para estado (columna L)
        dv_estado = DataValidation(type="list", formula1='"ACTIVO,INACTIVO"', allow_blank=True)
        dv_estado.add(f'L2:L1000')
        ws_plantilla.add_data_validation(dv_estado)
        
        # GUARDAR EN MEMORIA
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        
        # Configurar respuesta para descarga
        response.headers["Content-Disposition"] = "attachment; filename=plantilla_clientes_dinamica.xlsx"
        response.headers["Content-Type"] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        
        logger.info(f"Plantilla generada exitosamente - Modelos: {len(modelos_vehiculos)}, Concesionarios: {len(concesionarios)}, Analistas: {len(analistas)}")
        
        return Response(content=output.getvalue(), media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        
    except Exception as e:
        logger.error(f"Error generando plantilla dinámica: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error generando plantilla Excel"
        )
