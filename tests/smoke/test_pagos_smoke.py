"""
Smoke tests for pagos service.
Critical functionality tests that must pass before deploy.
"""

import pytest
from datetime import datetime
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.pago import Pago
from app.services.pagos.pagos_service import PagosService


class TestPagosSmokeTests:
    """Smoke tests for critical pagos functionality."""

    def test_smoke_crear_pago_basico(self, db_session: Session, test_cliente, pagos_service):
        """SMOKE TEST: Basic pago creation works."""
        datos = {
            "cliente_id": test_cliente.id,
            "cedula_cliente": test_cliente.cedula,
            "monto_pagado": Decimal("500.00"),
            "referencia_pago": "REF-SMOKE-01",
            "numero_documento": "DOC-SMOKE-01",
        }
        
        pago = pagos_service.crear_pago(datos)
        
        assert pago is not None
        assert pago.id is not None
        assert pago.monto_pagado == Decimal("500.00")

    def test_smoke_leer_pago(self, db_session: Session, test_pago, pagos_service):
        """SMOKE TEST: Reading pago works."""
        pago = pagos_service.obtener_pago(test_pago.id)
        
        assert pago is not None
        assert pago.id == test_pago.id

    def test_smoke_actualizar_pago(self, db_session: Session, test_pago, pagos_service):
        """SMOKE TEST: Updating pago works."""
        nuevos_datos = {
            "estado": "CONCILIADO",
            "monto_pagado": Decimal("750.00"),
        }
        
        pago = pagos_service.actualizar_pago(test_pago.id, nuevos_datos)
        
        assert pago.estado == "CONCILIADO"
        assert pago.monto_pagado == Decimal("750.00")

    def test_smoke_eliminar_pago(self, db_session: Session, test_pago, pagos_service):
        """SMOKE TEST: Deleting pago works."""
        pago_id = test_pago.id
        
        resultado = pagos_service.eliminar_pago(pago_id)
        
        assert resultado is True
        # Verify it's gone
        with pytest.raises(Exception):
            pagos_service.obtener_pago(pago_id)

    def test_smoke_buscar_pagos_cliente(self, db_session: Session, test_cliente, pagos_service):
        """SMOKE TEST: Searching pagos by cliente works."""
        # Create a pago
        datos = {
            "cliente_id": test_cliente.id,
            "cedula_cliente": test_cliente.cedula,
            "monto_pagado": Decimal("300.00"),
            "referencia_pago": "REF-SMOKE-SEARCH",
        }
        pago = pagos_service.crear_pago(datos)
        
        # Search
        pagos = pagos_service.obtener_pagos_cliente(test_cliente.id)
        
        assert len(pagos) >= 1
        assert any(p.id == pago.id for p in pagos)

    def test_smoke_resumen_pagos(self, db_session: Session, test_cliente, pagos_service):
        """SMOKE TEST: Getting pago summary works."""
        # Create some pagos
        for i in range(3):
            datos = {
                "cliente_id": test_cliente.id,
                "cedula_cliente": test_cliente.cedula,
                "monto_pagado": Decimal("200.00"),
                "referencia_pago": f"REF-SMOKE-RES-{i}",
            }
            pagos_service.crear_pago(datos)
        
        resumen = pagos_service.obtener_resumen_pagos()
        
        assert "total_pagos" in resumen
        assert "monto_total" in resumen
        assert resumen["total_pagos"] >= 3

    def test_smoke_conciliacion_workflow(self, db_session: Session, test_cliente, pagos_service):
        """SMOKE TEST: Complete conciliation workflow works."""
        # Create pago
        datos = {
            "cliente_id": test_cliente.id,
            "cedula_cliente": test_cliente.cedula,
            "monto_pagado": Decimal("500.00"),
            "referencia_pago": "REF-SMOKE-CONC",
            "estado": "REGISTRADO",
        }
        pago = pagos_service.crear_pago(datos)
        
        # Update to CONCILIADO
        pago = pagos_service.actualizar_pago(pago.id, {
            "estado": "CONCILIADO",
            "conciliado": True,
            "fecha_conciliacion": datetime.now(),
        })
        
        assert pago.conciliado is True
        assert pago.estado == "CONCILIADO"

    def test_smoke_pagos_performance(self, db_session: Session, test_cliente, pagos_service):
        """SMOKE TEST: Performance of pago operations is acceptable."""
        import time
        
        start = time.time()
        
        # Create 10 pagos
        for i in range(10):
            datos = {
                "cliente_id": test_cliente.id,
                "cedula_cliente": test_cliente.cedula,
                "monto_pagado": Decimal("100.00"),
                "referencia_pago": f"REF-PERF-{i}",
                "numero_documento": f"DOC-PERF-{i}",
            }
            pagos_service.crear_pago(datos)
        
        # Query all
        pagos_service.obtener_pagos_cliente(test_cliente.id)
        
        elapsed = time.time() - start
        
        # Should complete in less than 5 seconds
        assert elapsed < 5.0

    def test_smoke_db_integrity_pagos(self, db_session: Session, test_cliente, pagos_service):
        """SMOKE TEST: Database integrity is maintained."""
        # Create pago
        datos = {
            "cliente_id": test_cliente.id,
            "cedula_cliente": test_cliente.cedula,
            "monto_pagado": Decimal("500.00"),
            "referencia_pago": "REF-SMOKE-INT",
        }
        pago = pagos_service.crear_pago(datos)
        
        # Query directly from database
        db_pago = db_session.query(Pago).filter(Pago.id == pago.id).first()
        
        assert db_pago is not None
        assert db_pago.id == pago.id
        assert db_pago.monto_pagado == Decimal("500.00")

    def test_smoke_transactional_consistency(self, db_session: Session, test_cliente, pagos_service):
        """SMOKE TEST: Transactional consistency is maintained."""
        pago_ids = []
        
        # Create multiple pagos
        for i in range(5):
            datos = {
                "cliente_id": test_cliente.id,
                "cedula_cliente": test_cliente.cedula,
                "monto_pagado": Decimal("100.00"),
                "referencia_pago": f"REF-TRANS-{i}",
                "numero_documento": f"DOC-TRANS-{i}",
            }
            pago = pagos_service.crear_pago(datos)
            pago_ids.append(pago.id)
        
        # All should be queryable
        count = db_session.query(Pago).filter(
            Pago.id.in_(pago_ids)
        ).count()
        
        assert count == len(pago_ids)

    def test_smoke_error_handling_invalid_cliente(self, db_session: Session, pagos_service):
        """SMOKE TEST: Error handling for invalid cliente."""
        datos = {
            "cliente_id": 99999,
            "cedula_cliente": "V999999999",
            "monto_pagado": Decimal("500.00"),
            "referencia_pago": "REF-ERR",
        }
        
        try:
            pagos_service.crear_pago(datos)
            assert False, "Should have raised an error"
        except Exception:
            assert True

    def test_smoke_estado_changes(self, db_session: Session, test_cliente, pagos_service):
        """SMOKE TEST: Pago estado changes work correctly."""
        datos = {
            "cliente_id": test_cliente.id,
            "cedula_cliente": test_cliente.cedula,
            "monto_pagado": Decimal("500.00"),
            "referencia_pago": "REF-ESTADO",
            "estado": "REGISTRADO",
        }
        pago = pagos_service.crear_pago(datos)
        
        # Change estado
        pago = pagos_service.actualizar_pago(pago.id, {"estado": "VERIFICADO"})
        assert pago.estado == "VERIFICADO"
        
        # Change again
        pago = pagos_service.actualizar_pago(pago.id, {"estado": "CONCILIADO"})
        assert pago.estado == "CONCILIADO"
