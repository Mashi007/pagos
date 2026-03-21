"""
Adaptador de compatibilidad para endpoints.

Este módulo proporciona funciones de compatibilidad que permiten que los endpoints
existentes continúen funcionando sin cambios mientras se utiliza la
nueva arquitectura de servicios bajo el capó.

IMPORTANTE: Esto es una capa de compatibilidad TEMPORAL.
En sprints futuros, los endpoints serán refactorizados para usar directamente los servicios.
"""

from typing import Callable, Any, Optional
from functools import wraps
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.services.prestamos import (
    PrestamosService,
    PrestamoNotFoundError,
    PrestamoValidationError,
    PrestamoConflictError,
    PrestamoStateError,
    ClienteNotFoundError,
    ClienteConErrorError,
    AmortizacionCalculoError,
)


def con_manejo_errores_prestamos(func: Callable) -> Callable:
    """
    Decorador que envuelve funciones de endpoints para manejar excepciones de servicios.
    Convierte excepciones de servicios en respuestas HTTP apropiadas.

    Uso:
        @con_manejo_errores_prestamos
        def mi_endpoint(db: Session = Depends(get_db)):
            # ... código endpoint ...
            pass
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except PrestamoNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ClienteNotFoundError as e:
            raise HTTPException(status_code=404, detail=str(e))
        except ClienteConErrorError as e:
            raise HTTPException(status_code=409, detail=str(e))
        except PrestamoValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except PrestamoConflictError as e:
            raise HTTPException(status_code=409, detail=str(e))
        except PrestamoStateError as e:
            raise HTTPException(status_code=409, detail=str(e))
        except AmortizacionCalculoError as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            # Log del error real
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error inesperado en endpoint: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail="Error interno del servidor")

    return wrapper


def obtener_servicio_prestamos(db: Session) -> PrestamosService:
    """
    Factory function para obtener una instancia del servicio de préstamos.

    Uso en endpoints:
        @router.get("/prestamos/{prestamo_id}")
        def get_prestamo(prestamo_id: int, db: Session = Depends(get_db)):
            service = obtener_servicio_prestamos(db)
            prestamo = service.obtener_prestamo(prestamo_id)
            return prestamo
    """
    return PrestamosService(db)


class AdaptadorPrestamosLegacy:
    """
    Adaptador que proporciona funciones compatibles con la interfaz existente
    pero que usan internamente los nuevos servicios.

    Esto permite refactorizar gradualmente sin romper funcionalidades existentes.
    """

    def __init__(self, db: Session):
        self.db = db
        self.service = PrestamosService(db)

    def crear_prestamo_validado(self, datos: dict) -> dict:
        """
        Crea un préstamo con validaciones completas.
        Interfaz compatible con código legado.

        Retorna: Dict serializable para response JSON
        """
        try:
            prestamo = self.service.crear_prestamo(datos)
            return self._serializar_prestamo(prestamo)
        except Exception as e:
            return {'error': str(e), 'success': False}

    def obtener_prestamo_seguro(self, prestamo_id: int) -> Optional[dict]:
        """
        Obtiene un préstamo de forma segura (sin lanzar excepción si no existe).

        Retorna: Dict del préstamo o None
        """
        try:
            prestamo = self.service.obtener_prestamo(prestamo_id)
            return self._serializar_prestamo(prestamo)
        except PrestamoNotFoundError:
            return None

    def validar_datos_antes_crear(self, datos: dict) -> tuple[bool, Optional[str]]:
        """
        Valida datos antes de crear un préstamo.

        Retorna: (es_valido, mensaje_error_si_aplica)
        """
        try:
            self.service.validacion.validar_datos_prestamo_completos(datos)

            if 'cliente_id' in datos:
                self.service.validacion.validar_cliente_existe(datos['cliente_id'])
                self.service.validacion.validar_cliente_sin_errores(datos['cliente_id'])

            if 'total_financiamiento' in datos:
                self.service.validacion.validar_monto_numerico(
                    datos['total_financiamiento']
                )

            if 'numero_cuotas' in datos:
                self.service.validacion.validar_numero_cuotas(
                    datos['numero_cuotas']
                )

            if 'tasa_interes' in datos and datos['tasa_interes']:
                self.service.validacion.validar_tasa_interes(
                    datos['tasa_interes']
                )

            if 'modalidad_pago' in datos:
                self.service.validacion.validar_modalidad_pago(
                    datos['modalidad_pago']
                )

            if 'estado' in datos:
                self.service.validacion.validar_estado_prestamo(datos['estado'])

            return True, None
        except Exception as e:
            return False, str(e)

    def cambiar_estado_prestamo_seguro(
        self,
        prestamo_id: int,
        nuevo_estado: str,
        usuario_cambio: Optional[str] = None
    ) -> tuple[bool, Optional[str]]:
        """
        Cambia estado de forma segura, retornando estado sin lanzar excepciones.

        Retorna: (éxito, mensaje_error_si_aplica)
        """
        try:
            self.service.cambiar_estado_prestamo(
                prestamo_id,
                nuevo_estado,
                usuario_cambio
            )
            return True, None
        except Exception as e:
            return False, str(e)

    def obtener_tabla_amortizacion_segura(
        self,
        prestamo_id: int
    ) -> Optional[list]:
        """Obtiene tabla de amortización sin lanzar excepciones."""
        try:
            return self.service.obtener_tabla_amortizacion(prestamo_id)
        except Exception:
            return None

    def generar_tabla_amortizacion_segura(
        self,
        prestamo_id: int,
        regenerar: bool = False
    ) -> tuple[bool, Optional[list]]:
        """Genera tabla de amortización sin lanzar excepciones."""
        try:
            tabla = self.service.generar_tabla_amortizacion(
                prestamo_id,
                regenerar=regenerar
            )
            return True, tabla
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error generando amortización: {str(e)}")
            return False, None

    def calcular_cuota_fija(
        self,
        principal: float,
        tasa_anual: float,
        numero_cuotas: int,
        modalidad: str = 'MENSUAL'
    ) -> Optional[float]:
        """Calcula cuota fija."""
        try:
            return self.service.calculo.calcular_cuota_fija(
                principal,
                tasa_anual,
                numero_cuotas,
                modalidad
            )
        except Exception:
            return None

    def obtener_resumen_prestamo(self, prestamo_id: int) -> Optional[dict]:
        """Obtiene resumen del préstamo."""
        try:
            return self.service.obtener_resumen_prestamo(prestamo_id)
        except Exception:
            return None

    def obtener_prestamos_cliente(
        self,
        cliente_id: int,
        limit: int = 100
    ) -> list:
        """Obtiene préstamos de un cliente."""
        try:
            prestamos = self.service.obtener_prestamos_cliente(cliente_id, limit)
            return [self._serializar_prestamo(p) for p in prestamos]
        except Exception:
            return []

    def registrar_pago_cuota_seguro(
        self,
        cuota_id: int,
        monto_pagado: float
    ) -> tuple[bool, Optional[str]]:
        """Registra pago de cuota de forma segura."""
        try:
            self.service.registrar_pago_cuota(cuota_id, monto_pagado)
            return True, None
        except Exception as e:
            return False, str(e)

    def _serializar_prestamo(self, prestamo) -> dict:
        """Convierte modelo de préstamo a dict para JSON."""
        return {
            'id': prestamo.id,
            'cliente_id': prestamo.cliente_id,
            'cedula': prestamo.cedula,
            'nombres': prestamo.nombres,
            'total_financiamiento': float(prestamo.total_financiamiento),
            'tasa_interes': float(prestamo.tasa_interes),
            'numero_cuotas': prestamo.numero_cuotas,
            'cuota_periodo': float(prestamo.cuota_periodo),
            'modalidad_pago': prestamo.modalidad_pago,
            'estado': prestamo.estado,
            'producto': prestamo.producto,
            'fecha_requerimiento': (
                prestamo.fecha_requerimiento.isoformat()
                if hasattr(prestamo.fecha_requerimiento, 'isoformat')
                else str(prestamo.fecha_requerimiento)
            ),
            'fecha_aprobacion': (
                prestamo.fecha_aprobacion.isoformat()
                if prestamo.fecha_aprobacion
                else None
            ),
            'usuario_proponente': prestamo.usuario_proponente,
            'usuario_aprobador': prestamo.usuario_aprobador,
            'analista': prestamo.analista,
            'modelo_vehiculo': prestamo.modelo_vehiculo,
            'valor_activo': float(prestamo.valor_activo) if prestamo.valor_activo else None,
        }


# Funciones auxiliares para mantener compatibilidad

def validar_prestamo_existente(db: Session, prestamo_id: int) -> Any:
    """
    Valida que un préstamo existe (para usar en Depends si es necesario).
    Lanza HTTPException si no existe.
    """
    service = obtener_servicio_prestamos(db)
    try:
        return service.obtener_prestamo(prestamo_id)
    except PrestamoNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


def validar_cliente_existe_endpoint(db: Session, cliente_id: int) -> Any:
    """Valida que un cliente existe para usar en endpoints."""
    service = obtener_servicio_prestamos(db)
    try:
        return service.validacion.validar_cliente_existe(cliente_id)
    except ClienteNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
