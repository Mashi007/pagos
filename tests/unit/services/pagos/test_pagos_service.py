"""Tests unitarios para servicios de pagos."""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from app.services.pagos import (
    PagosService,
    PagosValidacion,
    PagosCalculo,
    PagoNotFoundError,
    PagoValidationError,
    PagoConflictError,
    ClienteNotFoundError,
)


class TestPagosValidacion:
    """Tests para el servicio PagosValidacion."""

    @pytest.fixture
    def db_mock(self):
        return MagicMock()

    @pytest.fixture
    def validacion_service(self, db_mock):
        return PagosValidacion(db_mock)

    def test_validar_cliente_existe_exitoso(self, validacion_service, db_mock):
        """Test validación de cliente existente."""
        cliente_mock = MagicMock()
        cliente_mock.id = 1
        db_mock.query.return_value.filter.return_value.first.return_value = cliente_mock

        resultado = validacion_service.validar_cliente_existe(1)
        
        assert resultado.id == 1
        assert db_mock.query.called

    def test_validar_cliente_no_existe(self, validacion_service, db_mock):
        """Test validación de cliente que no existe."""
        db_mock.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(ClienteNotFoundError) as exc_info:
            validacion_service.validar_cliente_existe(999)
        
        assert exc_info.value.cliente_id == 999

    def test_validar_monto_valido(self, validacion_service):
        """Test validación de monto válido."""
        resultado = validacion_service.validar_monto(100.00)
        assert resultado is True

    def test_validar_monto_cero(self, validacion_service):
        """Test validación de monto cero (debe fallar)."""
        with pytest.raises(PagoValidationError) as exc_info:
            validacion_service.validar_monto(0)
        
        assert "mayor a 0" in str(exc_info.value)

    def test_validar_monto_negativo(self, validacion_service):
        """Test validación de monto negativo (debe fallar)."""
        with pytest.raises(PagoValidationError):
            validacion_service.validar_monto(-100)

    def test_validar_monto_numerico_valido(self, validacion_service):
        """Test conversión de monto a número."""
        resultado = validacion_service.validar_monto_numerico("150.50")
        assert resultado == 150.50

    def test_validar_monto_numerico_invalido(self, validacion_service):
        """Test conversión de monto inválido."""
        with pytest.raises(PagoValidationError):
            validacion_service.validar_monto_numerico("abc")

    def test_validar_documento_no_duplicado_permitido(self, validacion_service, db_mock):
        """Test validación de documento sin duplicados."""
        with patch(
            "app.services.pagos.pagos_validacion.numero_documento_ya_registrado",
            return_value=False,
        ):
            resultado = validacion_service.validar_documento_no_duplicado("DOC123")
        assert resultado is True

    def test_validar_documento_duplicado(self, validacion_service, db_mock):
        """Test validación de documento duplicado."""
        with patch(
            "app.services.pagos.pagos_validacion.numero_documento_ya_registrado",
            return_value=True,
        ):
            with pytest.raises(PagoConflictError) as exc_info:
                validacion_service.validar_documento_no_duplicado("DOC123")

        msg = str(exc_info.value).lower()
        assert "duplicado" in msg or "comprobante" in msg or "existe" in msg

    def test_validar_estado_pago_valido(self, validacion_service):
        """Test validación de estado válido."""
        resultado = validacion_service.validar_estado_pago("pendiente")
        assert resultado is True

    def test_validar_estado_pago_invalido(self, validacion_service):
        """Test validación de estado inválido."""
        with pytest.raises(PagoValidationError):
            validacion_service.validar_estado_pago("estado_invalido")

    def test_validar_datos_pago_completos_ok(self, validacion_service):
        """Test validación de datos completos."""
        datos = {'cliente_id': 1, 'monto': 100}
        resultado = validacion_service.validar_datos_pago_completos(datos)
        assert resultado is True

    def test_validar_datos_pago_incompletos(self, validacion_service):
        """Test validación de datos incompletos."""
        datos = {'cliente_id': 1}  # Falta monto
        
        with pytest.raises(PagoValidationError):
            validacion_service.validar_datos_pago_completos(datos)


