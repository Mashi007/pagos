"""Servicio principal para gestión de préstamos."""

from typing import List, Optional, Dict
from datetime import date, datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, and_

from app.models.prestamo import Prestamo
from app.models.cliente import Cliente
from .prestamos_validacion import PrestamosValidacion
from .prestamos_calculo import PrestamosCalculo
from .amortizacion_service import AmortizacionService
from .prestamo_cedula_cliente_coherencia import (
    PrestamoCedulaClienteError,
    asegurar_prestamo_alineado_con_cliente,
)
from .prestamos_excepciones import (
    PrestamoNotFoundError,
    PrestamoValidationError,
    PrestamoStateError,
)


class PrestamosService:
    """
    Servicio principal para gestión de préstamos.
    Encapsula lógica de negocio, validación y cálculos.
    """

    def __init__(self, db: Session):
        self.db = db
        self.validacion = PrestamosValidacion(db)
        self.calculo = PrestamosCalculo(db)
        self.amortizacion = AmortizacionService(db)

    def crear_prestamo(self, datos_prestamo: dict) -> Prestamo:
        """
        Crea un nuevo préstamo con validaciones completas.

        Args:
            datos_prestamo: Dict con datos del préstamo

        Returns:
            Objeto Prestamo creado y guardado
        """
        # Validaciones
        self.validacion.validar_datos_prestamo_completos(datos_prestamo)

        # Validar cliente
        cliente = self.validacion.validar_cliente_existe(datos_prestamo['cliente_id'])
        self.validacion.validar_cliente_sin_errores(datos_prestamo['cliente_id'])

        # Validar datos numéricos
        total_financiamiento = self.validacion.validar_monto_numerico(
            datos_prestamo['total_financiamiento']
        )
        numero_cuotas = datos_prestamo['numero_cuotas']
        self.validacion.validar_numero_cuotas(numero_cuotas)

        cuota_periodo = self.validacion.validar_monto_numerico(
            datos_prestamo['cuota_periodo']
        )
        self.validacion.validar_cuota_periodo(
            cuota_periodo,
            total_financiamiento,
            numero_cuotas
        )

        # Validar tasa si se proporciona
        tasa_interes = float(datos_prestamo.get('tasa_interes', 0.0))
        if tasa_interes > 0:
            self.validacion.validar_tasa_interes(tasa_interes)

        # Validar modalidad
        modalidad = datos_prestamo.get('modalidad_pago', 'MENSUAL')
        self.validacion.validar_modalidad_pago(modalidad)

        # Validar cédula (coherencia con ficha cliente; la persistida en prestamo sale del cliente)
        self.validacion.validar_cedula_unica_por_cliente(
            datos_prestamo['cliente_id'],
            cliente.cedula or "",
        )

        # Validar fechas si se proporcionan
        if 'fecha_requerimiento' in datos_prestamo:
            self.validacion.validar_fecha(
                datos_prestamo['fecha_requerimiento'],
                'fecha_requerimiento'
            )

        if 'fecha_base_calculo' in datos_prestamo and datos_prestamo['fecha_base_calculo']:
            self.validacion.validar_fecha_base_calculo(
                datos_prestamo['fecha_base_calculo']
            )

        # Validar estado si se proporciona
        estado = datos_prestamo.get('estado', 'DRAFT')
        self.validacion.validar_estado_prestamo(estado)

        # Validar campos opcionales
        if 'observaciones' in datos_prestamo:
            self.validacion.validar_observaciones(datos_prestamo['observaciones'])

        if 'ml_impago_nivel_riesgo_manual' in datos_prestamo:
            self.validacion.validar_codigo_ml_riesgo(
                datos_prestamo['ml_impago_nivel_riesgo_manual']
            )

        if 'ml_impago_probabilidad_manual' in datos_prestamo:
            self.validacion.validar_probabilidad_ml(
                datos_prestamo['ml_impago_probabilidad_manual']
            )

        if 'valor_activo' in datos_prestamo:
            self.validacion.validar_valor_activo(datos_prestamo['valor_activo'])

        # Crear objeto Prestamo (cedula siempre alineada al cliente)
        nuevo_prestamo = Prestamo(
            cliente_id=datos_prestamo['cliente_id'],
            cedula=cliente.cedula or "",
            nombres=datos_prestamo['nombres'],
            total_financiamiento=total_financiamiento,
            fecha_requerimiento=datos_prestamo.get(
                'fecha_requerimiento',
                date.today()
            ),
            modalidad_pago=modalidad,
            numero_cuotas=numero_cuotas,
            cuota_periodo=cuota_periodo,
            tasa_interes=tasa_interes,
            fecha_base_calculo=datos_prestamo.get('fecha_base_calculo'),
            producto=datos_prestamo.get('producto', ''),
            estado=estado,
            usuario_proponente=datos_prestamo.get(
                'usuario_proponente',
                'itmaster@rapicreditca.com'
            ),
            usuario_aprobador=datos_prestamo.get('usuario_aprobador'),
            observaciones=datos_prestamo.get('observaciones', 'No observaciones'),
            analista=datos_prestamo.get('analista', ''),
            concesionario=datos_prestamo.get('concesionario'),
            modelo_vehiculo=datos_prestamo.get('modelo_vehiculo'),
            valor_activo=datos_prestamo.get('valor_activo'),
            ml_impago_nivel_riesgo_manual=datos_prestamo.get(
                'ml_impago_nivel_riesgo_manual'
            ),
            ml_impago_probabilidad_manual=datos_prestamo.get(
                'ml_impago_probabilidad_manual'
            ),
            usuario_autoriza=datos_prestamo.get(
                'usuario_autoriza',
                'operaciones@rapicreditca.com'
            ),
            informacion_desplegable=datos_prestamo.get(
                'informacion_desplegable',
                False
            ),
            requiere_revision=datos_prestamo.get('requiere_revision', False),
        )

        try:
            asegurar_prestamo_alineado_con_cliente(
                self.db,
                nuevo_prestamo,
                cliente=cliente,
                estado_para_validar=estado,
            )
        except PrestamoCedulaClienteError as e:
            raise PrestamoValidationError("cedula", str(e)) from e

        self.db.add(nuevo_prestamo)
        self.db.commit()
        self.db.refresh(nuevo_prestamo)

        # Generar tabla de amortización si el estado es APROBADO
        if estado == 'APROBADO':
            try:
                self.amortizacion.generar_tabla_amortizacion(
                    nuevo_prestamo.id,
                    fecha_inicio=datos_prestamo.get('fecha_base_calculo')
                )
            except Exception:
                # No fallar si no se puede generar la tabla
                pass

        return nuevo_prestamo

    def obtener_prestamo(self, prestamo_id: int) -> Prestamo:
        """Obtiene un préstamo por ID."""
        prestamo = self.db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
        if not prestamo:
            raise PrestamoNotFoundError(prestamo_id)
        return prestamo

    def obtener_prestamos_cliente(
        self,
        cliente_id: int,
        limit: int = 100,
        estado: Optional[str] = None
    ) -> List[Prestamo]:
        """Obtiene todos los préstamos de un cliente."""
        self.validacion.validar_cliente_existe(cliente_id)

        query = self.db.query(Prestamo)\
            .filter(Prestamo.cliente_id == cliente_id)\
            .order_by(desc(Prestamo.fecha_registro))

        if estado:
            query = query.filter(Prestamo.estado == estado)

        return query.limit(limit).all()

    def obtener_todos_prestamos(
        self,
        limit: int = 100,
        offset: int = 0,
        estado: Optional[str] = None,
        orden: str = 'fecha_registro_desc'
    ) -> List[Prestamo]:
        """Obtiene todos los préstamos con filtros opcionales."""
        query = self.db.query(Prestamo)

        if estado:
            query = query.filter(Prestamo.estado == estado)

        # Ordenamiento
        if orden == 'fecha_registro_desc':
            query = query.order_by(desc(Prestamo.fecha_registro))
        elif orden == 'fecha_registro_asc':
            query = query.order_by(Prestamo.fecha_registro)
        elif orden == 'total_asc':
            query = query.order_by(Prestamo.total_financiamiento)
        elif orden == 'total_desc':
            query = query.order_by(desc(Prestamo.total_financiamiento))

        return query.offset(offset).limit(limit).all()

    def actualizar_prestamo(
        self,
        prestamo_id: int,
        datos_actualizacion: dict
    ) -> Prestamo:
        """
        Actualiza un préstamo existente.

        Args:
            prestamo_id: ID del préstamo
            datos_actualizacion: Dict con campos a actualizar

        Returns:
            Préstamo actualizado
        """
        prestamo = self.obtener_prestamo(prestamo_id)

        # Validar transición de estado si se actualiza
        if 'estado' in datos_actualizacion:
            nuevo_estado = datos_actualizacion['estado']
            self.validacion.validar_estado_prestamo(nuevo_estado)
            self.validacion.validar_transicion_estado(prestamo.estado, nuevo_estado)

        # Validar otros campos según lo necesario
        if 'tasa_interes' in datos_actualizacion:
            self.validacion.validar_tasa_interes(
                datos_actualizacion['tasa_interes']
            )

        if 'modalidad_pago' in datos_actualizacion:
            self.validacion.validar_modalidad_pago(
                datos_actualizacion['modalidad_pago']
            )

        if 'numero_cuotas' in datos_actualizacion:
            self.validacion.validar_numero_cuotas(
                datos_actualizacion['numero_cuotas']
            )

        # Actualizar campos
        for campo, valor in datos_actualizacion.items():
            if hasattr(prestamo, campo):
                setattr(prestamo, campo, valor)

        try:
            asegurar_prestamo_alineado_con_cliente(self.db, prestamo)
        except PrestamoCedulaClienteError as e:
            raise PrestamoValidationError("cedula", str(e)) from e

        self.db.add(prestamo)
        self.db.commit()
        self.db.refresh(prestamo)

        return prestamo

    def cambiar_estado_prestamo(
        self,
        prestamo_id: int,
        nuevo_estado: str,
        usuario_cambio: Optional[str] = None,
        observaciones: Optional[str] = None
    ) -> Prestamo:
        """
        Cambia el estado de un préstamo con validaciones de transición.

        Args:
            prestamo_id: ID del préstamo
            nuevo_estado: Nuevo estado
            usuario_cambio: Usuario que realiza el cambio
            observaciones: Observaciones del cambio de estado

        Returns:
            Préstamo con estado actualizado
        """
        prestamo = self.obtener_prestamo(prestamo_id)

        # Validar transición
        self.validacion.validar_transicion_estado(prestamo.estado, nuevo_estado)

        prestamo.estado = nuevo_estado

        # Registrar información del cambio según el nuevo estado
        if nuevo_estado == 'APROBADO':
            prestamo.usuario_aprobador = usuario_cambio or prestamo.usuario_aprobador
            prestamo.fecha_aprobacion = datetime.now()

            # Generar tabla de amortización
            try:
                self.amortizacion.generar_tabla_amortizacion(
                    prestamo_id,
                    fecha_inicio=prestamo.fecha_base_calculo
                )
            except Exception:
                pass

        if nuevo_estado == 'ACTIVO':
            prestamo.usuario_autoriza = usuario_cambio or prestamo.usuario_autoriza

        if observaciones:
            prestamo.observaciones = observaciones

        try:
            asegurar_prestamo_alineado_con_cliente(
                self.db, prestamo, estado_para_validar=nuevo_estado
            )
        except PrestamoCedulaClienteError as e:
            raise PrestamoValidationError("cedula", str(e)) from e

        self.db.add(prestamo)
        self.db.commit()
        self.db.refresh(prestamo)

        return prestamo

    def obtener_resumen_prestamo(self, prestamo_id: int) -> Dict:
        """
        Obtiene un resumen completo del estado del préstamo.

        Returns:
            Dict con información del préstamo y amortización
        """
        prestamo = self.obtener_prestamo(prestamo_id)

        estado_amortizacion = {}
        try:
            estado_amortizacion = self.amortizacion.calcular_estado_amortizacion(
                prestamo_id
            )
        except Exception:
            pass

        return {
            'id': prestamo.id,
            'cliente_id': prestamo.cliente_id,
            'cedula': prestamo.cedula,
            'nombres': prestamo.nombres,
            'producto': prestamo.producto,
            'total_financiamiento': float(prestamo.total_financiamiento),
            'tasa_interes': float(prestamo.tasa_interes),
            'numero_cuotas': prestamo.numero_cuotas,
            'cuota_periodo': float(prestamo.cuota_periodo),
            'modalidad_pago': prestamo.modalidad_pago,
            'estado': prestamo.estado,
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
            'usuario_autoriza': prestamo.usuario_autoriza,
            'analista': prestamo.analista,
            'modelo_vehiculo': prestamo.modelo_vehiculo,
            'valor_activo': float(prestamo.valor_activo) if prestamo.valor_activo else None,
            'amortizacion': estado_amortizacion,
        }

    def obtener_prestamos_por_estado(
        self,
        estado: str,
        limit: int = 100
    ) -> List[Prestamo]:
        """Obtiene todos los préstamos con un estado específico."""
        self.validacion.validar_estado_prestamo(estado)

        return self.db.query(Prestamo)\
            .filter(Prestamo.estado == estado)\
            .order_by(desc(Prestamo.fecha_registro))\
            .limit(limit)\
            .all()

    def obtener_prestamos_vencidos(self, limit: int = 100) -> List[Dict]:
        """Obtiene préstamos con cuotas vencidas."""
        prestamos = self.db.query(Prestamo)\
            .filter(Prestamo.estado == 'ACTIVO')\
            .limit(limit)\
            .all()

        prestamos_vencidos = []
        for prestamo in prestamos:
            try:
                cuotas_vencidas = self.amortizacion.obtener_cuotas_vencidas(
                    prestamo.id
                )
                if cuotas_vencidas:
                    prestamos_vencidos.append({
                        'prestamo_id': prestamo.id,
                        'cliente_id': prestamo.cliente_id,
                        'nombres': prestamo.nombres,
                        'cuotas_vencidas': len(cuotas_vencidas),
                        'primera_cuota_vencida': cuotas_vencidas[0]['fecha_vencimiento'],
                    })
            except Exception:
                continue

        return prestamos_vencidos

    def generar_tabla_amortizacion(
        self,
        prestamo_id: int,
        regenerar: bool = False
    ) -> List[Dict]:
        """
        Genera o regenera la tabla de amortización de un préstamo.

        Args:
            prestamo_id: ID del préstamo
            regenerar: Si True, regenera desde cero

        Returns:
            Tabla de amortización
        """
        return self.amortizacion.generar_tabla_amortizacion(
            prestamo_id,
            regenerar=regenerar
        )

    def obtener_tabla_amortizacion(self, prestamo_id: int) -> List[Dict]:
        """Obtiene la tabla de amortización existente."""
        return self.amortizacion.obtener_tabla_amortizacion(prestamo_id)

    def registrar_pago_cuota(
        self,
        cuota_id: int,
        monto_pagado: float,
        fecha_pago: Optional[date] = None
    ) -> Dict:
        """Registra un pago de cuota."""
        return self.amortizacion.registrar_pago_cuota(
            cuota_id,
            monto_pagado,
            fecha_pago
        )

    def obtener_estadistica_prestamos(self) -> Dict:
        """
        Calcula estadísticas generales de préstamos.

        Returns:
            Dict con estadísticas
        """
        total_prestamos = self.db.query(func.count(Prestamo.id)).scalar() or 0

        total_monto = self.db.query(func.sum(Prestamo.total_financiamiento)).scalar() or 0

        por_estado = {}
        estados_count = self.db.query(
            Prestamo.estado,
            func.count(Prestamo.id)
        ).group_by(Prestamo.estado).all()

        for estado, count in estados_count:
            por_estado[estado] = count

        return {
            'total_prestamos': total_prestamos,
            'monto_total_otorgado': float(total_monto),
            'por_estado': por_estado,
        }
