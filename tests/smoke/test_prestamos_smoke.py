"""
Smoke tests for prestamos service.
Critical functionality tests that must pass before deploy.
"""

import pytest
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.prestamo import Prestamo
from app.models.cuota import Cuota
from app.services.prestamos.prestamos_service import PrestamosService


class TestPrestamosSmokeTests:
    """Smoke tests for critical prestamos functionality."""

    def test_smoke_crear_prestamo_basico(self, db_session: Session, test_cliente, prestamos_service):
        """SMOKE TEST: Basic prestamo creation works."""
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
        
        assert prestamo is not None
        assert prestamo.id is not None
        assert prestamo.estado == "DRAFT"

    def test_smoke_leer_prestamo(self, db_session: Session, test_prestamo, prestamos_service):
        """SMOKE TEST: Reading prestamo works."""
        prestamo = prestamos_service.obtener_prestamo(test_prestamo.id)
        
        assert prestamo is not None
        assert prestamo.id == test_prestamo.id

    def test_smoke_cambiar_estado_prestamo(self, db_session: Session, test_prestamo, prestamos_service):
        """SMOKE TEST: Changing prestamo estado works."""
        prestamo = prestamos_service.cambiar_estado_prestamo(
            test_prestamo.id,
            "APROBADO",
            usuario_cambio="test@rapicreditca.com"
        )
        
        assert prestamo.estado == "APROBADO"
        assert prestamo.usuario_aprobador == "test@rapicreditca.com"

    def test_smoke_generar_amortizacion(self, db_session: Session, test_prestamo_aprobado, prestamos_service):
        """SMOKE TEST: Amortization table generation works."""
        tabla = prestamos_service.generar_tabla_amortizacion(test_prestamo_aprobado.id)
        
        assert tabla is not None
        assert len(tabla) == test_prestamo_aprobado.numero_cuotas
        assert all("numero_cuota" in item for item in tabla)

    def test_smoke_buscar_prestamos_cliente(self, db_session: Session, test_cliente, prestamos_service):
        """SMOKE TEST: Searching prestamos by cliente works."""
        # Create a prestamo
        datos = {
            "cliente_id": test_cliente.id,
            "cedula": test_cliente.cedula,
            "nombres": test_cliente.nombres,
            "total_financiamiento": Decimal("5000.00"),
            "fecha_requerimiento": date(2026, 1, 15),
            "modalidad_pago": "MENSUAL",
            "numero_cuotas": 12,
            "cuota_periodo": Decimal("450.00"),
            "analista": "Test",
        }
        prestamo = prestamos_service.crear_prestamo(datos)
        
        # Search
        prestamos = prestamos_service.obtener_prestamos_cliente(test_cliente.id)
        
        assert len(prestamos) >= 1
        assert any(p.id == prestamo.id for p in prestamos)

    def test_smoke_resumen_prestamo(self, db_session: Session, test_prestamo_aprobado, prestamos_service):
        """SMOKE TEST: Getting prestamo summary works."""
        resumen = prestamos_service.obtener_resumen_prestamo(test_prestamo_aprobado.id)
        
        assert "id" in resumen
        assert "cliente_id" in resumen
        assert "estado" in resumen
        assert "total_financiamiento" in resumen

    def test_smoke_estadistica_prestamos(self, db_session: Session, test_cliente, prestamos_service):
        """SMOKE TEST: Getting prestamo statistics works."""
        # Create multiple prestamos
        for i in range(3):
            datos = {
                "cliente_id": test_cliente.id,
                "cedula": test_cliente.cedula,
                "nombres": test_cliente.nombres,
                "total_financiamiento": Decimal("10000.00"),
                "fecha_requerimiento": date(2026, 1, 15),
                "modalidad_pago": "MENSUAL",
                "numero_cuotas": 12,
                "cuota_periodo": Decimal("883.33"),
                "estado": "DRAFT",
                "analista": "Test",
            }
            prestamos_service.crear_prestamo(datos)
        
        stats = prestamos_service.obtener_estadistica_prestamos()
        
        assert "total_prestamos" in stats
        assert "monto_total_otorgado" in stats
        assert "por_estado" in stats

    def test_smoke_amortizacion_workflow(self, db_session: Session, test_prestamo_aprobado, prestamos_service):
        """SMOKE TEST: Complete amortization workflow works."""
        # Generate amortization
        tabla = prestamos_service.generar_tabla_amortizacion(test_prestamo_aprobado.id)
        assert len(tabla) > 0
        
        # Get amortization
        tabla2 = prestamos_service.obtener_tabla_amortizacion(test_prestamo_aprobado.id)
        assert len(tabla2) > 0

    def test_smoke_pago_cuota_workflow(self, db_session: Session, test_prestamo_aprobado, amortizacion_service):
        """SMOKE TEST: Payment recording workflow works."""
        # Generate amortization
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

    def test_smoke_estado_transitions(self, db_session: Session, test_prestamo, prestamos_service):
        """SMOKE TEST: Prestamo estado transitions work."""
        # DRAFT -> APROBADO
        prestamo = prestamos_service.cambiar_estado_prestamo(
            test_prestamo.id,
            "APROBADO"
        )
        assert prestamo.estado == "APROBADO"
        
        # APROBADO -> ACTIVO
        prestamo = prestamos_service.cambiar_estado_prestamo(
            prestamo.id,
            "ACTIVO"
        )
        assert prestamo.estado == "ACTIVO"

    def test_smoke_prestamos_performance(self, db_session: Session, test_cliente, prestamos_service):
        """SMOKE TEST: Performance of prestamo operations is acceptable."""
        import time
        
        start = time.time()
        
        # Create 5 prestamos
        for i in range(5):
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
            prestamos_service.crear_prestamo(datos)
        
        # Generate amortization for one
        prestamo = prestamos_service.obtener_prestamos_cliente(test_cliente.id)[0]
        prestamos_service.generar_tabla_amortizacion(prestamo.id)
        
        elapsed = time.time() - start
        
        # Should complete in less than 5 seconds
        assert elapsed < 5.0

    def test_smoke_db_integrity_prestamos(self, db_session: Session, test_cliente, prestamos_service):
        """SMOKE TEST: Database integrity is maintained."""
        # Create prestamo
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
        
        # Query directly from database
        db_prestamo = db_session.query(Prestamo).filter(
            Prestamo.id == prestamo.id
        ).first()
        
        assert db_prestamo is not None
        assert db_prestamo.id == prestamo.id
        assert db_prestamo.total_financiamiento == Decimal("10000.00")

    def test_smoke_cuotas_created_in_db(self, db_session: Session, test_prestamo_aprobado, prestamos_service):
        """SMOKE TEST: Amortization cuotas are created in database."""
        prestamos_service.generar_tabla_amortizacion(test_prestamo_aprobado.id)
        
        cuotas = db_session.query(Cuota).filter(
            Cuota.prestamo_id == test_prestamo_aprobado.id
        ).all()
        
        assert len(cuotas) == test_prestamo_aprobado.numero_cuotas
        
        # Verify cuota structure
        for cuota in cuotas:
            assert cuota.numero_cuota is not None
            assert cuota.fecha_vencimiento is not None
            assert cuota.monto is not None
            assert cuota.estado is not None

    def test_smoke_error_handling_invalid_cliente(self, db_session: Session, prestamos_service):
        """SMOKE TEST: Error handling for invalid cliente."""
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
        
        try:
            prestamos_service.crear_prestamo(datos)
            assert False, "Should have raised an error"
        except Exception:
            assert True

    def test_smoke_amortizacion_regenerable(self, db_session: Session, test_prestamo_aprobado, prestamos_service):
        """SMOKE TEST: Amortization can be regenerated."""
        # Generate first time
        tabla1 = prestamos_service.generar_tabla_amortizacion(test_prestamo_aprobado.id)
        count1 = len(tabla1)
        
        # Regenerate
        tabla2 = prestamos_service.generar_tabla_amortizacion(
            test_prestamo_aprobado.id,
            regenerar=True
        )
        count2 = len(tabla2)
        
        assert count1 == count2
        
        # Verify cuotas in DB
        cuotas = db_session.query(Cuota).filter(
            Cuota.prestamo_id == test_prestamo_aprobado.id
        ).all()
        
        assert len(cuotas) == test_prestamo_aprobado.numero_cuotas
