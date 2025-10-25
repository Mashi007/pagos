# Funciones refactorizadas para carga masiva de clientes
from typing import Dict, List, Tuple
import pandas as pd
import io
from fastapi import HTTPException
from sqlalchemy.orm import Session
import logging

from app.schemas.carga_masiva import ErrorCargaMasiva, ResultadoCargaMasiva

logger = logging.getLogger(__name__)


def _obtener_mapeo_columnas() -> Dict[str, str]:
    """Obtener mapeo de columnas Excel a sistema"""
    return {
        "CEDULA IDENTIDAD": "cedula",
        "CEDULA IDENT": "cedula",
        "CEDULA": "cedula",
        "NOMBRE": "nombre",
        "APELLIDO": "apellido",
        "MOVIL": "movil",
        "TELEFONO": "movil",
        "CORREO ELECTRONICO": "email",
        "EMAIL": "email",
        "DIRECCION": "direccion",
        "MODELO VEHICULO": "modelo_vehiculo",
        "MODELO": "modelo_vehiculo",
        "CONCESIONARIO": "concesionario",
        "TOTAL FINANCIAMIENTO": "total_financiamiento",
        "MONTO FINANCIAMIENTO": "total_financiamiento",
        "CUOTA INICIAL": "cuota_inicial",
        "INICIAL": "cuota_inicial",
        "NUMERO AMORTIZACIONES": "numero_amortizaciones",
        "AMORTIZACIONES": "numero_amortizaciones",
        "CUOTAS": "numero_amortizaciones",
        "MODALIDAD PAGO": "modalidad_pago",
        "MODALIDAD": "modalidad_pago",
        "FECHA ENTREGA": "fecha_entrega",
        "ENTREGA": "fecha_entrega",
        "USER": "asesor",
        "USER ASIGNADO": "asesor",
    }


def _validar_columnas_requeridas(df: pd.DataFrame) -> None:
    """Validar que existan las columnas requeridas"""
    columnas_requeridas = ["cedula", "nombre"]
    columnas_faltantes = [col for col in columnas_requeridas if col not in df.columns]

    if columnas_faltantes:
        raise HTTPException(
            status_code=400,
            detail=f"❌ Faltan columnas requeridas: {', '.join(columnas_faltantes)}",
        )


def _extraer_datos_fila(row: pd.Series, fila_numero: int) -> Dict[str, str]:
    """Extraer y limpiar datos de una fila"""
    cedula = str(row.get("cedula", "")).strip()
    nombre = str(row.get("nombre", "")).strip()
    apellido = str(row.get("apellido", "")).strip() if "apellido" in row else ""
    movil = str(row.get("movil", "")).strip()
    email = str(row.get("email", "")).strip()
    direccion = str(row.get("direccion", "")).strip()
    modelo_vehiculo = str(row.get("modelo_vehiculo", "")).strip()
    concesionario = str(row.get("concesionario", "")).strip()
    total_financiamiento = str(row.get("total_financiamiento", "")).strip()
    cuota_inicial = str(row.get("cuota_inicial", "")).strip()
    numero_amortizaciones = str(row.get("numero_amortizaciones", "")).strip()
    modalidad_pago = str(row.get("modalidad_pago", "")).strip()
    fecha_entrega = str(row.get("fecha_entrega", "")).strip()
    asesor = str(row.get("asesor", "")).strip()

    # Si no hay apellido separado, intentar split del nombre
    if not apellido and nombre:
        partes_nombre = nombre.split(" ", 1)
        if len(partes_nombre) > 1:
            nombre = partes_nombre[0]
            apellido = partes_nombre[1]

    return {
        "cedula": cedula,
        "nombre": nombre,
        "apellido": apellido,
        "movil": movil,
        "email": email,
        "direccion": direccion,
        "modelo_vehiculo": modelo_vehiculo,
        "concesionario": concesionario,
        "total_financiamiento": total_financiamiento,
        "cuota_inicial": cuota_inicial,
        "numero_amortizaciones": numero_amortizaciones,
        "modalidad_pago": modalidad_pago,
        "fecha_entrega": fecha_entrega,
        "asesor": asesor,
        "fila_numero": fila_numero,
    }