class TestPagosCalculo:
    """Tests para el servicio PagosCalculo."""

    @pytest.fixture
    def db_mock(self):
        return MagicMock()

    @pytest.fixture
    def calculo_service(self, db_mock):
        return PagosCalculo(db_mock)

    def test_convertir_pesos_a_dolares_con_tasa(self, calculo_service):
        """Test conversión pesos a dólares."""
        resultado = calculo_service.convertir_pesos_a_dolares(1000, tasa=50)
        assert resultado == 20.0

    def test_convertir_pesos_a_dolares_sin_tasa(self, calculo_service, db_mock):
        """Test conversión sin tasa (debe obtener actual)."""
        tasa_mock = MagicMock()
        tasa_mock.valor = 50
        db_mock.query.return_value.order_by.return_value.first.return_value = tasa_mock

        resultado = calculo_service.convertir_pesos_a_dolares(1000)
        assert resultado == 20.0

    def test_convertir_pesos_a_dolares_sin_tasa_disponible(self, calculo_service, db_mock):
        """Test conversión sin tasa disponible (retorna monto original)."""
        db_mock.query.return_value.order_by.return_value.first.return_value = None

        resultado = calculo_service.convertir_pesos_a_dolares(1000)
        assert resultado == 1000.0

    def test_convertir_dolares_a_pesos(self, calculo_service):
        """Test conversión dólares a pesos."""
        resultado = calculo_service.convertir_dolares_a_pesos(20, tasa=50)
        assert resultado == 1000.0

    def test_calcular_interes(self, calculo_service):
        """Test cálculo de intereses."""
        resultado = calculo_service.calcular_interes(1000, dias_atraso=10, tasa_interes_diaria=0.001)
        assert resultado == 10.0  # 1000 * 0.001 * 10

    def test_calcular_interes_sin_atraso(self, calculo_service):
        """Test cálculo sin atraso."""
        resultado = calculo_service.calcular_interes(1000, dias_atraso=0)
        assert resultado == 0.0

    def test_calcular_multa(self, calculo_service):
        """Test cálculo de multa."""
        resultado = calculo_service.calcular_multa(1000, porcentaje_multa=5)
        assert resultado == 50.0  # 1000 * 5 / 100

    def test_calcular_total_con_intereses_multa(self, calculo_service):
        """Test cálculo total con todos los conceptos."""
        resultado = calculo_service.calcular_total_con_intereses_multa(
            monto_principal=1000,
            dias_atraso=10,
            porcentaje_multa=5,
            tasa_interes_diaria=0.001
        )
        
        assert resultado['principal'] == 1000.0
        assert resultado['interes'] == 10.0
        assert resultado['multa'] == 50.0
        assert resultado['total'] == 1060.0

    def test_redondear_monto(self, calculo_service):
        """Test redondeo de monto."""
        resultado = calculo_service.redondear_monto(100.555, decimales=2)
        assert resultado == 100.56


class TestPagosService:
    """Tests para el servicio principal PagosService."""

    @pytest.fixture
    def db_mock(self):
        return MagicMock()

    @pytest.fixture
    def pagos_service(self, db_mock):
        return PagosService(db_mock)

    def test_crear_pago_desactivado_debe_usar_api(self, pagos_service):
        """crear_pago en servicio está desactivado; altas van por POST /pagos o cobros/import."""
        with pytest.raises(PagoValidationError) as exc:
            pagos_service.crear_pago(
                {"cliente_id": 1, "monto": 1000, "estado": "pendiente"}
            )
        assert "POST /pagos" in str(exc.value)

    def test_obtener_pago_exitoso(self, pagos_service, db_mock):
        """Test obtención exitosa de pago."""
        pago_mock = MagicMock()
        pago_mock.id = 1
        db_mock.query.return_value.filter.return_value.first.return_value = pago_mock

        resultado = pagos_service.obtener_pago(1)
        
        assert resultado.id == 1

    def test_obtener_pago_no_existe(self, pagos_service, db_mock):
        """Test obtención de pago inexistente."""
        db_mock.query.return_value.filter.return_value.first.return_value = None

        with pytest.raises(PagoNotFoundError):
            pagos_service.obtener_pago(999)

    def test_actualizar_estado_pago(self, pagos_service, db_mock):
        """Test actualización de estado de pago."""
        pago_mock = MagicMock()
        pago_mock.id = 1
        pago_mock.estado = 'pendiente'
        db_mock.query.return_value.filter.return_value.first.return_value = pago_mock

        resultado = pagos_service.actualizar_estado_pago(1, 'aplicado')
        
        assert db_mock.commit.called
        assert pago_mock.estado == 'aplicado'

    def test_obtener_resumen_pagos(self, pagos_service, db_mock):
        """Test obtención de resumen de pagos."""
        # Mock para contar pagos
        db_mock.query.return_value.count.return_value = 5
        
        # Mock para suma
        db_mock.query.return_value.filter.return_value.scalar.return_value = 5000
        
        resultado = pagos_service.obtener_resumen_pagos()
        
        assert 'total_pagos' in resultado
        assert 'total_monto' in resultado
        assert 'monto_promedio' in resultado


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
