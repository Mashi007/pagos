"""
Pruebas de Integración - Endpoints
"""

from fastapi.testclient import TestClient


class TestAuthEndpoints:
    """Pruebas para endpoints de autenticación"""

    def test_login_exitoso(self, test_client: TestClient, test_user):
        """Probar login exitoso"""
        response = test_client.post(
            "/api/v1/auth/login",
            data={"username": test_user.email, "password": "testpassword123"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"


    def test_login_credenciales_invalidas(self, test_client: TestClient):
        """Probar login con credenciales inválidas"""
        response = test_client.post(
            "/api/v1/auth/login",
            data={"username": "invalid@example.com", "password": "wrongpassword"},
        )

        assert response.status_code == 401


    def test_login_password_incorrecta(self, test_client: TestClient, test_user):
        """Probar login con password incorrecta"""
        response = test_client.post(
            "/api/v1/auth/login",
            data={"username": test_user.email, "password": "wrongpassword"},
        )

        assert response.status_code == 401


    def test_get_current_user(self, test_client: TestClient, auth_headers):
        """Probar obtener usuario actual"""
        response = test_client.get("/api/v1/auth/me", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        assert "nombre" in data
        assert "apellido" in data


    def test_get_current_user_sin_token(self, test_client: TestClient):
        """Probar obtener usuario sin token"""
        response = test_client.get("/api/v1/auth/me")

        assert response.status_code == 401


class TestClientesEndpoints:
    """Pruebas para endpoints de clientes"""

    def test_crear_cliente(
        self, test_client: TestClient, auth_headers, sample_cliente_data
    ):
        """Probar creación de cliente"""
        response = test_client.post(
            "/api/v1/clientes/", json=sample_cliente_data, headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()
        assert data["cedula"] == sample_cliente_data["cedula"]
        assert data["nombres"] == sample_cliente_data["nombres"]

    def test_crear_cliente_cedula_duplicada(
        self, test_client: TestClient, auth_headers, sample_cliente_data
    ):
        """Probar creación de cliente con cédula duplicada"""
        # Crear primer cliente
        response1 = test_client.post(
            "/api/v1/clientes/", json=sample_cliente_data, headers=auth_headers
        )
        assert response1.status_code == 201

        # Intentar crear segundo cliente con misma cédula
        response2 = test_client.post(
            "/api/v1/clientes/", json=sample_cliente_data, headers=auth_headers
        )

        assert response2.status_code == 503
        assert "duplicate" in response2.json()["detail"].lower()


    def test_listar_clientes(self, test_client: TestClient, auth_headers):
        """Probar listado de clientes"""
        response = test_client.get("/api/v1/clientes/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "total" in data
        assert "page" in data
        assert "per_page" in data


    def test_obtener_cliente_por_id(
        self, test_client: TestClient, auth_headers, sample_cliente_data
    ):
        """Probar obtener cliente por ID"""
        # Crear cliente primero
        create_response = test_client.post(
            "/api/v1/clientes/", json=sample_cliente_data, headers=auth_headers
        )
        cliente_id = create_response.json()["id"]

        # Obtener cliente por ID
        response = test_client.get(f"/api/v1/clientes/{cliente_id}", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == cliente_id
        assert data["cedula"] == sample_cliente_data["cedula"]


    def test_obtener_cliente_no_existe(self, test_client: TestClient, auth_headers):
        """Probar obtener cliente que no existe"""
        response = test_client.get("/api/v1/clientes/99999", headers=auth_headers)

        assert response.status_code == 404
        assert "no encontrado" in response.json()["detail"].lower()


    def test_actualizar_cliente(
        self, test_client: TestClient, auth_headers, sample_cliente_data
    ):
        """Probar actualización de cliente"""
        # Crear cliente primero
        create_response = test_client.post(
            "/api/v1/clientes/", json=sample_cliente_data, headers=auth_headers
        )
        cliente_id = create_response.json()["id"]

        # Actualizar cliente
        updated_data = {**sample_cliente_data, "nombres": "Juan Actualizado"}
        response = test_client.put(
            f"/api/v1/clientes/{cliente_id}", json=updated_data, headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()


    def test_eliminar_cliente(
        self, test_client: TestClient, auth_headers, sample_cliente_data
    ):
        """Probar eliminación de cliente"""
        # Crear cliente primero
        create_response = test_client.post(
            "/api/v1/clientes/", json=sample_cliente_data, headers=auth_headers
        )
        cliente_id = create_response.json()["id"]

        # Eliminar cliente
        response = test_client.delete(f"/api/v1/clientes/{cliente_id}", headers=auth_headers)

        assert response.status_code == 200
        assert "eliminado" in response.json()["message"].lower()


class TestValidadoresEndpoints:
    """Pruebas para endpoints de validadores"""


    def test_endpoint_test_validadores(self, test_client: TestClient):
        """Probar endpoint de test de validadores"""
        response = test_client.get("/api/v1/validadores/test")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "funcionando" in data["message"].lower()


    def test_endpoint_info_validadores(self, test_client: TestClient):
        """Probar endpoint de información de validadores"""
        response = test_client.get("/api/v1/validadores/")

        assert response.status_code == 200
        data = response.json()
        assert "validadores_disponibles" in data
        assert "endpoints" in data
        assert "status" in data


    def test_validar_cedula_valida(self, test_client: TestClient):
        """Probar validación de cédula válida"""
        response = test_client.get("/api/v1/validadores/test-cedula/V12345678")

        assert response.status_code == 200
        data = response.json()
        assert data["resultado"]["valido"] is True
        assert data["resultado"]["pais"] == "VENEZUELA"


    def test_validar_cedula_invalida(self, test_client: TestClient):
        """Probar validación de cédula inválida"""
        response = test_client.get("/api/v1/validadores/test-cedula/12345678")

        assert response.status_code == 200
        data = response.json()
        assert data["resultado"]["valido"] is False
        assert "prefijo" in data["resultado"]["error"].lower()


class TestHealthEndpoints:
    """Pruebas para endpoints de health check"""


    def test_health_check_render(self, test_client: TestClient):
        """Probar health check optimizado para Render"""
        response = test_client.get("/api/v1/health/render")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["render_optimized"] is True


    def test_health_check_detailed(self, test_client: TestClient):
        """Probar health check detallado"""
        response = test_client.get("/api/v1/health/detailed")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "service" in data
        assert "database" in data
        assert "system_metrics" in data


    def test_root_endpoint(self, test_client: TestClient):
        """Probar endpoint raíz"""
        response = test_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "status" in data
        assert data["status"] == "running"


class TestCargaMasivaEndpoints:
    """Pruebas para endpoints de carga masiva"""


    def test_upload_archivo_invalido(self, test_client: TestClient, auth_headers):
        """Probar upload de archivo inválido"""
        # Crear archivo de prueba vacío
        files = {"archivo": ("test.txt", b"", "text/plain")}
        data = {"tipo_carga": "clientes"}

        response = test_client.post(
            "/api/v1/carga-masiva/upload", files=files, data=data, headers=auth_headers
        )

        assert response.status_code == 400
        assert "formato" in response.json()["detail"].lower() or "error" in response.json()["detail"].lower()


    def test_upload_sin_archivo(self, test_client: TestClient, auth_headers):
        """Probar upload sin archivo"""
        data = {"tipo_carga": "clientes"}

        response = test_client.post(
            "/api/v1/carga-masiva/upload", data=data, headers=auth_headers
        )

        assert response.status_code == 422  # Validation error


    def test_upload_tipo_carga_invalido(self, test_client: TestClient, auth_headers):
        """Probar upload con tipo de carga inválido"""
        files = {"archivo": ("test.txt", b"test content", "text/plain")}
        data = {"tipo_carga": "invalid_type"}

        response = test_client.post(
            "/api/v1/carga-masiva/upload", files=files, data=data, headers=auth_headers
        )

        assert response.status_code == 400
        assert "tipo" in response.json()["detail"].lower()


    def test_listar_concesionarios(self, test_client: TestClient, auth_headers):
        """Probar listado de concesionarios"""
        response = test_client.get("/api/v1/concesionarios/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "total" in data

    def test_crear_concesionario(self, test_client: TestClient, auth_headers):
        """Probar creación de concesionario"""
        concesionario_data = {
            "nombre": "Concesionario Test",
            "direccion": "Caracas, Venezuela",
            "telefono": "+58412123456",
            "email": "test@concesionario.com",
            "activo": True,
        }
        response = test_client.post(
            "/api/v1/concesionarios/", json=concesionario_data, headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()


class TestAnalistasEndpoints:
    """Pruebas para endpoints de analistas"""


    def test_listar_analistas(self, test_client: TestClient, auth_headers):
        """Probar listado de analistas"""
        response = test_client.get("/api/v1/analistas/", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "total" in data


    def test_crear_analista(self, test_client: TestClient, auth_headers):
        """Probar creación de analista"""
        analista_data = {
            "nombre": "Analista Test",
            "email": "analista@test.com",
            "telefono": "+58412123456",
            "activo": True,
        }
        response = test_client.post(
            "/api/v1/analistas/", json=analista_data, headers=auth_headers
        )

        assert response.status_code == 201
        data = response.json()