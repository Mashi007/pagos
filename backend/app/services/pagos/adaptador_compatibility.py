"""
Compatibilidad con codigo que aun instancia PagosService.

- Lectura/validacion: alineado al modelo real `Pago` (prestamo_id, monto_pagado, numero_documento, etc.).
- Alta de pagos: no usar `PagosService.crear_pago`; lanza PagoValidationError pidiendo POST /pagos o cobros/import.
"""

from typing import Callable, Any, Optional
from functools import wraps
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.services.pagos import PagosService
from app.services.pagos.pagos_excepciones import (
    PagoNotFoundError,
    PagoValidationError,
    PagoConflictError,
    ClienteNotFoundError,
    CuentaNotFoundError,
    PrestamoNotFoundError,
)


def con_manejo_errores_pagos(func: Callable) -> Callable:
    """
    Decorador que envuelve funciones de endpoints para manejar excepciones de servicios.
    Convierte excepciones de servicios en respuestas HTTP apropiadas.
    
    Uso:
        @con_manejo_errores_pagos
        def mi_endpoint(db: Session = Depends(get_db)):
            # ... código endpoint ...
            pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except PagoNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ClienteNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except CuentaNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except PrestamoNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except PagoValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except PagoConflictError as e:
            raise HTTPException(status_code=409, detail=str(e))
        except Exception as e:
            # Log del error real
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error inesperado en endpoint: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Error interno del servidor")
    
    return wrapper


def obtener_servicio_pagos(db: Session) -> PagosService:
    """
    Factory function para obtener una instancia del servicio de pagos.
    
    Uso en endpoints:
        @router.get("/pagos/{pago_id}")
        def get_pago(pago_id: int, db: Session = Depends(get_db)):
            service = obtener_servicio_pagos(db)
            pago = service.obtener_pago(pago_id)
            return pago
    """
    return PagosService(db)


class AdaptadorPagosLegacy:
    """
    Adaptador que proporciona funciones compatibles con la interfaz existente
    pero que usan internamente los nuevos servicios.
    
    Esto permite refactorizar gradualmente sin romper funcionalidades existentes.
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.service = PagosService(db)
    
    def crear_pago_validado(self, datos: dict) -> dict:
        """
        Crea un pago con validaciones completas.
        Interfaz compatible con código legado.
        
        Retorna: Dict serializable para response JSON
        """
        try:
            pago = self.service.crear_pago(datos)
            return self._serializar_pago(pago)
        except Exception as e:
            return {'error': str(e), 'success': False}
    
    def obtener_pago_seguro(self, pago_id: int) -> Optional[dict]:
        """
        Obtiene un pago de forma segura (sin lanzar excepción si no existe).
        
        Retorna: Dict del pago o None
        """
        try:
            pago = self.service.obtener_pago(pago_id)
            return self._serializar_pago(pago)
        except PagoNotFoundError:
            return None
    
    def validar_datos_antes_crear(self, datos: dict) -> tuple[bool, Optional[str]]:
        """
        Valida datos antes de crear un pago.
        
        Retorna: (es_valido, mensaje_error_si_aplica)
        """
        try:
            self.service.validacion.validar_datos_pago_completos(datos)
            
            if 'cliente_id' in datos:
                self.service.validacion.validar_cliente_existe(datos['cliente_id'])
            
            if 'monto' in datos:
                self.service.validacion.validar_monto_numerico(datos['monto'])
            
            if 'documento' in datos and datos['documento']:
                self.service.validacion.validar_documento_no_duplicado(datos['documento'])
            
            if 'estado' in datos:
                self.service.validacion.validar_estado_pago(datos['estado'])
            
            return True, None
        except Exception as e:
            return False, str(e)
    
    def calcular_monto_dolares(self, monto_pesos: float, tasa: Optional[float] = None) -> float:
        """Calcula monto en dólares."""
        return self.service.calculo.convertir_pesos_a_dolares(monto_pesos, tasa)
    
    def calcular_interes_atraso(self, monto: float, dias: int, tasa: float = 0.001) -> float:
        """Calcula intereses por atraso."""
        return self.service.calculo.calcular_interes(monto, dias, tasa)
    
    def obtener_resumen_cliente(self, cliente_id: int) -> dict:
        """Obtiene resumen de pagos de un cliente."""
        return self.service.obtener_resumen_pagos(cliente_id)
    
    def _serializar_pago(self, pago) -> dict:
        """Convierte modelo `Pago` (tabla pagos) a dict para JSON."""
        fp = getattr(pago, "fecha_pago", None)
        mp = getattr(pago, "monto_pagado", None)
        return {
            "id": pago.id,
            "prestamo_id": getattr(pago, "prestamo_id", None),
            "cedula_cliente": getattr(pago, "cedula_cliente", None),
            "monto_pagado": float(mp) if mp is not None else None,
            "estado": getattr(pago, "estado", None),
            "numero_documento": getattr(pago, "numero_documento", None),
            "referencia_pago": getattr(pago, "referencia_pago", None),
            "fecha_pago": fp.isoformat() if fp is not None else None,
        }


# Funciones auxiliares para mantener compatibilidad con patrones existentes

def validar_pago_existente(db: Session, pago_id: int) -> Any:
    """
    Valida que un pago existe (para usar en Depends si es necesario).
    Lanza HTTPException si no existe.
    """
    service = obtener_servicio_pagos(db)
    try:
        return service.obtener_pago(pago_id)
    except PagoNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


def validar_cliente_existe_endpoint(db: Session, cliente_id: int) -> Any:
    """Valida que un cliente existe para usar en endpoints."""
    service = obtener_servicio_pagos(db)
    try:
        return service.validacion.validar_cliente_existe(cliente_id)
    except ClienteNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
