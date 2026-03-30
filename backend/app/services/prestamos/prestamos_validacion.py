"""Servicios de validación para préstamos."""

from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.utils.cedula_almacenamiento import normalizar_cedula_almacenamiento
from app.models.cliente_con_error import ClienteConError
from .prestamos_excepciones import (
    PrestamoValidationError,
    PrestamoConflictError,
    PrestamoStateError,
    ClienteNotFoundError,
    ClienteConErrorError,
)


class PrestamosValidacion:
    """Servicio de validaciones para préstamos."""

    # Estados válidos en el ciclo de vida del préstamo
    ESTADOS_VALIDOS = {
        'DRAFT': 'Borrador',
        'ENVIADO': 'Enviado a aprobación',
        'APROBADO': 'Aprobado',
        'RECHAZADO': 'Rechazado',
        'ACTIVO': 'Activo',
        'PAGADO': 'Pagado',
        'CANCELADO': 'Cancelado',
        'SUSPENDIDO': 'Suspendido',
    }

    # Transiciones de estado permitidas
    TRANSICIONES_PERMITIDAS = {
        'DRAFT': ['ENVIADO', 'CANCELADO'],
        'ENVIADO': ['APROBADO', 'RECHAZADO', 'DRAFT'],
        'APROBADO': ['ACTIVO', 'RECHAZADO'],
        'RECHAZADO': [],
        'ACTIVO': ['PAGADO', 'SUSPENDIDO', 'CANCELADO'],
        'PAGADO': [],
        'CANCELADO': [],
        'SUSPENDIDO': ['ACTIVO', 'CANCELADO'],
    }

    # Modalidades de pago válidas
    MODALIDADES_VALIDAS = ['MENSUAL', 'QUINCENAL', 'SEMANAL', 'DIARIA']

    def __init__(self, db: Session):
        self.db = db

    def validar_cliente_existe(self, cliente_id: int) -> Cliente:
        """Valida que el cliente existe en la BD."""
        cliente = self.db.query(Cliente).filter(Cliente.id == cliente_id).first()
        if not cliente:
            raise ClienteNotFoundError(cliente_id)
        return cliente

    def validar_cliente_sin_errores(self, cliente_id: int) -> bool:
        """
        Valida que el cliente no tiene errores registrados.
        Algunos estados de error pueden impedir nuevos préstamos.
        """
        cliente_con_error = self.db.query(ClienteConError).filter(
            ClienteConError.cliente_id == cliente_id
        ).first()

        if cliente_con_error:
            raise ClienteConErrorError(
                cliente_id,
                f"Errores: {cliente_con_error.error_type if hasattr(cliente_con_error, 'error_type') else 'Varios'}"
            )
        return True

    def validar_monto_numerico(self, monto: any) -> float:
        """Valida y convierte monto a número."""
        try:
            monto_float = float(monto)
            if monto_float <= 0:
                raise PrestamoValidationError("monto", "Monto debe ser mayor a 0")
            return monto_float
        except (ValueError, TypeError):
            raise PrestamoValidationError("monto", "Monto debe ser un número válido")

    def validar_total_financiamiento(self, monto: float) -> bool:
        """Valida que el total de financiamiento sea válido."""
        if not monto or monto <= 0:
            raise PrestamoValidationError(
                "total_financiamiento",
                "Total de financiamiento debe ser mayor a 0"
            )
        return True

    def validar_numero_cuotas(self, numero_cuotas: int) -> bool:
        """Valida que el número de cuotas sea válido."""
        try:
            cuotas = int(numero_cuotas)
            if cuotas <= 0:
                raise PrestamoValidationError(
                    "numero_cuotas",
                    "Número de cuotas debe ser mayor a 0"
                )
            if cuotas > 360:
                raise PrestamoValidationError(
                    "numero_cuotas",
                    "Número de cuotas no puede exceder 360 (30 años)"
                )
            return True
        except (ValueError, TypeError):
            raise PrestamoValidationError(
                "numero_cuotas",
                "Número de cuotas debe ser un entero válido"
            )

    def validar_tasa_interes(self, tasa: float) -> bool:
        """Valida que la tasa de interés sea válida."""
        try:
            tasa_float = float(tasa)
            if tasa_float < 0:
                raise PrestamoValidationError(
                    "tasa_interes",
                    "Tasa de interés no puede ser negativa"
                )
            if tasa_float > 100:
                raise PrestamoValidationError(
                    "tasa_interes",
                    "Tasa de interés parece demasiado alta (>100%)"
                )
            return True
        except (ValueError, TypeError):
            raise PrestamoValidationError(
                "tasa_interes",
                "Tasa de interés debe ser un número válido"
            )

    def validar_modalidad_pago(self, modalidad: str) -> bool:
        """Valida que la modalidad de pago sea válida."""
        if modalidad not in self.MODALIDADES_VALIDAS:
            raise PrestamoValidationError(
                "modalidad_pago",
                f"Modalidad debe ser una de: {', '.join(self.MODALIDADES_VALIDAS)}"
            )
        return True

    def validar_estado_prestamo(self, estado: str) -> bool:
        """Valida que el estado sea un estado válido."""
        if estado not in self.ESTADOS_VALIDOS:
            raise PrestamoValidationError(
                "estado",
                f"Estado debe ser uno de: {', '.join(self.ESTADOS_VALIDOS.keys())}"
            )
        return True

    def validar_transicion_estado(self, estado_actual: str, estado_nuevo: str) -> bool:
        """Valida que la transición de estado es permitida."""
        transiciones = self.TRANSICIONES_PERMITIDAS.get(estado_actual, [])
        if estado_nuevo not in transiciones:
            raise PrestamoStateError(estado_actual, estado_nuevo)
        return True

    def validar_fecha(self, fecha: date, campo: str = "fecha") -> bool:
        """Valida que una fecha sea válida."""
        try:
            if isinstance(fecha, str):
                fecha = datetime.fromisoformat(fecha).date()
            elif isinstance(fecha, datetime):
                fecha = fecha.date()
            elif not isinstance(fecha, date):
                raise ValueError("Fecha inválida")

            # Validar que no sea fecha futura (excepto para fechas de aprobación futura)
            if fecha > date.today():
                raise PrestamoValidationError(
                    campo,
                    "Fecha no puede ser en el futuro"
                )
            return True
        except (ValueError, TypeError) as e:
            raise PrestamoValidationError(campo, f"Formato de fecha inválido: {str(e)}")

    def validar_fecha_base_calculo(self, fecha_base: Optional[date]) -> bool:
        """Valida la fecha base de cálculo si se proporciona."""
        if fecha_base is None:
            return True

        try:
            if isinstance(fecha_base, str):
                fecha_base = datetime.fromisoformat(fecha_base).date()
            elif isinstance(fecha_base, datetime):
                fecha_base = fecha_base.date()

            if not isinstance(fecha_base, date):
                raise ValueError("Fecha base inválida")

            return True
        except (ValueError, TypeError) as e:
            raise PrestamoValidationError(
                "fecha_base_calculo",
                f"Formato de fecha inválida: {str(e)}"
            )

    def validar_datos_prestamo_completos(self, datos: dict) -> bool:
        """Valida que todos los datos requeridos estén presentes."""
        campos_requeridos = [
            'cliente_id',
            'cedula',
            'nombres',
            'total_financiamiento',
            'fecha_requerimiento',
            'modalidad_pago',
            'numero_cuotas',
            'cuota_periodo',
            'producto',
        ]

        for campo in campos_requeridos:
            if campo not in datos or datos[campo] is None:
                raise PrestamoValidationError(campo, "Campo requerido")

        return True

    def validar_cuota_periodo(self, cuota_periodo: float, total: float, numero_cuotas: int) -> bool:
        """
        Valida que la cuota periódica sea coherente con el total y número de cuotas.
        Permite una tolerancia pequeña por redondeo.
        """
        try:
            cuota = float(cuota_periodo)
            total_f = float(total)
            cuotas = int(numero_cuotas)

            if cuota <= 0:
                raise PrestamoValidationError(
                    "cuota_periodo",
                    "Cuota periódica debe ser mayor a 0"
                )

            # Calcular cuota teórica esperada (sin intereses)
            cuota_esperada = total_f / cuotas
            diferencia_porcentaje = abs(cuota - cuota_esperada) / cuota_esperada * 100

            # Permitir hasta 10% de diferencia (por intereses y redondeo)
            if diferencia_porcentaje > 10:
                # No es error crítico, solo advertencia en logs
                pass

            return True
        except (ValueError, TypeError):
            raise PrestamoValidationError(
                "cuota_periodo",
                "Cuota periódica debe ser un número válido"
            )

    def validar_prestamo_existente(self, prestamo_id: int) -> Prestamo:
        """Valida que un préstamo existe."""
        prestamo = self.db.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
        if not prestamo:
            from .prestamos_excepciones import PrestamoNotFoundError
            raise PrestamoNotFoundError(prestamo_id)
        return prestamo

    def validar_cedula_unica_por_cliente(self, cliente_id: int, cedula: str) -> bool:
        """
        Valida que la cédula enviada coincida con la ficha del cliente (misma regla que auditoria).
        """
        cliente = self.db.query(Cliente).filter(Cliente.id == cliente_id).first()
        if not cliente:
            raise ClienteNotFoundError(cliente_id)
        n_in = normalizar_cedula_almacenamiento(cedula) or ""
        n_cli = normalizar_cedula_almacenamiento(cliente.cedula) or ""
        if n_in != n_cli:
            raise PrestamoConflictError(
                f"Cedula del prestamo debe coincidir con la del cliente (cliente_id={cliente_id})."
            )
        return True

    def validar_codigo_ml_riesgo(self, codigo: Optional[str]) -> bool:
        """Valida códigos de nivel de riesgo ML."""
        if codigo is None:
            return True

        codigos_validos = ['BAJO', 'MEDIO', 'ALTO', 'CRÍTICO']
        if codigo not in codigos_validos:
            raise PrestamoValidationError(
                "ml_impago_nivel_riesgo",
                f"Código de riesgo debe ser uno de: {', '.join(codigos_validos)}"
            )
        return True

    def validar_probabilidad_ml(self, probabilidad: Optional[float]) -> bool:
        """Valida que la probabilidad ML esté entre 0 y 1."""
        if probabilidad is None:
            return True

        try:
            prob = float(probabilidad)
            if prob < 0 or prob > 1:
                raise PrestamoValidationError(
                    "ml_impago_probabilidad",
                    "Probabilidad debe estar entre 0 y 1"
                )
            return True
        except (ValueError, TypeError):
            raise PrestamoValidationError(
                "ml_impago_probabilidad",
                "Probabilidad debe ser un número entre 0 y 1"
            )

    def validar_observaciones(self, observaciones: Optional[str]) -> bool:
        """Valida el campo de observaciones."""
        if observaciones is None:
            return True

        if isinstance(observaciones, str) and len(observaciones) > 1000:
            raise PrestamoValidationError(
                "observaciones",
                "Observaciones no pueden exceder 1000 caracteres"
            )
        return True

    def validar_valor_activo(self, valor: Optional[float]) -> bool:
        """Valida que el valor del activo (vehículo) sea válido."""
        if valor is None:
            return True

        try:
            valor_f = float(valor)
            if valor_f < 0:
                raise PrestamoValidationError(
                    "valor_activo",
                    "Valor del activo no puede ser negativo"
                )
            return True
        except (ValueError, TypeError):
            raise PrestamoValidationError(
                "valor_activo",
                "Valor del activo debe ser un número válido"
            )
