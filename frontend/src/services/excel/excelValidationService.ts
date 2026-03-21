"""Servicio de validación de datos Excel."""

from typing import List, Dict, Any, Tuple, Optional


class ValidationError:
    """Representa un error de validación."""
    def __init__(self, row: int, field: str, message: str, value: Any = None):
        self.row = row
        self.field = field
        self.message = message
        self.value = value
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'row': self.row,
            'field': self.field,
            'message': self.message,
            'value': self.value,
        }


class ExcelValidationService:
    """Servicio para validar datos de Excel."""
    
    @staticmethod
    def validar_campos_requeridos(
        data: List[Dict[str, Any]], 
        campos_requeridos: List[str]
    ) -> List[ValidationError]:
        """Valida que todos los campos requeridos estén presentes."""
        errores = []
        
        for row_idx, row in enumerate(data, start=2):  # Empezar en 2 (header es fila 1)
            for campo in campos_requeridos:
                if campo not in row or row[campo] is None or row[campo] == '':
                    errores.append(ValidationError(
                        row=row_idx,
                        field=campo,
                        message=f"Campo requerido"
                    ))
        
        return errores
    
    @staticmethod
    def validar_montos(data: List[Dict[str, Any]]) -> List[ValidationError]:
        """Valida que los montos sean válidos."""
        errores = []
        
        for row_idx, row in enumerate(data, start=2):
            if 'monto' not in row:
                continue
            
            monto = row['monto']
            
            try:
                monto_float = float(monto)
                if monto_float <= 0:
                    errores.append(ValidationError(
                        row=row_idx,
                        field='monto',
                        message='Monto debe ser mayor a 0',
                        value=monto
                    ))
            except (ValueError, TypeError):
                errores.append(ValidationError(
                    row=row_idx,
                    field='monto',
                    message='Monto debe ser un número válido',
                    value=monto
                ))
        
        return errores
    
    @staticmethod
    def validar_documentos_unicos(
        data: List[Dict[str, Any]]
    ) -> List[ValidationError]:
        """Valida que los documentos no se repitan en el archivo."""
        errores = []
        documentos_vistos = {}
        
        for row_idx, row in enumerate(data, start=2):
            if 'documento' not in row or not row['documento']:
                continue
            
            documento = str(row['documento']).strip()
            
            if documento in documentos_vistos:
                errores.append(ValidationError(
                    row=row_idx,
                    field='documento',
                    message=f"Documento duplicado (también en fila {documentos_vistos[documento]})",
                    value=documento
                ))
            else:
                documentos_vistos[documento] = row_idx
        
        return errores
    
    @staticmethod
    def validar_clientes(
        data: List[Dict[str, Any]], 
        clientes_validos: List[int]
    ) -> List[ValidationError]:
        """Valida que los IDs de cliente sean válidos."""
        errores = []
        clientes_set = set(clientes_validos)
        
        for row_idx, row in enumerate(data, start=2):
            if 'cliente_id' not in row:
                continue
            
            cliente_id = row['cliente_id']
            
            try:
                cliente_id_int = int(cliente_id)
                if cliente_id_int not in clientes_set:
                    errores.append(ValidationError(
                        row=row_idx,
                        field='cliente_id',
                        message=f"Cliente ID {cliente_id_int} no existe",
                        value=cliente_id
                    ))
            except (ValueError, TypeError):
                errores.append(ValidationError(
                    row=row_idx,
                    field='cliente_id',
                    message='Cliente ID debe ser un número',
                    value=cliente_id
                ))
        
        return errores
    
    @staticmethod
    def validar_datos_completos(
        data: List[Dict[str, Any]], 
        campos_requeridos: List[str] = None
    ) -> Tuple[bool, List[ValidationError]]:
        """
        Validación completa de los datos.
        
        Returns:
            (es_valido, lista_de_errores)
        """
        if campos_requeridos is None:
            campos_requeridos = ['cliente_id', 'monto']
        
        errores = []
        
        # Validar campos requeridos
        errores.extend(ExcelValidationService.validar_campos_requeridos(data, campos_requeridos))
        
        # Validar montos
        errores.extend(ExcelValidationService.validar_montos(data))
        
        # Validar documentos únicos
        errores.extend(ExcelValidationService.validar_documentos_unicos(data))
        
        es_valido = len(errores) == 0
        return es_valido, errores
    
    @staticmethod
    def generar_reporte_validacion(errores: List[ValidationError]) -> Dict[str, Any]:
        """Genera un reporte legible de validación."""
        if not errores:
            return {
                'valido': True,
                'total_errores': 0,
                'errores': []
            }
        
        # Agrupar por fila
        errores_por_fila = {}
        for error in errores:
            if error.row not in errores_por_fila:
                errores_por_fila[error.row] = []
            errores_por_fila[error.row].append(error.to_dict())
        
        return {
            'valido': False,
            'total_errores': len(errores),
            'errores_por_fila': errores_por_fila,
            'errores': [e.to_dict() for e in errores],
            'primeras_filas_con_error': sorted(errores_por_fila.keys())[:5]
        }
