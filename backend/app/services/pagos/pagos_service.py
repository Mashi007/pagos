"""Servicio principal para gestión de pagos."""

from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, select

from app.models.pago import Pago
from app.models.cliente import Cliente
from app.core.documento import normalize_documento
from .pagos_validacion import PagosValidacion
from .pagos_calculo import PagosCalculo
from .pagos_excepciones import PagoNotFoundError


class PagosService:
    """
    Servicio principal para gestión de pagos.
    Encapsula lógica de negocio, validación y cálculos.
    """

    def __init__(self, db: Session):
        self.db = db
        self.validacion = PagosValidacion(db)
        self.calculo = PagosCalculo(db)

    def crear_pago(self, datos_pago: dict) -> Pago:
        """
        Crea un nuevo pago con validaciones completas.
        
        Args:
            datos_pago: Dict con datos del pago {
                'cliente_id': int,
                'monto': float,
                'documento': str (opcional),
                'referencia': str (opcional),
                'estado': str (default: 'pendiente'),
                ...otros campos
            }
        
        Returns:
            Objeto Pago creado y guardado
        """
        # Validaciones
        self.validacion.validar_datos_pago_completos(datos_pago)
        
        # Validar cliente existe
        cliente = self.validacion.validar_cliente_existe(datos_pago['cliente_id'])
        
        # Validar monto
        monto = self.validacion.validar_monto_numerico(datos_pago['monto'])
        
        # Validar documento no duplicado
        if 'documento' in datos_pago and datos_pago['documento']:
            self.validacion.validar_documento_no_duplicado(datos_pago['documento'])
        
        # Validar estado si se proporciona
        if 'estado' in datos_pago:
            self.validacion.validar_estado_pago(datos_pago['estado'])
        
        # Calcular monto en dólares
        monto_dolares = self.calculo.convertir_pesos_a_dolares(monto)
        
        # Crear objeto Pago
        nuevo_pago = Pago(
            cliente_id=datos_pago['cliente_id'],
            monto=monto,
            monto_dolares=monto_dolares,
            estado=datos_pago.get('estado', 'pendiente'),
            documento=datos_pago.get('documento', '').strip() or None,
            documento_normalizado=normalize_documento(datos_pago.get('documento', '')),
            referencia_pago=datos_pago.get('referencia', ''),
            fecha_pago=datos_pago.get('fecha_pago', datetime.now()),
        )
        
        # Agregar campos adicionales si existen
        for campo in ['cuenta_id', 'observaciones', 'metodo_pago']:
            if campo in datos_pago:
                setattr(nuevo_pago, campo, datos_pago[campo])
        
        self.db.add(nuevo_pago)
        self.db.commit()
        self.db.refresh(nuevo_pago)
        
        return nuevo_pago

    def obtener_pago(self, pago_id: int) -> Pago:
        """Obtiene un pago por ID."""
        pago = self.db.query(Pago).filter(Pago.id == pago_id).first()
        if not pago:
            raise PagoNotFoundError(pago_id)
        return pago

    def obtener_pagos_cliente(self, cliente_id: int, limit: int = 100) -> List[Pago]:
        """Obtiene todos los pagos de un cliente."""
        self.validacion.validar_cliente_existe(cliente_id)
        
        pagos = self.db.query(Pago)\
            .filter(Pago.cliente_id == cliente_id)\
            .order_by(desc(Pago.fecha_pago))\
            .limit(limit)\
            .all()
        
        return pagos

    def actualizar_estado_pago(self, pago_id: int, nuevo_estado: str) -> Pago:
        """Actualiza el estado de un pago."""
        pago = self.obtener_pago(pago_id)
        
        # Validar nuevo estado
        self.validacion.validar_estado_pago(nuevo_estado)
        
        pago.estado = nuevo_estado
        pago.fecha_actualizacion = datetime.now()
        
        self.db.commit()
        self.db.refresh(pago)
        
        return pago

    def actualizar_pago(self, pago_id: int, datos_actualizacion: dict) -> Pago:
        """
        Actualiza campos de un pago.
        
        Args:
            pago_id: ID del pago a actualizar
            datos_actualizacion: Dict con campos a actualizar
        """
        pago = self.obtener_pago(pago_id)
        
        # Validar documento no duplicado (si se actualiza)
        if 'documento' in datos_actualizacion:
            self.validacion.validar_documento_no_duplicado(
                datos_actualizacion['documento'],
                excluir_pago_id=pago_id
            )
        
        # Actualizar campos permitidos
        campos_permitidos = [
            'monto', 'estado', 'documento', 'referencia_pago',
            'observaciones', 'metodo_pago', 'cuenta_id'
        ]
        
        for campo, valor in datos_actualizacion.items():
            if campo in campos_permitidos and valor is not None:
                if campo == 'monto':
                    valor = self.validacion.validar_monto_numerico(valor)
                    pago.monto_dolares = self.calculo.convertir_pesos_a_dolares(valor)
                elif campo == 'estado':
                    self.validacion.validar_estado_pago(valor)
                elif campo == 'documento':
                    pago.documento_normalizado = normalize_documento(valor)
                
                setattr(pago, campo, valor)
        
        pago.fecha_actualizacion = datetime.now()
        self.db.commit()
        self.db.refresh(pago)
        
        return pago

    def eliminar_pago(self, pago_id: int) -> bool:
        """Elimina un pago (soft delete recomendado)."""
        pago = self.obtener_pago(pago_id)
        self.db.delete(pago)
        self.db.commit()
        return True

    def obtener_resumen_pagos(self, cliente_id: Optional[int] = None) -> dict:
        """
        Obtiene resumen de pagos (total, promedio, por estado).
        
        Args:
            cliente_id: Si se proporciona, filtra por cliente
        """
        query = self.db.query(Pago)
        
        if cliente_id:
            self.validacion.validar_cliente_existe(cliente_id)
            query = query.filter(Pago.cliente_id == cliente_id)
        
        total_pagos = query.count()
        total_monto = self.db.query(func.sum(Pago.monto)).filter(
            Pago.cliente_id == cliente_id if cliente_id else True
        ).scalar() or 0
        
        monto_promedio = total_monto / total_pagos if total_pagos > 0 else 0
        
        # Agrupar por estado
        por_estado = self.db.query(
            Pago.estado,
            func.count(Pago.id),
            func.sum(Pago.monto)
        ).group_by(Pago.estado)
        
        if cliente_id:
            por_estado = por_estado.filter(Pago.cliente_id == cliente_id)
        
        estado_dict = {estado: {'cantidad': cant, 'total': total} 
                       for estado, cant, total in por_estado.all()}
        
        return {
            'total_pagos': total_pagos,
            'total_monto': float(total_monto or 0),
            'monto_promedio': float(monto_promedio),
            'por_estado': estado_dict,
        }

    def validar_integridad_pagos(self, cliente_id: int) -> dict:
        """
        Valida la integridad de pagos de un cliente.
        Retorna reporte de anomalías encontradas.
        """
        cliente = self.validacion.validar_cliente_existe(cliente_id)
        pagos = self.obtener_pagos_cliente(cliente_id, limit=1000)
        
        anomalias = []
        
        for pago in pagos:
            # Validar documento duplicado
            if pago.documento:
                duplicados = self.db.query(Pago).filter(
                    Pago.documento_normalizado == pago.documento_normalizado,
                    Pago.id != pago.id
                ).count()
                
                if duplicados > 0:
                    anomalias.append({
                        'tipo': 'documento_duplicado',
                        'pago_id': pago.id,
                        'documento': pago.documento,
                        'cantidad_duplicados': duplicados
                    })
            
            # Validar monto válido
            if not pago.monto or pago.monto <= 0:
                anomalias.append({
                    'tipo': 'monto_invalido',
                    'pago_id': pago.id,
                    'monto': pago.monto
                })
        
        return {
            'cliente_id': cliente_id,
            'total_pagos': len(pagos),
            'total_anomalias': len(anomalias),
            'anomalias': anomalias
        }
