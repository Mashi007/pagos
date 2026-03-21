"""Tests para servicios de préstamos."""

import pytest
from decimal import Decimal
from datetime import date, timedelta
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

from app.services.prestamos import (
    PrestamosService,
    PrestamosValidacion,
    PrestamosCalculo,
    AmortizacionService,
    PrestamoNotFoundError,
    PrestamoValidationError,
    PrestamoConflictError,
    PrestamoStateError,
    ClienteNotFoundError,
    AmortizacionCalculoError,
)


class TestPrestamosValidacion:
    """Tests para validación de préstamos."""

    @pytest.fixture
    def db_mock(self):
        """Mock de la sesión de BD."""
        return Mock(spec=Session)

    @pytest.fixture
    def validacion(self, db_mock):
        """Instancia del servicio de validación."""
        return PrestamosValidacion(db_mock)

    def test_validar_cliente_existe(self, validacion, db_mock):
        """Valida que cliente exista."""
        cliente_mock = Mock()
        db_mock.query.return_value.filter.return_value.first.return_value = cliente_mock

        resultado = validacion.validar_cliente_existe(1)
        assert resultado == cliente_mock

    def test_validar_cliente_no_existe(self, validacion, db_mock):
        """Lanza error si cliente no existe."""
        db_mock.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ClienteNotFoundError):
            validacion.validar_cliente_existe(999)

    def test_validar_monto_numerico_valido(self, validacion):
        """Valida monto numérico válido."""
        resultado = validacion.validar_monto_numerico(1000.50)
        assert resultado == 1000.50

    def test_validar_monto_numerico_string(self, validacion):
        """Valida monto como string."""
        resultado = validacion.validar_monto_numerico("1000.50")
        assert resultado == 1000.50

    def test_validar_monto_numerico_negativo(self, validacion):
        """Rechaza monto negativo."""
        with pytest.raises(PrestamoValidationError):
            validacion.validar_monto_numerico(-100)

    def test_validar_monto_numerico_cero(self, validacion):
        """Rechaza monto cero."""
        with pytest.raises(PrestamoValidationError):
            validacion.validar_monto_numerico(0)

    def test_validar_numero_cuotas_valido(self, validacion):
        """Valida número de cuotas válido."""
        assert validacion.validar_numero_cuotas(12) is True

    def test_validar_numero_cuotas_invalido(self, validacion):
        """Rechaza número de cuotas inválido."""
        with pytest.raises(PrestamoValidationError):
            validacion.validar_numero_cuotas(0)

    def test_validar_numero_cuotas_demasiadas(self, validacion):
        """Rechaza número de cuotas > 360."""
        with pytest.raises(PrestamoValidationError):
            validacion.validar_numero_cuotas(361)

    def test_validar_tasa_interes_valida(self, validacion):
        """Valida tasa de interés válida."""
        assert validacion.validar_tasa_interes(12.5) is True

    def test_validar_tasa_interes_negativa(self, validacion):
        """Rechaza tasa negativa."""
        with pytest.raises(PrestamoValidationError):
            validacion.validar_tasa_interes(-5)

    def test_validar_modalidad_pago_valida(self, validacion):
        """Valida modalidad de pago válida."""
        assert validacion.validar_modalidad_pago('MENSUAL') is True
        assert validacion.validar_modalidad_pago('QUINCENAL') is True

    def test_validar_modalidad_pago_invalida(self, validacion):
        """Rechaza modalidad inválida."""
        with pytest.raises(PrestamoValidationError):
            validacion.validar_modalidad_pago('TRIMESTRAL')

    def test_validar_estado_prestamo_valido(self, validacion):
        """Valida estado válido."""
        assert validacion.validar_estado_prestamo('DRAFT') is True
        assert validacion.validar_estado_prestamo('APROBADO') is True

    def test_validar_estado_prestamo_invalido(self, validacion):
        """Rechaza estado inválido."""
        with pytest.raises(PrestamoValidationError):
            validacion.validar_estado_prestamo('INVALIDO')

    def test_validar_transicion_estado_valida(self, validacion):
        """Valida transición de estado válida."""
        assert validacion.validar_transicion_estado('DRAFT', 'ENVIADO') is True

    def test_validar_transicion_estado_invalida(self, validacion):
        """Rechaza transición inválida."""
        with pytest.raises(PrestamoStateError):
            validacion.validar_transicion_estado('DRAFT', 'PAGADO')

    def test_validar_datos_prestamo_completos_falta_campo(self, validacion):
        """Rechaza datos incompletos."""
        datos = {'cliente_id': 1}  # Falta monto

        with pytest.raises(PrestamoValidationError):
            validacion.validar_datos_prestamo_completos(datos)

    def test_validar_datos_prestamo_completos_valido(self, validacion):
        """Valida datos completos."""
        datos = {
            'cliente_id': 1,
            'cedula': '123456',
            'nombres': 'Test User',
            'total_financiamiento': 10000,
            'fecha_requerimiento': date.today(),
            'modalidad_pago': 'MENSUAL',
            'numero_cuotas': 12,
            'cuota_periodo': 833.33,
            'producto': 'Producto Test'
        }

        assert validacion.validar_datos_prestamo_completos(datos) is True

    def test_validar_cuota_periodo_coherente(self, validacion):
        """Valida que cuota periódica sea coherente."""
        assert validacion.validar_cuota_periodo(833.33, 10000, 12) is True

    def test_validar_cuota_periodo_incoherente(self, validacion):
        """Detecta cuota muy diferente del esperado."""
        # No lanza error pero continúa (solo log)
        assert validacion.validar_cuota_periodo(100, 10000, 12) is True


