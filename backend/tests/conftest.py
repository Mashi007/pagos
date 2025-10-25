"""
Fixtures de Testing
Configuración común para todas las pruebas
"""

import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.session import get_db, Base
from app.models.user import User
from app.core.security import get_password_hash


SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session")
def event_loop():
    """Crear event loop para pruebas asíncronas"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop


@pytest.fixture(scope="function")
def test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db_session(test_db):
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    transaction.rollback()


@pytest.fixture(scope="function")
def test_client(db_session):
    """Crear cliente de prueba FastAPI"""


    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def test_user(db_session):
    """Crear usuario de prueba"""
    user = User
        hashed_password=get_password_hash("testpassword123"),
        is_admin=False,
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture(scope="function")
def test_admin_user(db_session):
    """Crear usuario administrador de prueba"""
    admin = User
        hashed_password=get_password_hash("adminpassword123"),
        is_admin=True,
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    return admin


@pytest.fixture(scope="function")
def auth_headers(test_client, test_user):
    """Crear headers de autenticación para pruebas"""
        "/api/v1/auth/login",
        data={"username": test_user.email, "password": "testpassword123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def admin_headers(test_client, test_admin_user):
    """Crear headers de autenticación para admin"""
        "/api/v1/auth/login",
        data={"username": test_admin_user.email, "password": "adminpassword123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="function")
def sample_cliente_data():
    return 
    }


@pytest.fixture(scope="function")
def sample_pago_data():
    return 
    }


@pytest.fixture(scope="function")
def sample_prestamo_data():
    return 
    }


# Configuración de entorno de prueba
@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Configurar entorno de prueba"""
    # Configurar variables de entorno para testing

    yield

    # Limpiar variables de entorno después de las pruebas
    test_env_vars = ["ENVIRONMENT", "DEBUG", "LOG_LEVEL"]
    for var in test_env_vars:

"""