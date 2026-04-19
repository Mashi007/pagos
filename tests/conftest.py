"""
Shared pytest configuration and fixtures for all tests.
Sets up test database, test client, and common test data.
"""

import os
import pytest
from datetime import date, datetime
from decimal import Decimal
from typing import Generator

from sqlalchemy import create_engine, text, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.core.config import Settings


# Test database URL — el esquema usa JSONB (PostgreSQL). SQLite no puede crear todas las tablas.
def get_test_db_url():
    """URL del motor de pytest: TEST_DATABASE_URL, luego DATABASE_URL si es Postgres, si no SQLite."""
    test_db = (os.getenv("TEST_DATABASE_URL") or "").strip()
    if test_db:
        return test_db
    app_db = (os.getenv("DATABASE_URL") or "").strip()
    if app_db.startswith("postgres://"):
        app_db = app_db.replace("postgres://", "postgresql://", 1)
    if app_db.startswith("postgresql"):
        return app_db
    return "sqlite:///:memory:"


# Create test database engine
TEST_DB_URL = get_test_db_url()

if "sqlite" in TEST_DB_URL:
    engine = create_engine(
        TEST_DB_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # Use static pool for in-memory SQLite
    )
else:
    # PostgreSQL or other database
    engine = create_engine(
        TEST_DB_URL,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
    )


TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def db_engine():
    """Create database tables once per test session."""
    # Create all tables
    Base.metadata.create_all(bind=engine)
    yield engine
    # Drop all tables after all tests
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(db_engine) -> Generator[Session, None, None]:
    """
    Provide a test database session.
    Rolls back all changes after each test (transaction isolation).
    """
    # Start a transaction for this test
    connection = db_engine.connect()
    transaction = connection.begin()
    
    # Create a session bound to this transaction
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    # Rollback the transaction after the test (clean up)
    session.close()
    transaction.rollback()
    connection.close()


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def test_cliente_data() -> dict:
    """Test data for creating a cliente."""
    return {
        "cedula": "V123456789",
        "nombres": "Juan Pérez García",
        "telefono": "02641234567",
        "email": "juan@example.com",
        "direccion": "Calle Principal 123, Apartamento 4B",
        "fecha_nacimiento": date(1990, 5, 15),
        "ocupacion": "Ingeniero",
        "estado": "ACTIVO",
        "usuario_registro": "test_user",
        "notas": "Cliente de prueba",
    }


@pytest.fixture
def test_cliente(db_session: Session, test_cliente_data: dict):
    """Create and insert a test cliente into the database."""
    from app.models.cliente import Cliente
    
    cliente = Cliente(**test_cliente_data)
    db_session.add(cliente)
    db_session.commit()
    db_session.refresh(cliente)
    return cliente


@pytest.fixture
def test_cliente_2(db_session: Session) -> "Cliente":
    """Create a second test cliente."""
    from app.models.cliente import Cliente
    
    cliente = Cliente(
        cedula="V987654321",
        nombres="María González López",
        telefono="02649876543",
        email="maria@example.com",
        direccion="Avenida Secundaria 456",
        fecha_nacimiento=date(1985, 3, 20),
        ocupacion="Doctora",
        estado="ACTIVO",
        usuario_registro="test_user",
        notas="Cliente de prueba 2",
    )
    db_session.add(cliente)
    db_session.commit()
    db_session.refresh(cliente)
    return cliente


@pytest.fixture
def test_prestamo_data(test_cliente) -> dict:
    """Test data for creating a prestamo."""
    return {
        "cliente_id": test_cliente.id,
        "cedula": test_cliente.cedula,
        "nombres": test_cliente.nombres,
        "total_financiamiento": Decimal("10000.00"),
        "fecha_requerimiento": date(2026, 1, 15),
        "modalidad_pago": "MENSUAL",
        "numero_cuotas": 12,
        "cuota_periodo": Decimal("883.33"),
        "tasa_interes": Decimal("15.5000"),
        "fecha_base_calculo": date(2026, 2, 15),
        "producto": "Préstamo Personal",
        "estado": "DRAFT",
        "usuario_proponente": "test_proponente@rapicreditca.com",
        "usuario_aprobador": "test_aprobador@rapicreditca.com",
        "usuario_autoriza": "test_operaciones@rapicreditca.com",
        "observaciones": "Préstamo de prueba",
        "analista": "Test Analista",
        "concesionario": "Test Concesionario",
    }


@pytest.fixture
def test_prestamo(db_session: Session, test_prestamo_data: dict):
    """Create and insert a test prestamo into the database."""
    from app.models.prestamo import Prestamo
    
    prestamo = Prestamo(**test_prestamo_data)
    db_session.add(prestamo)
    db_session.commit()
    db_session.refresh(prestamo)
    return prestamo


@pytest.fixture
def test_prestamo_aprobado(db_session: Session, test_cliente):
    """Create an APROBADO prestamo with amortization table."""
    from app.models.prestamo import Prestamo
    
    prestamo = Prestamo(
        cliente_id=test_cliente.id,
        cedula=test_cliente.cedula,
        nombres=test_cliente.nombres,
        total_financiamiento=Decimal("15000.00"),
        fecha_requerimiento=date(2026, 1, 15),
        modalidad_pago="MENSUAL",
        numero_cuotas=24,
        cuota_periodo=Decimal("708.33"),
        tasa_interes=Decimal("12.0000"),
        fecha_base_calculo=date(2026, 2, 15),
        producto="Préstamo Auto",
        estado="APROBADO",
        usuario_proponente="test@rapicreditca.com",
        usuario_aprobador="test_aprobador@rapicreditca.com",
        fecha_aprobacion=datetime(2026, 1, 20),
    )
    db_session.add(prestamo)
    db_session.commit()
    db_session.refresh(prestamo)
    return prestamo