class TestPrestamosCalculo:
    """Tests para cálculos financieros."""

    @pytest.fixture
    def db_mock(self):
        """Mock de la sesión de BD."""
        return Mock(spec=Session)

    @pytest.fixture
    def calculo(self, db_mock):
        """Instancia del servicio de cálculo."""
        return PrestamosCalculo(db_mock)

    def test_convertir_pesos_a_dolares_con_tasa(self, calculo):
        """Convierte pesos a dólares con tasa proporcionada."""
        resultado = calculo.convertir_pesos_a_dolares(1000, tasa=50.0)
        assert resultado == 20.0

    def test_convertir_pesos_a_dolares_sin_tasa(self, calculo, db_mock):
        """Retorna monto original si no hay tasa."""
        db_mock.query.return_value.order_by.return_value.first.return_value = None

        resultado = calculo.convertir_pesos_a_dolares(1000)
        assert resultado == 1000.0

    def test_convertir_dolares_a_pesos(self, calculo):
        """Convierte dólares a pesos."""
        resultado = calculo.convertir_dolares_a_pesos(20, tasa=50.0)
        assert resultado == 1000.0

    def test_calcular_interes_simple(self, calculo):
        """Calcula interés simple."""
        # Principal: 1000, Tasa: 12% anual, Días: 30
        interes = calculo.calcular_interes_simple(1000, 12, 30)
        # (1000 * 0.12 * 30) / 365 = 9.86
        assert abs(interes - 9.86) < 0.01

    def test_calcular_interes_compuesto(self, calculo):
        """Calcula interés compuesto."""
        # Principal: 1000, Tasa: 12%, Períodos: 12, Días entre: 30
        interes = calculo.calcular_interes_compuesto(1000, 12, 12)
        assert interes > 0

    def test_calcular_cuota_fija_sin_interes(self, calculo):
        """Calcula cuota fija sin interés."""
        # 10000 en 12 cuotas sin interés = 833.33
        cuota = calculo.calcular_cuota_fija(10000, 0, 12)
        assert abs(cuota - 833.33) < 0.01

    def test_calcular_cuota_fija_con_interes(self, calculo):
        """Calcula cuota fija con interés."""
        # 10000 en 12 cuotas al 12% anual
        cuota = calculo.calcular_cuota_fija(10000, 12, 12)
        assert cuota > 833.33  # Debe ser mayor por interés

    def test_calcular_interes_periodo(self, calculo):
        """Calcula interés de un período."""
        interes = calculo.calcular_interes_periodo(10000, 12, 'MENSUAL')
        assert interes > 0

    def test_calcular_amortizacion_periodo(self, calculo):
        """Calcula amortización de un período."""
        amortizacion = calculo.calcular_amortizacion_periodo(100, 20)
        assert amortizacion == 80.0

    def test_calcular_vat(self, calculo):
        """Calcula VAT/IVA."""
        vat = calculo.calcular_vat(100, tasa_vat=13)
        assert vat == 13.0

    def test_calcular_tasa_efectiva(self, calculo):
        """Calcula tasa efectiva anual."""
        # Tasa nominal 12% con 12 períodos
        tea = calculo.calcular_tasa_efectiva(12, 12)
        assert tea > 12  # TEA debe ser mayor que tasa nominal


