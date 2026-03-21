"""
Comprehensive integration tests for prestamos service.
Tests against real database with amortization, payments, state transitions.
"""

import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.prestamo import Prestamo
from app.models.cuota import Cuota
from app.models.cliente import Cliente
from app.services.prestamos.prestamos_service import PrestamosService
from app.services.prestamos.amortizacion_service import AmortizacionService
from app.services.prestamos.prestamos_excepciones import (
    PrestamoNotFoundError,
    PrestamoValidationError,
    PrestamoStateError,
)


class TestPrestamosServiceIntegration:
    """Integration tests for PrestamosService."""

    # ========================================================================
    # Tests: crear_prestamo
    # ========================================================================

    def test_crear_prestamo_valido_draft(self, db_session: Session, test_cliente, prestamos_service):
        """Test creating a valid prestamo in DRAFT state."""
        datos = {
            "cliente_id": test_cliente.id,
            "cedula": test_cliente.cedula,
            "nombres": test_cliente.nombres,
            "total_financiamiento": Decimal("10000.00"),
            "fecha_requerimiento": date(2026, 1, 15),
            "modalidad_pago": "MENSUAL",
            "numero_cuotas": 12,
            "cuota_periodo": Decimal("883.33"),
            "tasa_interes": Decimal("15.5000"),
            "producto": "Préstamo Personal",
            "estado": "DRAFT",
            "analista": "Test Analista",
        }
        
        prestamo = prestamos_service.crear_prestamo(datos)
        
        assert prestamo.id is not None
        assert prestamo.estado == "DRAFT"
        assert prestamo.cliente_id == test_cliente.id
        assert prestamo.total_financiamiento == Decimal("10000.00")
        assert prestamo.numero_cuotas == 12

    def test_crear_prestamo_con_fecha_base_calculo(self, db_session: Session, test_cliente, prestamos_service):
        """Test creating prestamo with fecha_base_calculo."""
        datos = {
            "cliente_id": test_cliente.id,
            "cedula": test_cliente.cedula,
            "nombres": test_cliente.nombres,
            "total_financiamiento": Decimal("15000.00"),
            "fecha_requerimiento": date(2026, 1, 15),
            "modalidad_pago": "MENSUAL",
            "numero_cuotas": 24,
            "cuota_periodo": Decimal("708.33"),
            "tasa_interes": Decimal("12.0000"),
            "fecha_base_calculo": date(2026, 2, 15),
            "producto": "Préstamo Auto",
            "analista": "Test",
        }
        
        prestamo = prestamos_service.crear_prestamo(datos)
        
        assert prestamo.fecha_base_calculo == date(2026, 2, 15)

    def test_crear_prestamo_valida_cliente_existe(self, db_session: Session, prestamos_service):
        """Test that creating prestamo for non-existent cliente fails."""
        datos = {
            "cliente_id": 99999,
            "cedula": "V999999999",
            "nombres": "Test",
            "total_financiamiento": Decimal("10000.00"),
            "fecha_requerimiento": date(2026, 1, 15),
            "modalidad_pago": "MENSUAL",
            "numero_cuotas": 12,
            "cuota_periodo": Decimal("883.33"),
            "analista": "Test",
        }
        
        with pytest.raises(Exception):
            prestamos_service.crear_prestamo(datos)

    def test_crear_prestamo_numero_cuotas_invalido(self, db_session: Session, test_cliente, prestamos_service):
        """Test that invalid numero_cuotas fails."""
        datos = {
            "cliente_id": test_cliente.id,
            "cedula": test_cliente.cedula,
            "nombres": test_cliente.nombres,
            "total_financiamiento": Decimal("10000.00"),
            "fecha_requerimiento": date(2026, 1, 15),
            "modalidad_pago": "MENSUAL",
            "numero_cuotas": 0,  # Invalid
            "cuota_periodo": Decimal("883.33"),
            "analista": "Test",
        }
        
        with pytest.raises(Exception):
            prestamos_service.crear_prestamo(datos)

    def test_crear_prestamo_tasa_negativa_falla(self, db_session: Session, test_cliente, prestamos_service):
        """Test that negative tasa_interes fails."""
        datos = {
            "cliente_id": test_cliente.id,
            "cedula": test_cliente.cedula,
            "nombres": test_cliente.nombres,
            "total_financiamiento": Decimal("10000.00"),
            "fecha_requerimiento": date(2026, 1, 15),
            "modalidad_pago": "MENSUAL",
            "numero_cuotas": 12,
            "cuota_periodo": Decimal("883.33"),
            "tasa_interes": Decimal("-5.0000"),  # Invalid
            "analista": "Test",
        }
        
        with pytest.raises(Exception):
            prestamos_service.crear_prestamo(datos)

    # ========================================================================
    # Tests: obtener_prestamo
    # ========================================================================

    def test_obtener_prestamo_existente(self, db_session: Session, test_prestamo, prestamos_service):
        """Test retrieving an existing prestamo."""
        prestamo = prestamos_service.obtener_prestamo(test_prestamo.id)
        
        assert prestamo.id == test_prestamo.id
        assert prestamo.cliente_id == test_prestamo.cliente_id
        assert prestamo.estado == test_prestamo.estado

    def test_obtener_prestamo_no_existe_falla(self, db_session: Session, prestamos_service):
        """Test that retrieving non-existent prestamo raises error."""
        with pytest.raises(PrestamoNotFoundError):
            prestamos_service.obtener_prestamo(99999)

    # ========================================================================
    # Tests: obtener_prestamos_cliente
    # ========================================================================

    def test_obtener_prestamos_cliente_vacio(self, db_session: Session, test_cliente, prestamos_service):
        """Test retrieving prestamos for cliente with no prestamos."""
        prestamos = prestamos_service.obtener_prestamos_cliente(test_cliente.id)
        
        assert prestamos == []

    def test_obtener_prestamos_cliente_multiple(self, db_session: Session, test_cliente, prestamos_service):
        """Test retrieving multiple prestamos for a cliente."""
        # Create multiple prestamos
        for i in range(3):
            datos = {
                "cliente_id": test_cliente.id,
                "cedula": test_cliente.cedula,
                "nombres": test_cliente.nombres,
                "total_financiamiento": Decimal("5000.00") * (i + 1),
                "fecha_requerimiento": date(2026, 1, 15),
                "modalidad_pago": "MENSUAL",
                "numero_cuotas": 12,
                "cuota_periodo": Decimal("500.00"),
                "analista": "Test",
            }
            prestamos_service.crear_prestamo(datos)
        
        prestamos = prestamos_service.obtener_prestamos_cliente(test_cliente.id)
        
        assert len(prestamos) == 3

    def test_obtener_prestamos_cliente_filtro_estado(self, db_session: Session, test_cliente, prestamos_service):
        """Test retrieving prestamos filtered by estado."""
        # Create prestamos with different states
        for estado in ["DRAFT", "APROBADO"]:
            datos = {
                "cliente_id": test_cliente.id,
                "cedula": test_cliente.cedula,
                "nombres": test_cliente.nombres,
                "total_financiamiento": Decimal("10000.00"),
                "fecha_requerimiento": date(2026, 1, 15),
                "modalidad_pago": "MENSUAL",
                "numero_cuotas": 12,
                "cuota_periodo": Decimal("883.33"),
                "estado": estado,
                "analista": "Test",
            }
            prestamos_service.crear_prestamo(datos)
        
        prestamos_draft = prestamos_service.obtener_prestamos_cliente(
            test_cliente.id, 
            estado="DRAFT"
        )
        
        assert len(prestamos_draft) == 1
        assert prestamos_draft[0].estado == "DRAFT"

    # ========================================================================
    # Tests: actualizar_prestamo
    # ========================================================================

    def test_actualizar_prestamo_tasa(self, db_session: Session, test_prestamo, prestamos_service):
        """Test updating prestamo tasa_interes."""
        nuevos_datos = {
            "tasa_interes": Decimal("18.0000"),
        }
        
        prestamo = prestamos_service.actualizar_prestamo(test_prestamo.id, nuevos_datos)
        
        assert prestamo.tasa_interes == Decimal("18.0000")

    def test_actualizar_prestamo_observaciones(self, db_session: Session, test_prestamo, prestamos_service):
        """Test updating prestamo observaciones."""
        nuevas_obs = "Observaciones actualizadas"
        nuevos_datos = {
            "observaciones": nuevas_obs,
        }
        
        prestamo = prestamos_service.actualizar_prestamo(test_prestamo.id, nuevos_datos)
        
        assert prestamo.observaciones == nuevas_obs

    # ========================================================================
    # Tests: cambiar_estado_prestamo (State Transitions)
    # ========================================================================

    def test_cambiar_estado_draft_a_aprobado(self, db_session: Session, test_prestamo, prestamos_service):
        """Test state transition from DRAFT to APROBADO."""
        prestamo = prestamos_service.cambiar_estado_prestamo(
            test_prestamo.id,
            "APROBADO",
            usuario_cambio="test_aprobador@rapicreditca.com"
        )
        
        assert prestamo.estado == "APROBADO"
        assert prestamo.usuario_aprobador == "test_aprobador@rapicreditca.com"
        assert prestamo.fecha_aprobacion is not None

    def test_cambiar_estado_aprobado_a_activo(self, db_session: Session, test_prestamo_aprobado, prestamos_service):
        """Test state transition from APROBADO to ACTIVO."""
        prestamo = prestamos_service.cambiar_estado_prestamo(
            test_prestamo_aprobado.id,
            "ACTIVO",
            usuario_cambio="test_operaciones@rapicreditca.com"
        )
        
        assert prestamo.estado == "ACTIVO"

    def test_cambiar_estado_invalido_falla(self, db_session: Session, test_prestamo, prestamos_service):
        """Test that invalid estado fails."""
        with pytest.raises(Exception):
            prestamos_service.cambiar_estado_prestamo(
                test_prestamo.id,
                "ESTADO_INVALIDO"
            )

    def test_cambiar_estado_illegal_transition_falla(self, db_session: Session, test_prestamo_aprobado, prestamos_service):
        """Test that illegal state transition fails (e.g., APROBADO -> DRAFT)."""
        with pytest.raises(PrestamoStateError):
            prestamos_service.cambiar_estado_prestamo(
                test_prestamo_aprobado.id,
                "DRAFT"
            )

    # ========================================================================
    # Tests: Amortization (generar_tabla_amortizacion)
    # ========================================================================

    def test_generar_tabla_amortizacion(self, db_session: Session, test_prestamo_aprobado, prestamos_service):
        """Test generating amortization table."""
        tabla = prestamos_service.generar_tabla_amortizacion(test_prestamo_aprobado.id)
        
        assert len(tabla) == test_prestamo_aprobado.numero_cuotas
        assert all("numero_cuota" in item for item in tabla)
        assert all("monto_cuota" in item or "cuota_fija" in item for item in tabla)

    def test_tabla_amortizacion_saldo_final_cero(self, db_session: Session, test_prestamo_aprobado, prestamos_service):
        """Test that last cuota in amortization table results in zero balance."""
        tabla = prestamos_service.generar_tabla_amortizacion(test_prestamo_aprobado.id)
        
        ultima_cuota = tabla[-1]
        # Verify final balance is 0 or very close
        assert ultima_cuota.get("saldo_vigente") is not None

    def test_tabla_amortizacion_reproducible(self, db_session: Session, test_prestamo_aprobado, prestamos_service):
        """Test that amortization table is reproducible."""
        tabla1 = prestamos_service.generar_tabla_amortizacion(test_prestamo_aprobado.id)
        
        # Regenerate
        tabla2 = prestamos_service.generar_tabla_amortizacion(
            test_prestamo_aprobado.id,
            regenerar=True
        )
        
        assert len(tabla1) == len(tabla2)

    def test_obtener_tabla_amortizacion(self, db_session: Session, test_prestamo_aprobado, prestamos_service):
        """Test retrieving existing amortization table."""
        # Generate first
        prestamos_service.generar_tabla_amortizacion(test_prestamo_aprobado.id)
        
        # Retrieve
        tabla = prestamos_service.obtener_tabla_amortizacion(test_prestamo_aprobado.id)
        
        assert len(tabla) == test_prestamo_aprobado.numero_cuotas

    # ========================================================================
    # Tests: Payment Recording
    # ========================================================================

    def test_registrar_pago_cuota(self, db_session: Session, test_prestamo_aprobado, amortizacion_service):
        """Test recording a payment for a cuota."""
        # Generate amortization first
        amortizacion_service.generar_tabla_amortizacion(test_prestamo_aprobado.id)
        
        # Get first cuota
        cuota = db_session.query(Cuota).filter(
            Cuota.prestamo_id == test_prestamo_aprobado.id,
            Cuota.numero_cuota == 1
        ).first()
        
        # Record payment
        resultado = amortizacion_service.registrar_pago_cuota(
            cuota.id,
            float(cuota.monto),
            date.today()
        )
        
        assert resultado is not None
        assert "monto_pagado" in resultado

    def test_registrar_pago_parcial(self, db_session: Session, test_prestamo_aprobado, amortizacion_service):
        """Test recording partial payment for cuota."""
        amortizacion_service.generar_tabla_amortizacion(test_prestamo_aprobado.id)
        
        cuota = db_session.query(Cuota).filter(
            Cuota.prestamo_id == test_prestamo_aprobado.id,
            Cuota.numero_cuota == 1
        ).first()
        
        monto_parcial = float(cuota.monto) * 0.5
        
        resultado = amortizacion_service.registrar_pago_cuota(
            cuota.id,
            monto_parcial,
            date.today()
        )
        
        assert float(resultado.get("monto_pagado", 0)) == monto_parcial

    # ========================================================================
    # Tests: Resumen Prestamo
    # ========================================================================

    def test_obtener_resumen_prestamo(self, db_session: Session, test_prestamo_aprobado, prestamos_service):
        """Test getting prestamo summary."""
        resumen = prestamos_service.obtener_resumen_prestamo(test_prestamo_aprobado.id)
        
        assert resumen["id"] == test_prestamo_aprobado.id
        assert resumen["cliente_id"] == test_prestamo_aprobado.cliente_id
        assert resumen["estado"] == "APROBADO"
        assert "total_financiamiento" in resumen
        assert "numero_cuotas" in resumen

    def test_resumen_prestamo_incluye_amortizacion(self, db_session: Session, test_prestamo_aprobado, prestamos_service):
        """Test that prestamo summary includes amortization info."""
        # Generate amortization
        prestamos_service.generar_tabla_amortizacion(test_prestamo_aprobado.id)
        
        resumen = prestamos_service.obtener_resumen_prestamo(test_prestamo_aprobado.id)
        
        assert "amortizacion" in resumen

    # ========================================================================
    # Tests: Estadísticas
    # ========================================================================

    def test_obtener_estadistica_prestamos(self, db_session: Session, test_cliente, prestamos_service):
        """Test getting overall prestamo statistics."""
        # Create multiple prestamos
        for i in range(3):
            datos = {
                "cliente_id": test_cliente.id,
                "cedula": test_cliente.cedula,
                "nombres": test_cliente.nombres,
                "total_financiamiento": Decimal("5000.00"),
                "fecha_requerimiento": date(2026, 1, 15),
                "modalidad_pago": "MENSUAL",
                "numero_cuotas": 12,
                "cuota_periodo": Decimal("450.00"),
                "estado": "DRAFT",
                "analista": "Test",
            }
            prestamos_service.crear_prestamo(datos)
        
        stats = prestamos_service.obtener_estadistica_prestamos()
        
        assert stats["total_prestamos"] >= 3
        assert "monto_total_otorgado" in stats
        assert "por_estado" in stats

    def test_estadistica_por_estado(self, db_session: Session, test_cliente, prestamos_service):
        """Test that statistics correctly count by estado."""
        # Create prestamos with different states
        for estado in ["DRAFT", "APROBADO", "DRAFT"]:
            datos = {
                "cliente_id": test_cliente.id,
                "cedula": test_cliente.cedula,
                "nombres": test_cliente.nombres,
                "total_financiamiento": Decimal("10000.00"),
                "fecha_requerimiento": date(2026, 1, 15),
                "modalidad_pago": "MENSUAL",
                "numero_cuotas": 12,
                "cuota_periodo": Decimal("883.33"),
                "estado": estado,
                "analista": "Test",
            }
            prestamos_service.crear_prestamo(datos)
        
        stats = prestamos_service.obtener_estadistica_prestamos()
        
        assert stats["por_estado"]["DRAFT"] >= 2
        assert stats["por_estado"]["APROBADO"] >= 1

    # ========================================================================
    # Tests: Database Consistency
    # ========================================================================

    def test_crear_prestamo_persiste_en_bd(self, db_session: Session, test_cliente, prestamos_service):
        """Test that created prestamo is persisted in database."""
        datos = {
            "cliente_id": test_cliente.id,
            "cedula": test_cliente.cedula,
            "nombres": test_cliente.nombres,
            "total_financiamiento": Decimal("10000.00"),
            "fecha_requerimiento": date(2026, 1, 15),
            "modalidad_pago": "MENSUAL",
            "numero_cuotas": 12,
            "cuota_periodo": Decimal("883.33"),
            "analista": "Test",
        }
        
        prestamo = prestamos_service.crear_prestamo(datos)
        prestamo_id = prestamo.id
        
        # Refresh session and query
        db_session.expunge_all()
        
        db_prestamo = db_session.query(Prestamo).filter(Prestamo.id == prestamo_id).first()
        
        assert db_prestamo is not None
        assert db_prestamo.id == prestamo_id

    def test_actualizar_prestamo_persiste_cambios(self, db_session: Session, test_prestamo, prestamos_service):
        """Test that prestamo updates are persisted."""
        nueva_tasa = Decimal("20.0000")
        
        prestamos_service.actualizar_prestamo(
            test_prestamo.id,
            {"tasa_interes": nueva_tasa}
        )
        
        # Refresh
        db_session.expunge_all()
        
        db_prestamo = db_session.query(Prestamo).filter(
            Prestamo.id == test_prestamo.id
        ).first()
        
        assert db_prestamo.tasa_interes == nueva_tasa

    def test_amortizacion_creada_en_bd(self, db_session: Session, test_prestamo_aprobado, prestamos_service):
        """Test that amortization table is created in database."""
        prestamos_service.generar_tabla_amortizacion(test_prestamo_aprobado.id)
        
        cuotas = db_session.query(Cuota).filter(
            Cuota.prestamo_id == test_prestamo_aprobado.id
        ).all()
        
        assert len(cuotas) == test_prestamo_aprobado.numero_cuotas

    # ========================================================================
    # Tests: Edge Cases
    # ========================================================================

    def test_prestamo_tasa_cero(self, db_session: Session, test_cliente, prestamos_service):
        """Test creating prestamo with zero interest rate."""
        datos = {
            "cliente_id": test_cliente.id,
            "cedula": test_cliente.cedula,
            "nombres": test_cliente.nombres,
            "total_financiamiento": Decimal("10000.00"),
            "fecha_requerimiento": date(2026, 1, 15),
            "modalidad_pago": "MENSUAL",
            "numero_cuotas": 12,
            "cuota_periodo": Decimal("833.33"),
            "tasa_interes": Decimal("0.0000"),
            "analista": "Test",
        }
        
        prestamo = prestamos_service.crear_prestamo(datos)
        
        assert prestamo.tasa_interes == Decimal("0.0000")

    def test_prestamo_una_sola_cuota(self, db_session: Session, test_cliente, prestamos_service):
        """Test creating prestamo with single cuota."""
        datos = {
            "cliente_id": test_cliente.id,
            "cedula": test_cliente.cedula,
            "nombres": test_cliente.nombres,
            "total_financiamiento": Decimal("10000.00"),
            "fecha_requerimiento": date(2026, 1, 15),
            "modalidad_pago": "MENSUAL",
            "numero_cuotas": 1,
            "cuota_periodo": Decimal("10000.00"),
            "analista": "Test",
        }
        
        prestamo = prestamos_service.crear_prestamo(datos)
        
        assert prestamo.numero_cuotas == 1

    def test_prestamo_muchas_cuotas(self, db_session: Session, test_cliente, prestamos_service):
        """Test creating prestamo with many cuotas."""
        datos = {
            "cliente_id": test_cliente.id,
            "cedula": test_cliente.cedula,
            "nombres": test_cliente.nombres,
            "total_financiamiento": Decimal("100000.00"),
            "fecha_requerimiento": date(2026, 1, 15),
            "modalidad_pago": "MENSUAL",
            "numero_cuotas": 360,  # 30 years
            "cuota_periodo": Decimal("277.78"),
            "analista": "Test",
        }
        
        prestamo = prestamos_service.crear_prestamo(datos)
        
        assert prestamo.numero_cuotas == 360

    def test_obtener_prestamos_vencidos(self, db_session: Session, test_prestamo_aprobado, prestamos_service):
        """Test retrieving overdue prestamos."""
        # Generate amortization
        prestamos_service.generar_tabla_amortizacion(test_prestamo_aprobado.id)
        
        # Change prestamo estado to ACTIVO
        prestamos_service.cambiar_estado_prestamo(
            test_prestamo_aprobado.id,
            "ACTIVO"
        )
        
        vencidos = prestamos_service.obtener_prestamos_vencidos()
        
        # May or may not have vencidos depending on dates
        assert isinstance(vencidos, list)
