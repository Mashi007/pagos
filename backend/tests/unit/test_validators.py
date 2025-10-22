"""
Pruebas Unitarias - Validadores
Testing de la lógica de validación del sistema
"""
import pytest
from datetime import date, datetime
from decimal import Decimal

from app.services.validators_service import (
    ValidadorTelefono,
    ValidadorCedula,
    ValidadorFecha,
    ValidadorMonto,
    ValidadorAmortizaciones,
    ValidadorEmail,
    ValidadorEdad,
    ValidadorCoherenciaFinanciera,
    ValidadorDuplicados
)


class TestValidadorTelefono:
    """Pruebas para ValidadorTelefono"""

    def test_telefono_valido_venezuela(self):
        """Probar teléfono válido de Venezuela"""
        validador = ValidadorTelefono()
        resultado = validador.validar("+58412123456")

        assert resultado["valido"] is True
        assert resultado["valor_formateado"] == "+58412123456"
        assert resultado["pais"] == "VENEZUELA"

    def test_telefono_invalido_formato(self):
        """Probar teléfono con formato inválido"""
        validador = ValidadorTelefono()
        resultado = validador.validar("0412123456")

        assert resultado["valido"] is False
        assert "formato" in resultado["error"].lower()

    def test_telefono_corto(self):
        """Probar teléfono muy corto"""
        validador = ValidadorTelefono()
        resultado = validador.validar("+58412123")

        assert resultado["valido"] is False
        assert "longitud" in resultado["error"].lower()

    def test_telefono_vacio(self):
        """Probar teléfono vacío"""
        validador = ValidadorTelefono()
        resultado = validador.validar("")

        assert resultado["valido"] is False
        assert "requerido" in resultado["error"].lower()


class TestValidadorCedula:
    """Pruebas para ValidadorCedula"""

    def test_cedula_valida_venezolana(self):
        """Probar cédula venezolana válida"""
        validador = ValidadorCedula()
        resultado = validador.validar("V12345678")

        assert resultado["valido"] is True
        assert resultado["valor_formateado"] == "V12345678"
        assert resultado["pais"] == "VENEZUELA"
        assert resultado["tipo"] == "Venezolano"

    def test_cedula_valida_extranjera(self):
        """Probar cédula de extranjero válida"""
        validador = ValidadorCedula()
        resultado = validador.validar("E12345678")

        assert resultado["valido"] is True
        assert resultado["valor_formateado"] == "E12345678"
        assert resultado["tipo"] == "Extranjero"

    def test_cedula_valida_juridica(self):
        """Probar cédula jurídica válida"""
        validador = ValidadorCedula()
        resultado = validador.validar("J12345678")

        assert resultado["valido"] is True
        assert resultado["valor_formateado"] == "J12345678"
        assert resultado["tipo"] == "Jurídica"

    def test_cedula_invalida_prefijo(self):
        """Probar cédula con prefijo inválido"""
        validador = ValidadorCedula()
        resultado = validador.validar("X12345678")

        assert resultado["valido"] is False
        assert "prefijo" in resultado["error"].lower()

    def test_cedula_corta(self):
        """Probar cédula muy corta"""
        validador = ValidadorCedula()
        resultado = validador.validar("V123")

        assert resultado["valido"] is False
        assert "longitud" in resultado["error"].lower()

    def test_cedula_vacia(self):
        """Probar cédula vacía"""
        validador = ValidadorCedula()
        resultado = validador.validar("")

        assert resultado["valido"] is False
        assert "requerido" in resultado["error"].lower()


