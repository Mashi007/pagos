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
from app.models.cliente import Cliente
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
        
        # KPIS DE ACTUALIZACIÓN AUTOMÁTICA
        total_clientes = db.query(Cliente).count()
        clientes_activos = db.query(Cliente).filter(Cliente.activo == True).count()
        logger.info(f"KPIs - Total clientes: {total_clientes}, Activos: {clientes_activos}")
        
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
            ["   - cedula: Cedula unica (V/E/J + 7-10 digitos)"],
            ["   - nombres: Nombres completos"],
            ["   - apellidos: Apellidos completos"],
            ["   - modelo_vehiculo: Modelo del vehiculo (lista desplegable)"],
            ["   - concesionario: Concesionario (lista desplegable)"],
            ["   - analista: Analista asignado (lista desplegable)"],
            ["   - total_financiamiento: Monto total del financiamiento"],
            ["   - numero_amortizaciones: Numero de cuotas (1-60)"],
            ["   - modalidad_pago: SEMANAL/QUINCENAL/MENSUAL"],
            ["   - fecha_entrega: Fecha de entrega del vehiculo"],
            [""],
            ["3. CAMPOS OPCIONALES:"],
            ["   - telefono: Numero de telefono"],
            ["   - email: Correo electronico valido"],
            ["   - direccion: Direccion completa"],
            ["   - fecha_nacimiento: Formato YYYY-MM-DD"],
            ["   - ocupacion: Ocupacion del cliente"],
            ["   - cuota_inicial: Cuota inicial"],
            ["   - estado: ACTIVO o INACTIVO"],
            ["   - activo: true o false"],
            ["   - notas: Observaciones adicionales"],
            [""],
            ["5. VALIDACIONES:"],
            ["   - Cedula debe ser unica en el sistema"],
            ["   - Email debe tener formato valido"],
            ["   - Fecha de nacimiento en formato YYYY-MM-DD"],
            ["   - Estado debe ser ACTIVO o INACTIVO"],
            ["   - Usar solo valores de las listas desplegables"],
            [""],
            ["4. EJEMPLOS DE DATOS VALIDOS:"],
            ["   - cedula: 'V12345678'"],
            ["   - nombres: 'Juan Carlos'"],
            ["   - apellidos: 'Perez Garcia'"],
            ["   - telefono: '0987654321'"],
            ["   - email: 'juan.perez@email.com'"],
            ["   - direccion: 'Av. Principal 123, Quito'"],
            ["   - fecha_nacimiento: '1990-05-15'"],
            ["   - ocupacion: 'Ingeniero'"],
            ["   - modelo_vehiculo: 'Toyota Corolla 2023'"],
            ["   - concesionario: 'AutoMax Quito'"],
            ["   - analista: 'Maria Gonzalez'"],
            ["   - total_financiamiento: '25000'"],
            ["   - cuota_inicial: '5000'"],
            ["   - numero_amortizaciones: '12'"],
            ["   - modalidad_pago: 'QUINCENAL'"],
            ["   - fecha_entrega: '2024-12-31'"],
            ["   - estado: 'ACTIVO'"],
            ["   - activo: 'true'"],
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
        
        # Encabezados completos - COMPATIBLES CON FORMULARIO WEB
        encabezados = [
            # Datos personales (coincide con formulario)
            "cedula", "nombres", "apellidos", "telefono", "email",
            "direccion", "fecha_nacimiento", "ocupacion",
            
            # Datos del vehículo (coincide con formulario)
            "modelo_vehiculo", "concesionario", "analista",
            
            # Datos del financiamiento (coincide con formulario)
            "total_financiamiento", "cuota_inicial", "numero_amortizaciones",
            "modalidad_pago", "fecha_entrega",
            
            # Estado y control (coincide con BD)
            "estado", "activo", "notas"
        ]
        
        for i, encabezado in enumerate(encabezados, 1):
            ws_plantilla.cell(row=1, column=i, value=encabezado)
        
        # Ejemplo de datos completos - COMPATIBLES CON FORMULARIO WEB
        ejemplo = [
            # Datos personales
            "V12345678", "Juan Carlos", "Perez Garcia", "0987654321",
            "juan.perez@email.com", "Av. Principal 123, Quito", "1990-05-15", "Ingeniero",
            
            # Datos del vehículo
            modelos_vehiculos[0] if modelos_vehiculos else "Toyota Corolla 2023",
            concesionarios[0] if concesionarios else "AutoMax Quito",
            analistas[0] if analistas else "Maria Gonzalez",
            
            # Datos del financiamiento
            "25000", "5000", "12", "QUINCENAL", "2024-12-31",
            
            # Estado y control
            "ACTIVO", "true", "Cliente preferencial"
        ]
        
        for i, valor in enumerate(ejemplo, 1):
            ws_plantilla.cell(row=2, column=i, value=valor)
        
        # CONFIGURAR LISTAS DESPLEGABLES CON DATOS REALES - COMPATIBLES CON FORMULARIO
        
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
        
        # Lista desplegable para modalidad_pago (columna N)
        dv_modalidad = DataValidation(type="list", formula1='"SEMANAL,QUINCENAL,MENSUAL"', allow_blank=True)
        dv_modalidad.add(f'N2:N1000')
        ws_plantilla.add_data_validation(dv_modalidad)
        
        # Lista desplegable para estado (columna P)
        dv_estado = DataValidation(type="list", formula1='"ACTIVO,INACTIVO"', allow_blank=True)
        dv_estado.add(f'P2:P1000')
        ws_plantilla.add_data_validation(dv_estado)
        
        # Lista desplegable para activo (columna Q)
        dv_activo = DataValidation(type="list", formula1='"true,false"', allow_blank=True)
        dv_activo.add(f'Q2:Q1000')
        ws_plantilla.add_data_validation(dv_activo)
        
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