class TestAmortizacionService:
    """Tests para servicio de amortización."""

    @pytest.fixture
    def db_mock(self):
        """Mock de la sesión de BD."""
        return Mock(spec=Session)

    @pytest.fixture
    def amortizacion(self, db_mock):
        """Instancia del servicio de amortización."""
        return AmortizacionService(db_mock)

    def test_calcular_siguiente_fecha_cuota_mensual(self, amortizacion):
        """Calcula siguiente fecha para modalidad mensual."""
        fecha = date(2024, 1, 15)
        siguiente = amortizacion.calcular_siguiente_fecha_cuota(fecha, 'MENSUAL')
        assert siguiente == date(2024, 2, 15)

    def test_calcular_siguiente_fecha_cuota_mensual_año_nuevo(self, amortizacion):
        """Calcula siguiente fecha al cambiar de año."""
        fecha = date(2024, 12, 15)
        siguiente = amortizacion.calcular_siguiente_fecha_cuota(fecha, 'MENSUAL')
        assert siguiente == date(2025, 1, 15)

    def test_calcular_siguiente_fecha_cuota_quincenal(self, amortizacion):
        """Calcula siguiente fecha para modalidad quincenal."""
        fecha = date(2024, 1, 15)
        siguiente = amortizacion.calcular_siguiente_fecha_cuota(fecha, 'QUINCENAL')
        assert siguiente == date(2024, 1, 30)

    def test_calcular_siguiente_fecha_cuota_semanal(self, amortizacion):
        """Calcula siguiente fecha para modalidad semanal."""
        fecha = date(2024, 1, 15)
        siguiente = amortizacion.calcular_siguiente_fecha_cuota(fecha, 'SEMANAL')
        assert siguiente == date(2024, 1, 22)

    def test_calcular_siguiente_fecha_cuota_diaria(self, amortizacion):
        """Calcula siguiente fecha para modalidad diaria."""
        fecha = date(2024, 1, 15)
        siguiente = amortizacion.calcular_siguiente_fecha_cuota(fecha, 'DIARIA')
        assert siguiente == date(2024, 1, 16)


class TestPrestamosService:
    """Tests para servicio principal de préstamos."""

    @pytest.fixture
    def db_mock(self):
        """Mock de la sesión de BD."""
        return Mock(spec=Session)

    @pytest.fixture
    def service(self, db_mock):
        """Instancia del servicio de préstamos."""
        return PrestamosService(db_mock)

    def test_crear_prestamo_falta_cliente(self, service, db_mock):
        """Rechaza creación sin cliente válido."""
        db_mock.query.return_value.filter.return_value.first.return_value = None

        datos = {
            'cliente_id': 999,
            'cedula': '123456',
            'nombres': 'Test',
            'total_financiamiento': 10000,
            'fecha_requerimiento': date.today(),
            'modalidad_pago': 'MENSUAL',
            'numero_cuotas': 12,
            'cuota_periodo': 833.33,
            'producto': 'Test'
        }

        with pytest.raises(ClienteNotFoundError):
            service.crear_prestamo(datos)

    def test_obtener_prestamo_no_existe(self, service, db_mock):
        """Lanza error si préstamo no existe."""
        db_mock.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(PrestamoNotFoundError):
            service.obtener_prestamo(999)

    def test_cambiar_estado_prestamo_valido(self, service, db_mock):
        """Cambia estado de préstamo válido."""
        prestamo_mock = Mock()
        prestamo_mock.estado = 'DRAFT'
        db_mock.query.return_value.filter.return_value.first.return_value = prestamo_mock

        resultado = service.cambiar_estado_prestamo(1, 'ENVIADO')
        assert resultado.estado == 'ENVIADO'

    def test_cambiar_estado_prestamo_invalido(self, service, db_mock):
        """Rechaza cambio de estado inválido."""
        prestamo_mock = Mock()
        prestamo_mock.estado = 'DRAFT'
        db_mock.query.return_value.filter.return_value.first.return_value = prestamo_mock

        with pytest.raises(PrestamoStateError):
            service.cambiar_estado_prestamo(1, 'PAGADO')

    def test_obtener_estadistica_prestamos(self, service, db_mock):
        """Obtiene estadísticas de préstamos."""
        db_mock.query.return_value.scalar.return_value = 10
        db_mock.query.return_value.group_by.return_value.all.return_value = [
            ('DRAFT', 3),
            ('APROBADO', 5),
            ('ACTIVO', 2),
        ]

        stats = service.obtener_estadistica_prestamos()
        assert stats['total_prestamos'] == 10