class TestValidadorFecha:
    """Pruebas para ValidadorFecha"""

    def test_fecha_valida_formato_dd_mm_yyyy(self):
        """Probar fecha válida en formato DD/MM/YYYY"""
        validador = ValidadorFecha()
        resultado = validador.validar("01/01/1990")

        assert resultado["valido"] is True
        assert resultado["valor_formateado"] == "01/01/1990"
        assert resultado["fecha_parseada"] == date(1990, 1, 1)

    def test_fecha_invalida_formato(self):
        """Probar fecha con formato inválido"""
        validador = ValidadorFecha()
        resultado = validador.validar("1990-01-01")

        assert resultado["valido"] is False
        assert "formato" in resultado["error"].lower()

    def test_fecha_invalida_dia(self):
        """Probar fecha con día inválido"""
        validador = ValidadorFecha()
        resultado = validador.validar("32/01/1990")

        assert resultado["valido"] is False
        assert "día" in resultado["error"].lower()

    def test_fecha_invalida_mes(self):
        """Probar fecha con mes inválido"""
        validador = ValidadorFecha()
        resultado = validador.validar("01/13/1990")

        assert resultado["valido"] is False
        assert "mes" in resultado["error"].lower()

    def test_fecha_futura(self):
        """Probar fecha futura"""
        validador = ValidadorFecha()
        resultado = validador.validar("01/01/2030")

        assert resultado["valido"] is False
        assert "futura" in resultado["error"].lower()

    def test_fecha_muy_antigua(self):
        """Probar fecha muy antigua"""
        validador = ValidadorFecha()
        resultado = validador.validar("01/01/1900")

        assert resultado["valido"] is False
        assert "antigua" in resultado["error"].lower()


class TestValidadorMonto:
    """Pruebas para ValidadorMonto"""

    def test_monto_valido_positivo(self):
        """Probar monto válido positivo"""
        validador = ValidadorMonto()
        resultado = validador.validar("1000.50")

        assert resultado["valido"] is True
        assert resultado["valor_formateado"] == "1000.50"
        assert resultado["monto_numerico"] == Decimal("1000.50")

    def test_monto_valido_entero(self):
        """Probar monto válido entero"""
        validador = ValidadorMonto()
        resultado = validador.validar("1000")

        assert resultado["valido"] is True
        assert resultado["valor_formateado"] == "1000.00"
        assert resultado["monto_numerico"] == Decimal("1000.00")

    def test_monto_negativo(self):
        """Probar monto negativo"""
        validador = ValidadorMonto()
        resultado = validador.validar("-1000")

        assert resultado["valido"] is False
        assert "negativo" in resultado["error"].lower()

    def test_monto_cero(self):
        """Probar monto cero"""
        validador = ValidadorMonto()
        resultado = validador.validar("0")

        assert resultado["valido"] is False
        assert "cero" in resultado["error"].lower()

    def test_monto_invalido_formato(self):
        """Probar monto con formato inválido"""
        validador = ValidadorMonto()
        resultado = validador.validar("abc")

        assert resultado["valido"] is False
        assert "formato" in resultado["error"].lower()

    def test_monto_muy_grande(self):
        """Probar monto muy grande"""
        validador = ValidadorMonto()
        resultado = validador.validar("999999999999")

        assert resultado["valido"] is False
        assert "límite" in resultado["error"].lower()


class TestValidadorAmortizaciones:
    """Pruebas para ValidadorAmortizaciones"""

    def test_amortizaciones_validas(self):
        """Probar número de amortizaciones válido"""
        validador = ValidadorAmortizaciones()
        resultado = validador.validar("24")

        assert resultado["valido"] is True
        assert resultado["valor_formateado"] == "24"
        assert resultado["numero_amortizaciones"] == 24

    def test_amortizaciones_cero(self):
        """Probar amortizaciones cero"""
        validador = ValidadorAmortizaciones()
        resultado = validador.validar("0")

        assert resultado["valido"] is False
        assert "cero" in resultado["error"].lower()

    def test_amortizaciones_negativas(self):
        """Probar amortizaciones negativas"""
        validador = ValidadorAmortizaciones()
        resultado = validador.validar("-5")

        assert resultado["valido"] is False
        assert "negativo" in resultado["error"].lower()

    def test_amortizaciones_muy_grandes(self):
        """Probar amortizaciones muy grandes"""
        validador = ValidadorAmortizaciones()
        resultado = validador.validar("500")

        assert resultado["valido"] is False
        assert "límite" in resultado["error"].lower()

    def test_amortizaciones_decimales(self):
        """Probar amortizaciones con decimales"""
        validador = ValidadorAmortizaciones()
        resultado = validador.validar("24.5")

        assert resultado["valido"] is False
        assert "entero" in resultado["error"].lower()


