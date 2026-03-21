"""
Comprehensive integration tests for pagos service.
Tests against real database with transactions and fixtures.
"""

import pytest
from datetime import date, datetime
from decimal import Decimal
from sqlalchemy.orm import Session

from app.models.pago import Pago
from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.services.pagos.pagos_service import PagosService
from app.services.pagos.pagos_excepciones import PagoNotFoundError


class TestPagosServiceIntegration:
    """Integration tests for PagosService with real database."""

    # ========================================================================
    # Tests: crear_pago
    # ========================================================================

    def test_crear_pago_valido(self, db_session: Session, test_cliente, pagos_service):
        """Test creating a valid pago."""
        datos = {
            "cliente_id": test_cliente.id,
            "cedula_cliente": test_cliente.cedula,
            "monto_pagado": Decimal("500.00"),
            "referencia_pago": "REF-001",
            "numero_documento": "DOC-001",
            "institucion_bancaria": "Banco Test",
            "fecha_pago": datetime(2026, 3, 15),
        }
        
        pago = pagos_service.crear_pago(datos)
        
        assert pago.id is not None
        assert pago.cedula_cliente == test_cliente.cedula
        assert pago.monto_pagado == Decimal("500.00")
        assert pago.referencia_pago == "REF-001"
        assert pago.numero_documento == "DOC-001"
        assert db_session.query(Pago).filter(Pago.id == pago.id).first() is not None

    def test_crear_pago_con_prestamo_id(self, db_session: Session, test_cliente, test_prestamo, pagos_service):
        """Test creating a pago linked to a prestamo."""
        datos = {
            "cliente_id": test_cliente.id,
            "cedula_cliente": test_cliente.cedula,
            "prestamo_id": test_prestamo.id,
            "monto_pagado": Decimal("883.33"),
            "referencia_pago": "REF-002",
            "numero_documento": "DOC-002",
        }
        
        pago = pagos_service.crear_pago(datos)
        
        assert pago.prestamo_id == test_prestamo.id
        assert pago.monto_pagado == Decimal("883.33")

    def test_crear_pago_sin_documento_duplicado(self, db_session: Session, test_cliente, pagos_service):
        """Test that duplicate documento raises error."""
        datos = {
            "cliente_id": test_cliente.id,
            "cedula_cliente": test_cliente.cedula,
            "monto_pagado": Decimal("500.00"),
            "referencia_pago": "REF-003",
            "numero_documento": "DOC-UNICO-001",
        }
        
        # Create first pago
        pago1 = pagos_service.crear_pago(datos)
        assert pago1.id is not None
        
        # Try to create second with same documento - should fail
        datos["referencia_pago"] = "REF-004"
        with pytest.raises(Exception):  # Should raise validation error
            pagos_service.crear_pago(datos)

    def test_crear_pago_monto_negativo_falla(self, db_session: Session, test_cliente, pagos_service):
        """Test that negative monto raises error."""
        datos = {
            "cliente_id": test_cliente.id,
            "cedula_cliente": test_cliente.cedula,
            "monto_pagado": Decimal("-100.00"),
            "referencia_pago": "REF-005",
        }
        
        with pytest.raises(Exception):  # Should raise validation error
            pagos_service.crear_pago(datos)

    def test_crear_pago_cliente_no_existe_falla(self, db_session: Session, pagos_service):
        """Test that creating pago for non-existent cliente fails."""
        datos = {
            "cliente_id": 99999,
            "cedula_cliente": "V999999999",
            "monto_pagado": Decimal("500.00"),
            "referencia_pago": "REF-006",
        }
        
        with pytest.raises(Exception):  # Should raise validation error
            pagos_service.crear_pago(datos)

    # ========================================================================
    # Tests: obtener_pago
    # ========================================================================

    def test_obtener_pago_existente(self, db_session: Session, test_pago, pagos_service):
        """Test retrieving an existing pago."""
        pago = pagos_service.obtener_pago(test_pago.id)
        
        assert pago.id == test_pago.id
        assert pago.cedula_cliente == test_pago.cedula_cliente
        assert pago.monto_pagado == test_pago.monto_pagado

    def test_obtener_pago_no_existe_falla(self, db_session: Session, pagos_service):
        """Test that retrieving non-existent pago raises PagoNotFoundError."""
        with pytest.raises(PagoNotFoundError):
            pagos_service.obtener_pago(99999)

    # ========================================================================
    # Tests: actualizar_pago
    # ========================================================================

    def test_actualizar_pago_estado(self, db_session: Session, test_pago, pagos_service):
        """Test updating pago estado."""
        nuevos_datos = {
            "estado": "CONCILIADO",
        }
        
        pago = pagos_service.actualizar_pago(test_pago.id, nuevos_datos)
        
        assert pago.estado == "CONCILIADO"
        # Verify in database
        db_pago = db_session.query(Pago).filter(Pago.id == test_pago.id).first()
        assert db_pago.estado == "CONCILIADO"

    def test_actualizar_pago_monto(self, db_session: Session, test_pago, pagos_service):
        """Test updating pago monto."""
        nuevos_datos = {
            "monto_pagado": Decimal("750.00"),
        }
        
        pago = pagos_service.actualizar_pago(test_pago.id, nuevos_datos)
        
        assert pago.monto_pagado == Decimal("750.00")

    def test_actualizar_pago_notas(self, db_session: Session, test_pago, pagos_service):
        """Test updating pago notas."""
        nuevos_datos = {
            "notas": "Pago actualizado en prueba",
        }
        
        pago = pagos_service.actualizar_pago(test_pago.id, nuevos_datos)
        
        assert pago.notas == "Pago actualizado en prueba"

    def test_actualizar_pago_multiple_campos(self, db_session: Session, test_pago, pagos_service):
        """Test updating multiple pago fields at once."""
        nuevos_datos = {
            "estado": "VERIFICADO",
            "monto_pagado": Decimal("600.00"),
            "notas": "Múltiples actualizaciones",
        }
        
        pago = pagos_service.actualizar_pago(test_pago.id, nuevos_datos)
        
        assert pago.estado == "VERIFICADO"
        assert pago.monto_pagado == Decimal("600.00")
        assert pago.notas == "Múltiples actualizaciones"

    def test_actualizar_pago_no_existe_falla(self, db_session: Session, pagos_service):
        """Test that updating non-existent pago fails."""
        nuevos_datos = {"estado": "CONCILIADO"}
        
        with pytest.raises(PagoNotFoundError):
            pagos_service.actualizar_pago(99999, nuevos_datos)

    # ========================================================================
    # Tests: obtener_pagos_cliente
    # ========================================================================

    def test_obtener_pagos_cliente_vacio(self, db_session: Session, test_cliente, pagos_service):
        """Test retrieving pagos for cliente with no pagos."""
        pagos = pagos_service.obtener_pagos_cliente(test_cliente.id)
        
        assert pagos == []

    def test_obtener_pagos_cliente_multiple(self, db_session: Session, test_cliente, pagos_service):
        """Test retrieving multiple pagos for a cliente."""
        # Create multiple pagos
        for i in range(5):
            datos = {
                "cliente_id": test_cliente.id,
                "cedula_cliente": test_cliente.cedula,
                "monto_pagado": Decimal("100.00") * (i + 1),
                "referencia_pago": f"REF-{i}",
                "numero_documento": f"DOC-{i}",
            }
            pagos_service.crear_pago(datos)
        
        pagos = pagos_service.obtener_pagos_cliente(test_cliente.id)
        
        assert len(pagos) == 5
        # Verify they're ordered by fecha_pago descending
        for i in range(len(pagos) - 1):
            assert pagos[i].fecha_pago >= pagos[i + 1].fecha_pago

    def test_obtener_pagos_cliente_con_limit(self, db_session: Session, test_cliente, pagos_service):
        """Test retrieving pagos with limit."""
        # Create 10 pagos
        for i in range(10):
            datos = {
                "cliente_id": test_cliente.id,
                "cedula_cliente": test_cliente.cedula,
                "monto_pagado": Decimal("100.00"),
                "referencia_pago": f"REF-{i}",
                "numero_documento": f"DOC-{i}",
            }
            pagos_service.crear_pago(datos)
        
        pagos = pagos_service.obtener_pagos_cliente(test_cliente.id, limit=5)
        
        assert len(pagos) == 5

    def test_obtener_pagos_cliente_no_existe_falla(self, db_session: Session, pagos_service):
        """Test that retrieving pagos for non-existent cliente fails."""
        with pytest.raises(Exception):  # Should raise validation error
            pagos_service.obtener_pagos_cliente(99999)

    # ========================================================================
    # Tests: eliminar_pago
    # ========================================================================

    def test_eliminar_pago_existente(self, db_session: Session, test_pago, pagos_service):
        """Test deleting an existing pago."""
        pago_id = test_pago.id
        
        resultado = pagos_service.eliminar_pago(pago_id)
        
        assert resultado is True
        # Verify pago is gone from database
        assert db_session.query(Pago).filter(Pago.id == pago_id).first() is None

    def test_eliminar_pago_no_existe_falla(self, db_session: Session, pagos_service):
        """Test that deleting non-existent pago fails."""
        with pytest.raises(PagoNotFoundError):
            pagos_service.eliminar_pago(99999)

    # ========================================================================
    # Tests: obtener_resumen_pagos
    # ========================================================================

    def test_obtener_resumen_pagos_global(self, db_session: Session, test_cliente, pagos_service):
        """Test getting global pago summary."""
        # Create pagos for multiple clientes
        cliente2 = Cliente(
            cedula="V111111111",
            nombres="Cliente 2",
            telefono="0264",
            email="c2@test.com",
            direccion="Dir",
            fecha_nacimiento=date(1990, 1, 1),
            ocupacion="Test",
            estado="ACTIVO",
            usuario_registro="test",
            notas="Test",
        )
        db_session.add(cliente2)
        db_session.commit()

        # Add pagos
        for i in range(3):
            datos = {
                "cliente_id": test_cliente.id,
                "cedula_cliente": test_cliente.cedula,
                "monto_pagado": Decimal("500.00"),
                "referencia_pago": f"REF-{i}",
            }
            pagos_service.crear_pago(datos)

        datos2 = {
            "cliente_id": cliente2.id,
            "cedula_cliente": cliente2.cedula,
            "monto_pagado": Decimal("300.00"),
            "referencia_pago": "REF-C2",
        }
        pagos_service.crear_pago(datos2)

        resumen = pagos_service.obtener_resumen_pagos()
        
        assert resumen["total_pagos"] == 4
        assert resumen["monto_total"] == Decimal("1800.00")

    def test_obtener_resumen_pagos_por_cliente(self, db_session: Session, test_cliente, pagos_service):
        """Test getting pago summary for specific cliente."""
        # Create pagos
        for i in range(3):
            datos = {
                "cliente_id": test_cliente.id,
                "cedula_cliente": test_cliente.cedula,
                "monto_pagado": Decimal("200.00"),
                "referencia_pago": f"REF-{i}",
            }
            pagos_service.crear_pago(datos)

        resumen = pagos_service.obtener_resumen_pagos(test_cliente.id)
        
        assert resumen["total_pagos"] == 3
        assert resumen["monto_total"] == Decimal("600.00")

    def test_obtener_resumen_pagos_por_estado(self, db_session: Session, test_cliente, pagos_service):
        """Test getting pago summary grouped by estado."""
        # Create pagos with different states
        datos1 = {
            "cliente_id": test_cliente.id,
            "cedula_cliente": test_cliente.cedula,
            "monto_pagado": Decimal("500.00"),
            "referencia_pago": "REF-1",
            "estado": "PENDIENTE",
        }
        pagos_service.crear_pago(datos1)

        datos2 = {
            "cliente_id": test_cliente.id,
            "cedula_cliente": test_cliente.cedula,
            "monto_pagado": Decimal("300.00"),
            "referencia_pago": "REF-2",
            "estado": "CONCILIADO",
        }
        pagos_service.crear_pago(datos2)

        resumen = pagos_service.obtener_resumen_pagos()
        
        assert "por_estado" in resumen
        assert "PENDIENTE" in resumen["por_estado"]
        assert "CONCILIADO" in resumen["por_estado"]

    # ========================================================================
    # Tests: obtener_pagos_por_estado
    # ========================================================================

    def test_obtener_pagos_por_estado_registrado(self, db_session: Session, test_cliente, pagos_service):
        """Test retrieving pagos by estado REGISTRADO."""
        # Create pagos
        datos = {
            "cliente_id": test_cliente.id,
            "cedula_cliente": test_cliente.cedula,
            "monto_pagado": Decimal("500.00"),
            "referencia_pago": "REF-STATUS",
            "estado": "REGISTRADO",
        }
        pago = pagos_service.crear_pago(datos)

        pagos = pagos_service.obtener_pagos_por_estado("REGISTRADO")
        
        assert len(pagos) >= 1
        assert any(p.id == pago.id for p in pagos)

    def test_obtener_pagos_por_estado_conciliado(self, db_session: Session, test_cliente, pagos_service):
        """Test retrieving pagos by estado CONCILIADO."""
        datos = {
            "cliente_id": test_cliente.id,
            "cedula_cliente": test_cliente.cedula,
            "monto_pagado": Decimal("300.00"),
            "referencia_pago": "REF-CONC",
            "estado": "CONCILIADO",
        }
        pago = pagos_service.crear_pago(datos)

        pagos = pagos_service.obtener_pagos_por_estado("CONCILIADO")
        
        assert any(p.id == pago.id for p in pagos)

    # ========================================================================
    # Tests: Conciliación
    # ========================================================================

    def test_conciliar_pago(self, db_session: Session, test_pago, pagos_service):
        """Test marking a pago as conciliado."""
        datos_update = {
            "conciliado": True,
            "estado": "CONCILIADO",
        }
        
        pago = pagos_service.actualizar_pago(test_pago.id, datos_update)
        
        assert pago.conciliado is True
        assert pago.estado == "CONCILIADO"

    def test_registrar_pago_pone_fecha_conciliacion(self, db_session: Session, test_pago, pagos_service):
        """Test that conciliating pago sets fecha_conciliacion."""
        datos_update = {
            "conciliado": True,
            "fecha_conciliacion": datetime.now(),
        }
        
        pago = pagos_service.actualizar_pago(test_pago.id, datos_update)
        
        assert pago.fecha_conciliacion is not None

    # ========================================================================
    # Tests: Transactional Integrity
    # ========================================================================

    def test_crear_multiple_pagos_transacional(self, db_session: Session, test_cliente, pagos_service):
        """Test creating multiple pagos maintains transaction integrity."""
        pagos_creados = []
        
        for i in range(5):
            datos = {
                "cliente_id": test_cliente.id,
                "cedula_cliente": test_cliente.cedula,
                "monto_pagado": Decimal(f"{100 * (i + 1)}.00"),
                "referencia_pago": f"REF-TRANS-{i}",
                "numero_documento": f"DOC-TRANS-{i}",
            }
            pago = pagos_service.crear_pago(datos)
            pagos_creados.append(pago)
        
        # Verify all were created
        assert len(pagos_creados) == 5
        
        # Verify all exist in database
        for pago in pagos_creados:
            db_pago = db_session.query(Pago).filter(Pago.id == pago.id).first()
            assert db_pago is not None
            assert db_pago.id == pago.id

    def test_actualizar_pago_no_afecta_otros(self, db_session: Session, test_cliente, pagos_service):
        """Test that updating one pago doesn't affect others."""
        # Create two pagos
        datos1 = {
            "cliente_id": test_cliente.id,
            "cedula_cliente": test_cliente.cedula,
            "monto_pagado": Decimal("500.00"),
            "referencia_pago": "REF-ISOLATED-1",
        }
        pago1 = pagos_service.crear_pago(datos1)

        datos2 = {
            "cliente_id": test_cliente.id,
            "cedula_cliente": test_cliente.cedula,
            "monto_pagado": Decimal("300.00"),
            "referencia_pago": "REF-ISOLATED-2",
        }
        pago2 = pagos_service.crear_pago(datos2)

        # Update first pago
        pagos_service.actualizar_pago(pago1.id, {"estado": "CONCILIADO"})

        # Verify second pago is unchanged
        pago2_check = pagos_service.obtener_pago(pago2.id)
        assert pago2_check.estado != "CONCILIADO"

    # ========================================================================
    # Tests: Edge Cases
    # ========================================================================

    def test_pago_monto_cero_falla(self, db_session: Session, test_cliente, pagos_service):
        """Test that creating pago with monto 0 fails."""
        datos = {
            "cliente_id": test_cliente.id,
            "cedula_cliente": test_cliente.cedula,
            "monto_pagado": Decimal("0.00"),
            "referencia_pago": "REF-ZERO",
        }
        
        with pytest.raises(Exception):  # Should raise validation error
            pagos_service.crear_pago(datos)

    def test_pago_referencia_vacia_falla(self, db_session: Session, test_cliente, pagos_service):
        """Test that referencia_pago is required."""
        datos = {
            "cliente_id": test_cliente.id,
            "cedula_cliente": test_cliente.cedula,
            "monto_pagado": Decimal("500.00"),
            "referencia_pago": "",
        }
        
        with pytest.raises(Exception):
            pagos_service.crear_pago(datos)

    def test_pago_large_monto(self, db_session: Session, test_cliente, pagos_service):
        """Test creating pago with large amount."""
        datos = {
            "cliente_id": test_cliente.id,
            "cedula_cliente": test_cliente.cedula,
            "monto_pagado": Decimal("999999999.99"),
            "referencia_pago": "REF-LARGE",
        }
        
        pago = pagos_service.crear_pago(datos)
        
        assert pago.monto_pagado == Decimal("999999999.99")

    def test_pago_precision_decimal(self, db_session: Session, test_cliente, pagos_service):
        """Test that decimal precision is maintained."""
        monto = Decimal("123.456789")
        datos = {
            "cliente_id": test_cliente.id,
            "cedula_cliente": test_cliente.cedula,
            "monto_pagado": monto,
            "referencia_pago": "REF-DECIMAL",
        }
        
        pago = pagos_service.crear_pago(datos)
        
        # Verify precision is maintained
        assert pago.monto_pagado == Decimal("123.456789")

    # ========================================================================
    # Tests: Backward Compatibility (Old + New Endpoints)
    # ========================================================================

    def test_pago_legacy_estado_field(self, db_session: Session, test_pago):
        """Test that legacy estado field is still accessible."""
        assert test_pago.estado is not None
        assert isinstance(test_pago.estado, str)

    def test_pago_timestamp_always_set(self, db_session: Session, test_pago):
        """Test that fecha_registro timestamp is always set."""
        assert test_pago.fecha_registro is not None
        assert isinstance(test_pago.fecha_registro, datetime)

    def test_pago_preserves_cedula_format(self, db_session: Session, test_cliente, pagos_service):
        """Test that cedula format is preserved in pago."""
        cedula = "V123456789"
        datos = {
            "cliente_id": test_cliente.id,
            "cedula_cliente": cedula,
            "monto_pagado": Decimal("500.00"),
            "referencia_pago": "REF-CEDULA",
        }
        
        pago = pagos_service.crear_pago(datos)
        
        assert pago.cedula_cliente == cedula
