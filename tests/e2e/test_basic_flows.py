"""
Tests End-to-End básicos para flujos críticos de la aplicación

Requisitos:
    - pytest
    - playwright (pip install playwright && playwright install)

Ejecutar:
    pytest tests/e2e/test_basic_flows.py -v
"""

import os
import pytest
from playwright.sync_api import Page, expect


# Configuración
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Configuración del navegador para tests"""
    return {
        **browser_context_args,
        "viewport": {"width": 1920, "height": 1080},
        "ignore_https_errors": True,
    }


@pytest.mark.e2e
class TestAuthenticationFlow:
    """Tests del flujo de autenticación"""

    def test_login_page_loads(self, page: Page):
        """Verificar que la página de login carga correctamente"""
        page.goto(f"{FRONTEND_URL}/login")
        expect(page).to_have_title(containing="Login")
        # Verificar que hay campos de email y password
        expect(page.locator('input[type="email"]')).to_be_visible()
        expect(page.locator('input[type="password"]')).to_be_visible()

    def test_login_with_invalid_credentials(self, page: Page):
        """Verificar que login falla con credenciales inválidas"""
        page.goto(f"{FRONTEND_URL}/login")
        page.fill('input[type="email"]', "invalid@example.com")
        page.fill('input[type="password"]', "wrongpassword")
        page.click('button[type="submit"]')
        # Debería mostrar mensaje de error
        expect(page.locator(".error-message, .alert-error")).to_be_visible(timeout=5000)


@pytest.mark.e2e
class TestHealthCheck:
    """Tests de health checks"""

    def test_api_health_endpoint(self, page: Page):
        """Verificar que el endpoint de health responde"""
        response = page.request.get(f"{BASE_URL}/health")
        assert response.status == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_api_detailed_health_endpoint(self, page: Page):
        """Verificar endpoint de health detallado"""
        response = page.request.get(f"{BASE_URL}/api/v1/health")
        assert response.status == 200
        data = response.json()
        assert "status" in data
        assert "database" in data or "system" in data


@pytest.mark.e2e
class TestDashboardFlow:
    """Tests del flujo del dashboard"""

    @pytest.mark.skip(reason="Requiere autenticación - implementar setup de sesión")
    def test_dashboard_loads_after_login(self, page: Page):
        """Verificar que el dashboard carga después de login"""
        # TODO: Implementar login primero
        page.goto(f"{FRONTEND_URL}/dashboard")
        # Verificar elementos del dashboard
        expect(page.locator("h1, h2")).to_contain_text("Dashboard")


@pytest.mark.e2e
class TestAPIDocumentation:
    """Tests de documentación de API"""

    def test_swagger_docs_accessible(self, page: Page):
        """Verificar que Swagger UI es accesible"""
        page.goto(f"{BASE_URL}/docs")
        expect(page).to_have_title(containing="Swagger")
        # Verificar que hay endpoints listados
        expect(page.locator(".opblock")).to_have_count(count=1, timeout=10000)

    def test_openapi_schema_accessible(self, page: Page):
        """Verificar que el schema OpenAPI es accesible"""
        response = page.request.get(f"{BASE_URL}/openapi.json")
        assert response.status == 200
        data = response.json()
        assert "openapi" in data
        assert "paths" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