class TestAdaptadorCompatibilidad:
    """Tests para adaptador de compatibilidad."""

    @pytest.fixture
    def db_mock(self):
        """Mock de la sesión de BD."""
        return Mock(spec=Session)

    def test_validar_datos_antes_crear_valido(self, db_mock):
        """Valida datos completos."""
        from app.services.prestamos import AdaptadorPrestamosLegacy

        adaptador = AdaptadorPrestamosLegacy(db_mock)

        datos = {
            'cliente_id': 1,
            'cedula': '123456',
            'nombres': 'Test',
            'total_financiamiento': 10000,
            'fecha_requerimiento': date.today(),
            'modalidad_pago': 'MENSUAL',
            'numero_cuotas': 12,
            'cuota_periodo': 833.33,
            'producto': 'Test'
        }

        db_mock.query.return_value.filter.return_value.first.return_value = Mock()

        es_valido, error = adaptador.validar_datos_antes_crear(datos)
        assert es_valido is True
        assert error is None

    def test_validar_datos_antes_crear_invalido(self, db_mock):
        """Detecta datos inválidos."""
        from app.services.prestamos import AdaptadorPrestamosLegacy

        adaptador = AdaptadorPrestamosLegacy(db_mock)

        datos = {'cliente_id': 999}  # Datos incompletos

        es_valido, error = adaptador.validar_datos_antes_crear(datos)
        assert es_valido is False
        assert error is not None


class TestCasosEdge:
    """Tests para casos edge y especiales."""

    @pytest.fixture
    def db_mock(self):
        """Mock de la sesión de BD."""
        return Mock(spec=Session)

    @pytest.fixture
    def calculo(self, db_mock):
        """Instancia del servicio de cálculo."""
        return PrestamosCalculo(db_mock)

    def test_convertir_monto_cero(self, calculo):
        """Maneja monto cero."""
        resultado = calculo.convertir_pesos_a_dolares(0, tasa=50)
        assert resultado == 0.0

    def test_convertir_monto_negativo(self, calculo):
        """Maneja monto negativo."""
        resultado = calculo.convertir_pesos_a_dolares(-100, tasa=50)
        assert resultado == 0.0

    def test_tasa_cero(self, calculo):
        """Maneja tasa cero."""
        resultado = calculo.convertir_pesos_a_dolares(1000, tasa=0)
        assert resultado == 1000.0

    def test_calcular_cuota_un_periodo(self, calculo):
        """Calcula cuota para un solo período."""
        cuota = calculo.calcular_cuota_fija(10000, 0, 1)
        assert cuota == 10000.0

    def test_interes_atraso_cero_dias(self, calculo):
        """Calcula interés con cero días de atraso."""
        interes = calculo.calcular_interes_simple(1000, 12, 0)
        assert interes == 0.0

    def test_vat_cero_porciento(self, calculo):
        """Calcula VAT con 0%."""
        vat = calculo.calcular_vat(100, tasa_vat=0)
        assert vat == 0.0
