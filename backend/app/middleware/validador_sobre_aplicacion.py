# -*- coding: utf-8 -*-
"""
Middleware de validación en tiempo real para evitar sobre-aplicaciones.
Intercepta requests que intenten aplicar pagos y valida antes de ejecutar.
"""
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from decimal import Decimal
from sqlalchemy.orm import Session
import logging
import json

from app.core.database import SessionLocal
from app.models.cuota import Cuota
from app.models.cuota_pago import CuotaPago
from app.services.conciliacion_automatica_service import ValidadorSobreAplicacion

logger = logging.getLogger(__name__)


class ValidadorSobreAplicacionMiddleware(BaseHTTPMiddleware):
    """
    Middleware que intercepta requests de aplicación de pagos y valida
    en tiempo real para evitar sobre-aplicaciones.
    """
    
    async def dispatch(self, request: Request, call_next):
        # Solo validar requests POST/PUT a endpoints de aplicación de pagos
        if request.method in ['POST', 'PUT'] and '/aplicar-cuota' in request.url.path:
            db = SessionLocal()
            try:
                body = await request.body()
                if body:
                    try:
                        data = json.loads(body)
                        cuota_id = data.get('cuota_id')
                        monto_a_aplicar = data.get('monto_aplicado')
                        
                        if cuota_id and monto_a_aplicar:
                            cuota = db.query(Cuota).filter(Cuota.id == cuota_id).first()
                            if not cuota:
                                return JSONResponse(
                                    status_code=404,
                                    content={'detail': f'Cuota {cuota_id} no encontrada'}
                                )
                            
                            es_valido, errores = ValidadorSobreAplicacion.validar_aplicacion(
                                db, cuota, Decimal(str(monto_a_aplicar))
                            )
                            
                            if not es_valido:
                                logger.warning(
                                    f'Validación fallida para cuota {cuota_id}: {errores}'
                                )
                                return JSONResponse(
                                    status_code=422,
                                    content={
                                        'detail': 'Validación fallida',
                                        'errores': errores
                                    }
                                )
                    except json.JSONDecodeError:
                        pass
            except Exception as e:
                logger.warning(f'Error en validación middleware: {e}')
            finally:
                db.close()
        
        response = await call_next(request)
        return response