@pytest.fixture
def test_cuota_data(test_prestamo) -> dict:
    """Test data for creating a cuota."""
    return {
        "prestamo_id": test_prestamo.id,
        "cliente_id": test_prestamo.cliente_id,
        "numero_cuota": 1,
        "fecha_vencimiento": date(2026, 3, 15),
        "monto_cuota": Decimal("883.33"),
        "saldo_capital_inicial": Decimal("10000.00"),
        "saldo_capital_final": Decimal("9116.67"),
        "monto_capital": Decimal("750.00"),
        "monto_interes": Decimal("133.33"),
        "estado": "PENDIENTE",
    }


@pytest.fixture
def test_cuota(db_session: Session, test_cuota_data: dict):
    """Create and insert a test cuota."""
    from app.models.cuota import Cuota
    
    cuota = Cuota(**test_cuota_data)
    db_session.add(cuota)
    db_session.commit()
    db_session.refresh(cuota)
    return cuota


@pytest.fixture
def test_pago_data(test_cliente) -> dict:
    """Test data for creating a pago."""
    return {
        "cedula_cliente": test_cliente.cedula,
        "prestamo_id": None,
        "fecha_pago": datetime(2026, 3, 10),
        "monto_pagado": Decimal("500.00"),
        "numero_documento": "DOC-2026-001",
        "institucion_bancaria": "Banco Test",
        "estado": "REGISTRADO",
        "usuario_registro": "test_user",
        "referencia_pago": "REF-2026-001",
        "conciliado": False,
    }


@pytest.fixture
def test_pago(db_session: Session, test_pago_data: dict):
    """Create and insert a test pago."""
    from app.models.pago import Pago
    
    pago = Pago(**test_pago_data)
    db_session.add(pago)
    db_session.commit()
    db_session.refresh(pago)
    return pago


@pytest.fixture
def test_pago_con_prestamo(db_session: Session, test_cliente, test_prestamo):
    """Create a pago linked to a prestamo."""
    from app.models.pago import Pago
    
    pago = Pago(
        cedula_cliente=test_cliente.cedula,
        prestamo_id=test_prestamo.id,
        fecha_pago=datetime(2026, 3, 10),
        monto_pagado=Decimal("500.00"),
        numero_documento="DOC-2026-002",
        institucion_bancaria="Banco Test",
        estado="REGISTRADO",
        usuario_registro="test_user",
        referencia_pago="REF-2026-002",
        conciliado=False,
    )
    db_session.add(pago)
    db_session.commit()
    db_session.refresh(pago)
    return pago


# ============================================================================
# Service Fixtures
# ============================================================================

@pytest.fixture
def prestamos_service(db_session: Session):
    """Provide PrestamosService instance with test DB session."""
    from app.services.prestamos.prestamos_service import PrestamosService
    return PrestamosService(db_session)


@pytest.fixture
def pagos_service(db_session: Session):
    """Provide PagosService instance with test DB session."""
    from app.services.pagos.pagos_service import PagosService
    return PagosService(db_session)


@pytest.fixture
def amortizacion_service(db_session: Session):
    """Provide AmortizacionService instance with test DB session."""
    from app.services.prestamos.amortizacion_service import AmortizacionService
    return AmortizacionService(db_session)


# ============================================================================
# Helper Functions
# ============================================================================

def create_test_prestamo(
    db_session: Session,
    cliente_id: int,
    total: Decimal = Decimal("10000.00"),
    cuotas: int = 12,
    tasa: Decimal = Decimal("15.5000"),
    estado: str = "DRAFT",
) -> "Prestamo":
    """Helper to create a prestamo with common test parameters."""
    from app.models.prestamo import Prestamo
    
    prestamo = Prestamo(
        cliente_id=cliente_id,
        cedula=f"V{cliente_id:08d}",
        nombres=f"Test Cliente {cliente_id}",
        total_financiamiento=total,
        fecha_requerimiento=date.today(),
        modalidad_pago="MENSUAL",
        numero_cuotas=cuotas,
        cuota_periodo=total / cuotas,
        tasa_interes=tasa,
        fecha_base_calculo=date.today(),
        producto="Préstamo Test",
        estado=estado,
        usuario_proponente="test@rapicreditca.com",
    )
    db_session.add(prestamo)
    db_session.commit()
    db_session.refresh(prestamo)
    return prestamo


def create_test_pago(
    db_session: Session,
    cedula: str,
    monto: Decimal = Decimal("500.00"),
    prestamo_id: int = None,
) -> "Pago":
    """Helper to create a pago with common test parameters."""
    from app.models.pago import Pago
    
    pago = Pago(
        cedula_cliente=cedula,
        prestamo_id=prestamo_id,
        fecha_pago=datetime.now(),
        monto_pagado=monto,
        numero_documento=f"DOC-{datetime.now().timestamp()}",
        referencia_pago=f"REF-{datetime.now().timestamp()}",
        estado="REGISTRADO",
        conciliado=False,
    )
    db_session.add(pago)
    db_session.commit()
    db_session.refresh(pago)
    return pago
