"""Servicio de parseo de archivos Excel."""

from typing import List, Dict, Any, Optional, Tuple
from enum import Enum


class ExcelParsingError(Exception):
    """Error en el parseo de Excel."""
    pass


class ExcelFormat(Enum):
    """Formatos de Excel soportados."""
    XLSX = "xlsx"
    XLS = "xls"
    CSV = "csv"


class ExcelParsingService:
    """Servicio para parsear archivos Excel."""
    
    SUPPORTED_FORMATS = {'.xlsx', '.xls', '.csv'}
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
    
    @staticmethod
    def validar_archivo(file_path: str, file_size: int) -> Tuple[bool, Optional[str]]:
        """
        Valida que el archivo sea un Excel válido.
        
        Returns:
            (es_valido, mensaje_error_si_aplica)
        """
        # Validar extensión
        if not any(file_path.lower().endswith(fmt) for fmt in ExcelParsingService.SUPPORTED_FORMATS):
            return False, f"Formato no soportado. Use: {', '.join(ExcelParsingService.SUPPORTED_FORMATS)}"
        
        # Validar tamaño
        if file_size > ExcelParsingService.MAX_FILE_SIZE:
            return False, f"Archivo muy grande. Máximo: {ExcelParsingService.MAX_FILE_SIZE / 1024 / 1024:.0f} MB"
        
        if file_size == 0:
            return False, "Archivo vacío"
        
        return True, None
    
    @staticmethod
    def obtener_formato(file_path: str) -> Optional[ExcelFormat]:
        """Obtiene el formato del archivo."""
        for fmt in ExcelFormat:
            if file_path.lower().endswith(f'.{fmt.value}'):
                return fmt
        return None
    
    @staticmethod
    def extraer_headers(data: List[Dict[str, Any]]) -> List[str]:
        """Extrae headers (nombres de columnas) del archivo."""
        if not data or len(data) == 0:
            return []
        
        # Obtener las claves del primer registro
        return list(data[0].keys())
    
    @staticmethod
    def normalizar_headers(headers: List[str]) -> Dict[str, str]:
        """
        Normaliza nombres de columnas.
        
        Mapea variantes comunes a nombres canónicos.
        Ej: "Cliente ID", "cliente_id", "ClienteID" → "cliente_id"
        """
        mapeos = {
            'cliente_id': ['cliente id', 'cliente_id', 'clienteid', 'id cliente', 'cliente'],
            'monto': ['monto', 'cantidad', 'importe', 'amount'],
            'documento': ['documento', 'doc', 'nº documento', 'numero documento'],
            'referencia': ['referencia', 'ref', 'referencia pago'],
            'cuenta_id': ['cuenta_id', 'cuenta', 'accountid'],
            'fecha_pago': ['fecha pago', 'fecha', 'date'],
        }
        
        # Crear mapeo inverso: original → normalizado
        mapping = {}
        for canonical, variants in mapeos.items():
            for variant in variants:
                mapping[variant.lower()] = canonical
        
        # Mapear headers encontrados
        header_mapping = {}
        for header in headers:
            header_lower = header.lower().strip()
            header_mapping[header] = mapping.get(header_lower, header)
        
        return header_mapping
    
    @staticmethod
    def renombrar_columnas(data: List[Dict[str, Any]], mapping: Dict[str, str]) -> List[Dict[str, Any]]:
        """Renombra columnas según el mapeo."""
        resultado = []
        for row in data:
            new_row = {}
            for old_key, value in row.items():
                new_key = mapping.get(old_key, old_key)
                new_row[new_key] = value
            resultado.append(new_row)
        return resultado
    
    @staticmethod
    def limpiar_valores(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Limpia espacios en blanco de valores string."""
        resultado = []
        for row in data:
            new_row = {}
            for key, value in row.items():
                if isinstance(value, str):
                    new_row[key] = value.strip()
                else:
                    new_row[key] = value
            resultado.append(new_row)
        return resultado
    
    @staticmethod
    def remover_filas_vacias(data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remueve filas donde todos los valores son None o vacío."""
        resultado = []
        for row in data:
            # Verificar si la fila tiene al menos un valor no vacío
            tiene_valor = any(
                v is not None and v != '' and str(v).strip() != ''
                for v in row.values()
            )
            if tiene_valor:
                resultado.append(row)
        return resultado
