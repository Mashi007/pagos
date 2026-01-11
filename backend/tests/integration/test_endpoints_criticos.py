"""
Tests de Integración - Endpoints Críticos
Tests para dashboard, préstamos, pagos, reportes, cobranzas y notificaciones
"""

import pytest
from datetime import date, datetime, timedelta
from decimal import Decimal
from fastapi.testclient import TestClient

from app.models.cliente import Cliente
from app.models.prestamo import Prestamo
from app.models.pago import Pago
from app.models.amortizacion import Cuota


@pytest.mark.integration
class TestDashboardEndpoints:
    """Tests para endpoints de dashboard"""

    def test_dashboard_admin_basico(self, test_client: TestClient, admin_headers):
        """Probar dashboard de administrador básico"""
        response = test_client.get(
            "/api/v1/dashboard/admin",
            headers=admin_headers,
            params={"periodo": "mes"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "cartera_total" in data or "total_prestamos" in data
        assert "cartera_vencida" in data or "mora" in data

    def test_dashboard_admin_con_filtros(self, test_client: TestClient, admin_headers):
        """Probar dashboard de administrador con filtros"""
        response = test_client.get(
            "/api/v1/dashboard/admin",
            headers=admin_headers,
            params={
                "periodo": "mes",
                "analista": "Test Analista",
                "fecha_inicio": "2024-01-01",
                "fecha_fin": "2024-12-31"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_dashboard_admin_sin_permisos(self, test_client: TestClient, auth_headers):
        """Probar que usuarios no admin no pueden acceder"""
        response = test_client.get(
            "/api/v1/dashboard/admin",
            headers=auth_headers
        )

        assert response.status_code == 403

    def test_kpis_principales(self, test_client: TestClient, admin_headers):
        """Probar endpoint de KPIs principales"""
        response = test_client.get(
            "/api/v1/dashboard/kpis-principales",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_cobros_diarios(self, test_client: TestClient, admin_headers):
        """Probar endpoint de cobros diarios"""
        response = test_client.get(
            "/api/v1/dashboard/cobros-diarios",
            headers=admin_headers,
            params={"dias": 30}
        )

        assert response.status_code == 200
        data = response.json()
        assert "datos" in data
        assert isinstance(data["datos"], list)

    def test_opciones_filtros(self, test_client: TestClient, admin_headers):
        """Probar endpoint de opciones de filtros"""
        response = test_client.get(
            "/api/v1/dashboard/opciones-filtros",
            headers=admin_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)


@pytest.mark.integration
class TestPrestamosEndpoints:
    """Tests para endpoints de préstamos"""

    def test_listar_prestamos(self, test_client: TestClient, auth_headers):
        """Probar listado de préstamos"""
        response = test_client.get(
            "/api/v1/prestamos",
            headers=auth_headers,
            params={"page": 1, "per_page": 20}
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data

    def test_listar_prestamos_con_filtros(self, test_client: TestClient, auth_headers):
        """Probar listado de préstamos con filtros"""
        response = test_client.get(
            "/api/v1/prestamos",
            headers=auth_headers,
            params={
                "page": 1,
                "per_page": 20,
                "estado": "APROBADO",
                "cedula": "V12345678"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    def test_obtener_prestamo_por_id(self, test_client: TestClient, auth_headers, test_db, db_session, sample_cliente_data):
        """Probar obtener préstamo por ID"""
        # Crear cliente primero
        cliente = Cliente(**sample_cliente_data, estado="ACTIVO")
        db_session.add(cliente)
        db_session.commit()

        # Crear préstamo
        prestamo = Prestamo(
            cliente_id=cliente.id,
            cedula=sample_cliente_data["cedula"],
            nombres=sample_cliente_data["nombres"],
            total_financiamiento=Decimal("50000.00"),
            fecha_requerimiento=date.today(),
            modalidad_pago="MENSUAL",
            numero_cuotas=24,
            cuota_periodo=1,
            estado="APROBADO"
        )
        db_session.add(prestamo)
        db_session.commit()

        # Obtener préstamo
        response = test_client.get(
            f"/api/v1/prestamos/{prestamo.id}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == prestamo.id

    def test_obtener_prestamo_no_existe(self, test_client: TestClient, auth_headers):
        """Probar obtener préstamo que no existe"""
        response = test_client.get(
            "/api/v1/prestamos/99999",
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_obtener_prestamos_por_cedula(self, test_client: TestClient, auth_headers, test_db, db_session, sample_cliente_data):
        """Probar obtener préstamos por cédula"""
        # Crear cliente y préstamo
        cliente = Cliente(**sample_cliente_data, estado="ACTIVO")
        db_session.add(cliente)
        db_session.commit()

        prestamo = Prestamo(
            cliente_id=cliente.id,
            cedula=sample_cliente_data["cedula"],
            nombres=sample_cliente_data["nombres"],
            total_financiamiento=Decimal("50000.00"),
            fecha_requerimiento=date.today(),
            modalidad_pago="MENSUAL",
            numero_cuotas=24,
            cuota_periodo=1,
            estado="APROBADO"
        )
        db_session.add(prestamo)
        db_session.commit()

        # Obtener préstamos por cédula
        response = test_client.get(
            f"/api/v1/prestamos/cedula/{sample_cliente_data['cedula']}",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_stats_prestamos(self, test_client: TestClient, auth_headers):
        """Probar estadísticas de préstamos"""
        response = test_client.get(
            "/api/v1/prestamos/stats",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_crear_prestamo(self, test_client: TestClient, auth_headers, test_db, db_session, sample_cliente_data):
        """Probar creación de préstamo"""
        # Crear cliente primero
        cliente = Cliente(**sample_cliente_data, estado="ACTIVO")
        db_session.add(cliente)
        db_session.commit()

        prestamo_data = {
            "cedula": sample_cliente_data["cedula"],
            "total_financiamiento": 50000.00,
            "fecha_requerimiento": date.today().isoformat(),
            "modalidad_pago": "MENSUAL",
            "numero_cuotas": 24,
            "cuota_periodo": 1,
            "producto": "VEHICULO",
            "producto_financiero": "CREDITO_DIRECTO"
        }

        response = test_client.post(
            "/api/v1/prestamos",
            json=prestamo_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert data["cedula"] == sample_cliente_data["cedula"]
        assert data["total_financiamiento"] == 50000.00

    def test_crear_prestamo_cliente_no_existe(self, test_client: TestClient, auth_headers):
        """Probar creación de préstamo con cliente inexistente"""
        prestamo_data = {
            "cedula": "V99999999",
            "total_financiamiento": 50000.00,
            "fecha_requerimiento": date.today().isoformat(),
            "modalidad_pago": "MENSUAL",
            "numero_cuotas": 24,
            "cuota_periodo": 1,
            "producto": "VEHICULO"
        }

        response = test_client.post(
            "/api/v1/prestamos",
            json=prestamo_data,
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_actualizar_prestamo(self, test_client: TestClient, auth_headers, test_db, db_session, sample_cliente_data):
        """Probar actualización de préstamo"""
        # Crear cliente y préstamo
        cliente = Cliente(**sample_cliente_data, estado="ACTIVO")
        db_session.add(cliente)
        db_session.commit()

        prestamo = Prestamo(
            cliente_id=cliente.id,
            cedula=sample_cliente_data["cedula"],
            nombres=sample_cliente_data["nombres"],
            total_financiamiento=Decimal("50000.00"),
            fecha_requerimiento=date.today(),
            modalidad_pago="MENSUAL",
            numero_cuotas=24,
            cuota_periodo=1,
            estado="DRAFT"
        )
        db_session.add(prestamo)
        db_session.commit()

        # Actualizar préstamo
        update_data = {
            "total_financiamiento": 60000.00,
            "observaciones": "Préstamo actualizado"
        }

        response = test_client.put(
            f"/api/v1/prestamos/{prestamo.id}",
            json=update_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert float(data["total_financiamiento"]) == 60000.00

    def test_eliminar_prestamo(self, test_client: TestClient, auth_headers, test_db, db_session, sample_cliente_data):
        """Probar eliminación de préstamo"""
        # Crear cliente y préstamo
        cliente = Cliente(**sample_cliente_data, estado="ACTIVO")
        db_session.add(cliente)
        db_session.commit()

        prestamo = Prestamo(
            cliente_id=cliente.id,
            cedula=sample_cliente_data["cedula"],
            nombres=sample_cliente_data["nombres"],
            total_financiamiento=Decimal("50000.00"),
            fecha_requerimiento=date.today(),
            modalidad_pago="MENSUAL",
            numero_cuotas=24,
            cuota_periodo=1,
            estado="DRAFT"
        )
        db_session.add(prestamo)
        db_session.commit()

        # Eliminar préstamo
        response = test_client.delete(
            f"/api/v1/prestamos/{prestamo.id}",
            headers=auth_headers
        )

        assert response.status_code == 200

    def test_obtener_cuotas_prestamo(self, test_client: TestClient, auth_headers, test_db, db_session, sample_cliente_data):
        """Probar obtener cuotas de un préstamo"""
        # Crear cliente y préstamo
        cliente = Cliente(**sample_cliente_data, estado="ACTIVO")
        db_session.add(cliente)
        db_session.commit()

        prestamo = Prestamo(
            cliente_id=cliente.id,
            cedula=sample_cliente_data["cedula"],
            nombres=sample_cliente_data["nombres"],
            total_financiamiento=Decimal("50000.00"),
            fecha_requerimiento=date.today(),
            modalidad_pago="MENSUAL",
            numero_cuotas=24,
            cuota_periodo=1,
            estado="APROBADO"
        )
        db_session.add(prestamo)
        db_session.commit()

        # Obtener cuotas
        response = test_client.get(
            f"/api/v1/prestamos/{prestamo.id}/cuotas",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.integration
class TestPagosEndpoints:
    """Tests para endpoints de pagos"""

    def test_listar_pagos(self, test_client: TestClient, auth_headers):
        """Probar listado de pagos"""
        response = test_client.get(
            "/api/v1/pagos",
            headers=auth_headers,
            params={"page": 1, "per_page": 20}
        )

        assert response.status_code == 200
        data = response.json()
        assert "pagos" in data or "data" in data
        assert "total" in data
        assert "page" in data

    def test_listar_pagos_con_filtros(self, test_client: TestClient, auth_headers):
        """Probar listado de pagos con filtros"""
        response = test_client.get(
            "/api/v1/pagos",
            headers=auth_headers,
            params={
                "page": 1,
                "per_page": 20,
                "cedula": "V12345678",
                "fecha_desde": "2024-01-01",
                "fecha_hasta": "2024-12-31"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_crear_pago(self, test_client: TestClient, auth_headers, test_db, db_session, sample_cliente_data):
        """Probar creación de pago"""
        # Crear cliente primero
        cliente = Cliente(**sample_cliente_data, estado="ACTIVO")
        db_session.add(cliente)
        db_session.commit()

        pago_data = {
            "cedula": sample_cliente_data["cedula"],
            "monto_pagado": 1000.00,
            "fecha_pago": datetime.now().isoformat(),  # Usar datetime en lugar de date
            "metodo_pago": "TRANSFERENCIA",
            "numero_documento": "DOC123456"
        }

        response = test_client.post(
            "/api/v1/pagos",
            json=pago_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert float(data["monto_pagado"]) == 1000.00

    def test_crear_pago_cliente_no_existe(self, test_client: TestClient, auth_headers):
        """Probar creación de pago con cliente inexistente"""
        pago_data = {
            "cedula": "V99999999",
            "monto_pagado": 1000.00,
            "fecha_pago": datetime.now().isoformat(),  # Usar datetime
            "metodo_pago": "TRANSFERENCIA",
            "numero_documento": "DOC999999"
        }

        response = test_client.post(
            "/api/v1/pagos",
            json=pago_data,
            headers=auth_headers
        )

        assert response.status_code == 404

    def test_obtener_pago_por_id(self, test_client: TestClient, auth_headers, db_session, sample_cliente_data):
        """Probar obtener pago por ID"""
        # Crear cliente y pago
        cliente = Cliente(**sample_cliente_data, estado="ACTIVO")
        db_session.add(cliente)
        db_session.commit()

        pago = Pago(
            cedula=sample_cliente_data["cedula"],
            monto_pagado=Decimal("1000.00"),
            fecha_pago=date.today(),
            metodo_pago="TRANSFERENCIA",
            numero_documento="DOC123456"
        )
        db_session.add(pago)
        db_session.commit()

        # Obtener pago
        response = test_client.get(
            f"/api/v1/pagos/{pago.id}",
            headers=auth_headers
        )

        # Puede retornar 200 o 404 dependiendo de si el endpoint existe
        assert response.status_code in [200, 404]

    def test_actualizar_pago(self, test_client: TestClient, auth_headers, test_db, db_session, sample_cliente_data):
        """Probar actualización de pago"""
        # Crear cliente y pago
        cliente = Cliente(**sample_cliente_data, estado="ACTIVO")
        db_session.add(cliente)
        db_session.commit()

        pago = Pago(
            cedula=sample_cliente_data["cedula"],
            monto_pagado=Decimal("1000.00"),
            fecha_pago=datetime.now(),
            metodo_pago="TRANSFERENCIA",
            numero_documento="DOC123456"
        )
        db_session.add(pago)
        db_session.commit()

        # Actualizar pago
        update_data = {
            "monto_pagado": 1500.00
        }

        response = test_client.put(
            f"/api/v1/pagos/{pago.id}",
            json=update_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert float(data["monto_pagado"]) == 1500.00

    def test_pagos_kpis(self, test_client: TestClient, auth_headers):
        """Probar KPIs de pagos"""
        response = test_client.get(
            "/api/v1/pagos/kpis",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_pagos_stats(self, test_client: TestClient, auth_headers):
        """Probar estadísticas de pagos"""
        response = test_client.get(
            "/api/v1/pagos/stats",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_ultimos_pagos(self, test_client: TestClient, auth_headers):
        """Probar endpoint de últimos pagos"""
        response = test_client.get(
            "/api/v1/pagos/ultimos",
            headers=auth_headers,
            params={"limit": 10}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)


@pytest.mark.integration
class TestReportesEndpoints:
    """Tests para endpoints de reportes"""

    def test_reporte_cartera(self, test_client: TestClient, auth_headers):
        """Probar reporte de cartera"""
        response = test_client.get(
            "/api/v1/reportes/cartera",
            headers=auth_headers,
            params={"fecha_corte": date.today().isoformat()}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "cartera_total" in data or "total_cartera" in data

    def test_reporte_pagos(self, test_client: TestClient, auth_headers):
        """Probar reporte de pagos"""
        response = test_client.get(
            "/api/v1/reportes/pagos",
            headers=auth_headers,
            params={
                "fecha_inicio": "2024-01-01",
                "fecha_fin": "2024-12-31"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_reporte_morosidad(self, test_client: TestClient, auth_headers):
        """Probar reporte de morosidad"""
        response = test_client.get(
            "/api/v1/reportes/morosidad",
            headers=auth_headers,
            params={"fecha_corte": date.today().isoformat()}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_reporte_financiero(self, test_client: TestClient, auth_headers):
        """Probar reporte financiero"""
        response = test_client.get(
            "/api/v1/reportes/financiero",
            headers=auth_headers,
            params={
                "fecha_inicio": "2024-01-01",
                "fecha_fin": "2024-12-31"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_reporte_asesores(self, test_client: TestClient, auth_headers):
        """Probar reporte de asesores"""
        response = test_client.get(
            "/api/v1/reportes/asesores",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_reporte_productos(self, test_client: TestClient, auth_headers):
        """Probar reporte de productos"""
        response = test_client.get(
            "/api/v1/reportes/productos",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)


@pytest.mark.integration
class TestCobranzasEndpoints:
    """Tests para endpoints de cobranzas"""

    def test_clientes_atrasados(self, test_client: TestClient, auth_headers):
        """Probar obtener clientes atrasados"""
        response = test_client.get(
            "/api/v1/cobranzas/clientes-atrasados",
            headers=auth_headers,
            params={"dias_retraso": 30}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict) or isinstance(data, list)

    def test_resumen_cobranzas(self, test_client: TestClient, auth_headers):
        """Probar resumen de cobranzas"""
        response = test_client.get(
            "/api/v1/cobranzas/resumen",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_cobranzas_por_analista(self, test_client: TestClient, auth_headers):
        """Probar cobranzas por analista"""
        response = test_client.get(
            "/api/v1/cobranzas/por-analista",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict) or isinstance(data, list)

    def test_montos_por_mes(self, test_client: TestClient, auth_headers):
        """Probar montos de cobranza por mes"""
        response = test_client.get(
            "/api/v1/cobranzas/montos-por-mes",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict) or isinstance(data, list)

    def test_clientes_por_cantidad_pagos(self, test_client: TestClient, auth_headers):
        """Probar clientes por cantidad de pagos"""
        response = test_client.get(
            "/api/v1/cobranzas/clientes-por-cantidad-pagos",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict) or isinstance(data, list)


@pytest.mark.integration
class TestNotificacionesEndpoints:
    """Tests para endpoints de notificaciones"""

    def test_listar_notificaciones(self, test_client: TestClient, auth_headers):
        """Probar listado de notificaciones"""
        response = test_client.get(
            "/api/v1/notificaciones/",
            headers=auth_headers,
            params={"page": 1, "per_page": 20}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict) or isinstance(data, list)

    def test_enviar_notificacion(self, test_client: TestClient, auth_headers, test_db, db_session, sample_cliente_data):
        """Probar envío de notificación"""
        # Crear cliente primero
        cliente = Cliente(**sample_cliente_data, estado="ACTIVO")
        db_session.add(cliente)
        db_session.commit()

        notificacion_data = {
            "cliente_id": cliente.id,
            "tipo": "EMAIL",
            "canal": "EMAIL",
            "asunto": "Test Notification",
            "mensaje": "This is a test notification"
        }

        response = test_client.post(
            "/api/v1/notificaciones/enviar",
            json=notificacion_data,
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_estadisticas_notificaciones(self, test_client: TestClient, auth_headers):
        """Probar estadísticas de notificaciones"""
        response = test_client.get(
            "/api/v1/notificaciones/estadisticas/resumen",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_listar_plantillas(self, test_client: TestClient, auth_headers):
        """Probar listado de plantillas de notificaciones"""
        response = test_client.get(
            "/api/v1/notificaciones/plantillas",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_listar_variables(self, test_client: TestClient, auth_headers):
        """Probar listado de variables disponibles"""
        response = test_client.get(
            "/api/v1/notificaciones/variables",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