def _validar_campos_criticos(datos: Dict[str, str]) -> Tuple[List[ErrorCargaMasiva], int]:
    """Validar campos críticos y generar errores"""
    errores = []
    errores_criticos = 0

    # Cédula (CRÍTICO)
    if not datos["cedula"] or datos["cedula"].upper() == "ERROR":
        errores.append(
            ErrorCargaMasiva(
                fila=datos["fila_numero"],
                cedula=datos["cedula"] or "VACÍO",
                campo="cedula",
                valor_original=datos["cedula"],
                error="Cédula vacía o marcada como ERROR",
                tipo_error="CRITICO",
                puede_corregirse=True,
                sugerencia="Ingrese cédula válida (ej: V12345678)",
            )
        )
        errores_criticos += 1

    # Nombre (CRÍTICO)
    if not datos["nombre"] or datos["nombre"].upper() == "ERROR":
        errores.append(
            ErrorCargaMasiva(
                fila=datos["fila_numero"],
                cedula=datos["cedula"] or "VACÍO",
                campo="nombre",
                valor_original=datos["nombre"],
                error="Nombre vacío o marcado como ERROR",
                tipo_error="CRITICO",
                puede_corregirse=True,
                sugerencia="Ingrese nombre completo del cliente",
            )
        )
        errores_criticos += 1

    # Total Financiamiento (CRÍTICO si se quiere financiamiento)
    if not datos["total_financiamiento"] or datos["total_financiamiento"].upper() == "ERROR":
        errores.append(
            ErrorCargaMasiva(
                fila=datos["fila_numero"],
                cedula=datos["cedula"],
                campo="total_financiamiento",
                valor_original=datos["total_financiamiento"],
                error="Total financiamiento vacío o marcado como ERROR",
                tipo_error="CRITICO",
                puede_corregirse=True,
                sugerencia="Ingrese monto válido (ej: 5000000)",
            )
        )
        errores_criticos += 1

    return errores, errores_criticos


async def _analizar_archivo_clientes_refactored(
    contenido: bytes, nombre_archivo: str, db: Session, usuario_id: int
) -> ResultadoCargaMasiva:
    """
    Analizar archivo de clientes sin guardar (VERSIÓN REFACTORIZADA)
    Detectar TODOS los errores y clasificarlos
    """
    try:
        # Leer Excel
        df = pd.read_excel(io.BytesIO(contenido))

        # Mapear columnas y validar estructura
        mapeo_columnas = _obtener_mapeo_columnas()
        df = df.rename(columns=mapeo_columnas)
        _validar_columnas_requeridas(df)

        # Procesar cada registro
        registros_procesados = []
        total_registros = len(df)
        registros_con_errores = 0
        errores_criticos = 0
        errores_advertencia = 0
        datos_vacios = 0
        todos_los_errores = []

        for index, row in df.iterrows():
            fila_numero = index + 2  # +2 porque Excel empieza en 1 y tiene header

            # Extraer datos de la fila
            datos = _extraer_datos_fila(row, fila_numero)

            # Validar campos críticos
            errores_registro, criticos = _validar_campos_criticos(datos)
            errores_criticos += criticos

            # TODO: Agregar más validaciones aquí...
            # - Validación de formato de cédula
            # - Validación de email
            # - Validación de teléfono
            # - Validación de montos
            # - Validación de fechas

            if errores_registro:
                registros_con_errores += 1
                todos_los_errores.extend(errores_registro)
            else:
                registros_procesados.append(datos)

        return ResultadoCargaMasiva(
            archivo=nombre_archivo,
            total_registros=total_registros,
            registros_procesados=len(registros_procesados),
            registros_con_errores=registros_con_errores,
            errores_criticos=errores_criticos,
            errores_advertencia=errores_advertencia,
            datos_vacios=datos_vacios,
            tasa_exito=round(len(registros_procesados) / total_registros * 100, 1) if total_registros > 0 else 0,
            errores_detallados=todos_los_errores,
            registros_validos=registros_procesados,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analizando archivo de clientes: {e}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")