class TestValidadorEmail:
    """Pruebas para ValidadorEmail"""

    def test_email_valido(self):
        """Probar email válido"""
        validador = ValidadorEmail()
        resultado = validador.validar("test@example.com")

        assert resultado["valido"] is True
        assert resultado["valor_formateado"] == "test@example.com"

    def test_email_invalido_formato(self):
        """Probar email con formato inválido"""
        validador = ValidadorEmail()
        resultado = validador.validar("test@")

        assert resultado["valido"] is False
        assert "formato" in resultado["error"].lower()

    def test_email_sin_arroba(self):
        """Probar email sin @"""
        validador = ValidadorEmail()
        resultado = validador.validar("testexample.com")

        assert resultado["valido"] is False
        assert "formato" in resultado["error"].lower()

    def test_email_vacio(self):
        """Probar email vacío"""
        validador = ValidadorEmail()
        resultado = validador.validar("")

        assert resultado["valido"] is False
        assert "requerido" in resultado["error"].lower()


class TestValidadorEdad:
    """Pruebas para ValidadorEdad"""

    def test_edad_valida(self):
        """Probar edad válida"""
        validador = ValidadorEdad()
        resultado = validador.validar("25")

        assert resultado["valido"] is True
        assert resultado["edad"] == 25

    def test_edad_menor_18(self):
        """Probar edad menor a 18"""
        validador = ValidadorEdad()
        resultado = validador.validar("16")

        assert resultado["valido"] is False
        assert "menor" in resultado["error"].lower()

    def test_edad_mayor_100(self):
        """Probar edad mayor a 100"""
        validador = ValidadorEdad()
        resultado = validador.validar("120")

        assert resultado["valido"] is False
        assert "mayor" in resultado["error"].lower()

    def test_edad_negativa(self):
        """Probar edad negativa"""
        validador = ValidadorEdad()
        resultado = validador.validar("-5")

        assert resultado["valido"] is False
        assert "negativo" in resultado["error"].lower()


class TestValidadorCoherenciaFinanciera:
    """Pruebas para ValidadorCoherenciaFinanciera"""

    def test_coherencia_valida(self):
        """Probar coherencia financiera válida"""
        validador = ValidadorCoherenciaFinanciera()
        datos = {
            "monto_total": 50000,
            "cuota_inicial": 5000,
            "monto_financiado": 45000,
            "numero_amortizaciones": 24,
            "monto_cuota": 2000
        }
        resultado = validador.validar(datos)

        assert resultado["valido"] is True

    def test_coherencia_invalida_montos(self):
        """Probar coherencia inválida en montos"""
        validador = ValidadorCoherenciaFinanciera()
        datos = {
            "monto_total": 50000,
            "cuota_inicial": 5000,
            "monto_financiado": 60000,  # Mayor que monto_total - cuota_inicial
            "numero_amortizaciones": 24,
            "monto_cuota": 2000
        }
        resultado = validador.validar(datos)

        assert resultado["valido"] is False
        assert "coherencia" in resultado["error"].lower()

    def test_coherencia_invalida_cuotas(self):
        """Probar coherencia inválida en cuotas"""
        validador = ValidadorCoherenciaFinanciera()
        datos = {
            "monto_total": 50000,
            "cuota_inicial": 5000,
            "monto_financiado": 45000,
            "numero_amortizaciones": 24,
            "monto_cuota": 1000  # Muy bajo para el monto financiado
        }
        resultado = validador.validar(datos)

        assert resultado["valido"] is False
        assert "cuota" in resultado["error"].lower()


class TestValidadorDuplicados:
    """Pruebas para ValidadorDuplicados"""

    def test_duplicado_detectado(self):
        """Probar detección de duplicado"""
        validador = ValidadorDuplicados()
        datos_existentes = [
            {"cedula": "V12345678", "email": "test@example.com"},
            {"cedula": "V87654321", "email": "other@example.com"}
        ]
        datos_nuevos = {"cedula": "V12345678", "email": "new@example.com"}

        resultado = validador.validar(datos_nuevos, datos_existentes)

        assert resultado["valido"] is False
        assert "duplicado" in resultado["error"].lower()
        assert resultado["duplicados_encontrados"] == ["cedula"]

    def test_sin_duplicados(self):
        """Probar sin duplicados"""
        validador = ValidadorDuplicados()
        datos_existentes = [
            {"cedula": "V12345678", "email": "test@example.com"}
        ]
        datos_nuevos = {"cedula": "V87654321", "email": "new@example.com"}

        resultado = validador.validar(datos_nuevos, datos_existentes)

        assert resultado["valido"] is True
        assert resultado["duplicados_encontrados"] == []
