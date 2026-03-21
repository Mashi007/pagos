# Comprehensive Testing Guide - Pagos and Prestamos

## Overview

This document provides comprehensive information about the test suite for pagos and prestamos services.

### Test Statistics

- **Total Tests**: 55+
  - **Integration Tests**: 45+ 
    - Pagos: 20+
    - Prestamos: 25+
  - **Smoke Tests**: 10+
    - Pagos: 5-10
    - Prestamos: 5-10

- **Coverage**: Core service methods, state transitions, error handling, edge cases
- **Execution Time**: < 2 minutes total, < 30 seconds for smoke tests
- **Database**: SQLite in-memory (default) or PostgreSQL (configurable)

## Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements-test.txt

# OR install just pytest and sqlalchemy
pip install pytest sqlalchemy psycopg2-binary
```

### Running Tests

```bash
# Run all tests
pytest tests/

# Run smoke tests (must pass before deploy)
pytest tests/smoke/

# Run integration tests
pytest tests/integration/

# Run pagos tests
pytest tests/ -k pagos

# Run prestamos tests
pytest tests/ -k prestamos

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run specific test
pytest tests/smoke/test_pagos_smoke.py::TestPagosSmokeTests::test_smoke_crear_pago_basico
```

### Using Test Runner Scripts

**Linux/Mac:**
```bash
chmod +x run_tests.sh

./run_tests.sh smoke        # Run smoke tests
./run_tests.sh integration  # Run integration tests
./run_tests.sh pagos        # Run pagos tests
./run_tests.sh prestamos    # Run prestamos tests
./run_tests.sh coverage     # Run with coverage report
./run_tests.sh all          # Run all tests
./run_tests.sh all vv       # Run all tests with extra verbosity
```

**Windows:**
```powershell
.\run_tests.ps1 smoke        # Run smoke tests
.\run_tests.ps1 integration  # Run integration tests
.\run_tests.ps1 pagos        # Run pagos tests
.\run_tests.ps1 prestamos    # Run prestamos tests
.\run_tests.ps1 coverage     # Run with coverage report
.\run_tests.ps1 all          # Run all tests
.\run_tests.ps1 all vv       # Run all tests with extra verbosity
```

## Test Structure

### File Organization

```
tests/
├── conftest.py                 # Shared fixtures and configuration
├── __init__.py
├── README.md                   # Quick reference
├── pytest.ini                  # Pytest configuration
│
├── integration/                # Integration tests (against real DB)
│   ├── __init__.py
│   └── services/
│       ├── __init__.py
│       ├── pagos/
│       │   ├── __init__.py
│       │   └── test_pagos_integration.py       (20+ tests)
│       └── prestamos/
│           ├── __init__.py
│           └── test_prestamos_integration.py   (25+ tests)
│
└── smoke/                      # Smoke tests (critical path)
    ├── __init__.py
    ├── test_pagos_smoke.py       (10 tests)
    └── test_prestamos_smoke.py    (10 tests)
```

## Pagos Service Tests

### Integration Tests: test_pagos_integration.py

#### Test Categories

1. **Create Operations** (5 tests)
   - `test_crear_pago_valido`: Basic pago creation
   - `test_crear_pago_con_prestamo_id`: Link pago to prestamo
   - `test_crear_pago_sin_documento_duplicado`: Duplicate documento validation
   - `test_crear_pago_monto_negativo_falla`: Negative amount validation
   - `test_crear_pago_cliente_no_existe_falla`: Non-existent cliente error

2. **Read Operations** (2 tests)
   - `test_obtener_pago_existente`: Retrieve existing pago
   - `test_obtener_pago_no_existe_falla`: Handle non-existent pago

3. **Update Operations** (4 tests)
   - `test_actualizar_pago_estado`: Update pago estado
   - `test_actualizar_pago_monto`: Update pago amount
   - `test_actualizar_pago_notas`: Update pago notes
   - `test_actualizar_pago_multiple_campos`: Update multiple fields

4. **Delete Operations** (2 tests)
   - `test_eliminar_pago_existente`: Delete existing pago
   - `test_eliminar_pago_no_existe_falla`: Handle delete non-existent

5. **Search/Query Operations** (3 tests)
   - `test_obtener_pagos_cliente_vacio`: Empty cliente pagos
   - `test_obtener_pagos_cliente_multiple`: Multiple pagos retrieval
   - `test_obtener_pagos_cliente_con_limit`: Pagination with limit

6. **Summary/Aggregation** (3 tests)
   - `test_obtener_resumen_pagos_global`: Global summary
   - `test_obtener_resumen_pagos_por_cliente`: Per-cliente summary
   - `test_obtener_resumen_pagos_por_estado`: Grouped by estado

7. **State Management** (2 tests)
   - `test_obtener_pagos_por_estado_registrado`: Query by estado
   - `test_obtener_pagos_por_estado_conciliado`: Another estado query

8. **Conciliation** (2 tests)
   - `test_conciliar_pago`: Mark as conciliado
   - `test_registrar_pago_pone_fecha_conciliacion`: Timestamp setting

9. **Transactional Integrity** (2 tests)
   - `test_crear_multiple_pagos_transacional`: Multiple creates
   - `test_actualizar_pago_no_afecta_otros`: Isolation verification

10. **Edge Cases** (3 tests)
    - `test_pago_monto_cero_falla`: Zero amount validation
    - `test_pago_referencia_vacia_falla`: Required fields
    - `test_pago_large_monto`: Large amount handling
    - `test_pago_precision_decimal`: Decimal precision

11. **Backward Compatibility** (3 tests)
    - `test_pago_legacy_estado_field`: Legacy field access
    - `test_pago_timestamp_always_set`: Default timestamp
    - `test_pago_preserves_cedula_format`: Format preservation

### Smoke Tests: test_pagos_smoke.py

Critical path tests for pre-deployment validation:

1. **CRUD Operations**
   - Create pago
   - Read pago
   - Update pago
   - Delete pago

2. **Query Operations**
   - Search pagos by cliente

3. **Aggregations**
   - Get pago summary

4. **Workflows**
   - Complete conciliation workflow

5. **Performance**
   - Operations complete in < 5 seconds

6. **Integrity**
   - Database integrity maintained
   - Transactional consistency

7. **Error Handling**
   - Invalid cliente error handling
   - Estado transitions

## Prestamos Service Tests

### Integration Tests: test_prestamos_integration.py

#### Test Categories

1. **Create Operations** (5 tests)
   - `test_crear_prestamo_valido_draft`: Create DRAFT prestamo
   - `test_crear_prestamo_con_fecha_base_calculo`: With calculation date
   - `test_crear_prestamo_valida_cliente_existe`: Cliente validation
   - `test_crear_prestamo_numero_cuotas_invalido`: Cuota validation
   - `test_crear_prestamo_tasa_negativa_falla`: Rate validation

2. **Read Operations** (2 tests)
   - `test_obtener_prestamo_existente`: Retrieve existing
   - `test_obtener_prestamo_no_existe_falla`: Handle non-existent

3. **Search Operations** (3 tests)
   - `test_obtener_prestamos_cliente_vacio`: Empty result set
   - `test_obtener_prestamos_cliente_multiple`: Multiple results
   - `test_obtener_prestamos_cliente_filtro_estado`: Estado filtering

4. **Update Operations** (2 tests)
   - `test_actualizar_prestamo_tasa`: Update interest rate
   - `test_actualizar_prestamo_observaciones`: Update notes

5. **State Transitions** (4 tests)
   - `test_cambiar_estado_draft_a_aprobado`: DRAFT->APROBADO
   - `test_cambiar_estado_aprobado_a_activo`: APROBADO->ACTIVO
   - `test_cambiar_estado_invalido_falla`: Invalid estado
   - `test_cambiar_estado_illegal_transition_falla`: Illegal transition

6. **Amortization** (3 tests)
   - `test_generar_tabla_amortizacion`: Generate schedule
   - `test_tabla_amortizacion_saldo_final_cero`: Final balance = 0
   - `test_tabla_amortizacion_reproducible`: Consistent generation

7. **Payment Recording** (2 tests)
   - `test_registrar_pago_cuota`: Full payment
   - `test_registrar_pago_parcial`: Partial payment

8. **Summary/Statistics** (3 tests)
   - `test_obtener_resumen_prestamo`: Prestamo summary
   - `test_resumen_prestamo_incluye_amortizacion`: Summary includes amort.
   - `test_obtener_estadistica_prestamos`: Overall statistics

9. **Database Consistency** (3 tests)
   - `test_crear_prestamo_persiste_en_bd`: Persistence
   - `test_actualizar_prestamo_persiste_cambios`: Update persistence
   - `test_amortizacion_creada_en_bd`: Amortization persisted

10. **Edge Cases** (3 tests)
    - `test_prestamo_tasa_cero`: Zero interest
    - `test_prestamo_una_sola_cuota`: Single cuota
    - `test_prestamo_muchas_cuotas`: 360 cuotas (30 years)

11. **Advanced Queries**
    - `test_obtener_prestamos_vencidos`: Overdue loans

### Smoke Tests: test_prestamos_smoke.py

Critical path tests:

1. **CRUD Operations**
   - Create prestamo
   - Read prestamo

2. **State Changes**
   - Change prestamo estado

3. **Amortization**
   - Generate amortization table
   - Complete amortization workflow
   - Payment recording workflow

4. **Query Operations**
   - Search prestamos by cliente
   - Get prestamo summary
   - Get statistics

5. **Workflows**
   - Estado transitions (DRAFT -> APROBADO -> ACTIVO)
   - Complete amortization workflow

6. **Performance**
   - Operations complete in < 5 seconds

7. **Integrity**
   - Database integrity maintained
   - Cuotas created correctly in DB

8. **Error Handling**
   - Invalid cliente error handling

9. **Regeneration**
   - Amortization regenerable

## Fixtures Reference

### Database Fixtures

```python
@pytest.fixture
def db_session(db_engine) -> Generator[Session, None, None]:
    """Test database session with automatic transaction rollback."""
```

- Provides SQLAlchemy Session for test
- Automatically rolls back after test completes
- Ensures test isolation and cleanup

### Model Fixtures

```python
# Cliente fixtures
@pytest.fixture
def test_cliente(db_session: Session, test_cliente_data: dict):
    """Create and insert a test cliente into the database."""

@pytest.fixture
def test_cliente_2(db_session: Session) -> Cliente:
    """Create a second test cliente."""

# Prestamo fixtures
@pytest.fixture
def test_prestamo(db_session: Session, test_prestamo_data: dict):
    """Create and insert a test prestamo into the database."""

@pytest.fixture
def test_prestamo_aprobado(db_session: Session, test_cliente):
    """Create an APROBADO prestamo with amortization table."""

# Cuota fixture
@pytest.fixture
def test_cuota(db_session: Session, test_cuota_data: dict):
    """Create and insert a test cuota."""

# Pago fixtures
@pytest.fixture
def test_pago(db_session: Session, test_pago_data: dict):
    """Create and insert a test pago."""

@pytest.fixture
def test_pago_con_prestamo(db_session: Session, test_cliente, test_prestamo):
    """Create a pago linked to a prestamo."""
```

### Service Fixtures

```python
@pytest.fixture
def prestamos_service(db_session: Session):
    """Provide PrestamosService instance with test DB session."""

@pytest.fixture
def pagos_service(db_session: Session):
    """Provide PagosService instance with test DB session."""

@pytest.fixture
def amortizacion_service(db_session: Session):
    """Provide AmortizacionService instance with test DB session."""
```

### Helper Functions

```python
def create_test_prestamo(
    db_session: Session,
    cliente_id: int,
    total: Decimal = Decimal("10000.00"),
    cuotas: int = 12,
    tasa: Decimal = Decimal("15.5000"),
    estado: str = "DRAFT",
) -> Prestamo:
    """Helper to create a prestamo with common test parameters."""

def create_test_pago(
    db_session: Session,
    cedula: str,
    monto: Decimal = Decimal("500.00"),
    prestamo_id: int = None,
) -> Pago:
    """Helper to create a pago with common test parameters."""
```

## Advanced Testing Patterns

### Testing with Real Database

```python
def test_example(db_session: Session, test_cliente, prestamos_service):
    # All changes happen against real database
    prestamo = prestamos_service.crear_prestamo({
        "cliente_id": test_cliente.id,
        # ...
    })
    
    # Query directly from database to verify
    db_prestamo = db_session.query(Prestamo).filter(
        Prestamo.id == prestamo.id
    ).first()
    
    assert db_prestamo.id == prestamo.id
    # Automatic rollback happens at end of test
```

### Testing State Transitions

```python
def test_prestamo_state_machine(db_session: Session, test_prestamo, prestamos_service):
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
```

### Testing Error Cases

```python
def test_invalid_operation(db_session: Session, prestamos_service):
    with pytest.raises(PrestamoNotFoundError):
        prestamos_service.obtener_prestamo(99999)
    
    with pytest.raises(PrestamoStateError):
        prestamos_service.cambiar_estado_prestamo(
            test_prestamo.id,
            "INVALID_ESTADO"
        )
```

### Testing Amortization Calculations

```python
def test_amortization_math(db_session: Session, test_prestamo_aprobado, prestamos_service):
    tabla = prestamos_service.generar_tabla_amortizacion(test_prestamo_aprobado.id)
    
    # Verify cuota count
    assert len(tabla) == test_prestamo_aprobado.numero_cuotas
    
    # Verify final balance is zero
    ultima_cuota = tabla[-1]
    assert ultima_cuota.get("saldo_vigente") == 0 or abs(float(ultima_cuota.get("saldo_vigente", 0))) < 0.01
    
    # Verify cuotas in database
    cuotas = db_session.query(Cuota).filter(
        Cuota.prestamo_id == test_prestamo_aprobado.id
    ).all()
    
    assert len(cuotas) == test_prestamo_aprobado.numero_cuotas
```

## Database Configuration

### Default Configuration (SQLite In-Memory)

```python
# No configuration needed, tests use :memory: by default
pytest tests/
```

### Using PostgreSQL

```bash
# Set environment variable
export TEST_DATABASE_URL="postgresql://user:password@localhost:5432/test_db"

# Run tests
pytest tests/
```

### Using SQLite File

```bash
export TEST_DATABASE_URL="sqlite:///test_db.sqlite"
pytest tests/
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:14
        env:
          POSTGRES_DB: test_db
          POSTGRES_PASSWORD: test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: |
          pip install -r requirements-test.txt
      
      - name: Run smoke tests
        run: pytest tests/smoke/ -v
      
      - name: Run integration tests
        run: |
          export TEST_DATABASE_URL="postgresql://postgres:test@localhost:5432/test_db"
          pytest tests/integration/ -v
      
      - name: Generate coverage
        run: pytest tests/ --cov=app --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
```

## Troubleshooting

### Common Issues

#### "ModuleNotFoundError: No module named 'app'"

```bash
# Solution: Add current directory to PYTHONPATH
export PYTHONPATH=".:$PYTHONPATH"
pytest tests/

# Or on Windows
set PYTHONPATH=.;%PYTHONPATH%
pytest tests/
```

#### "sqlalchemy.exc.OperationalError: could not connect to server"

```bash
# Solution: Ensure test database is accessible or use in-memory SQLite
# Use SQLite by default (no environment variable needed)
pytest tests/

# Or specify SQLite explicitly
export TEST_DATABASE_URL="sqlite:///:memory:"
pytest tests/
```

#### "ImportError: cannot import name 'Base' from 'app.core.database'"

```bash
# Solution: Ensure app is properly installed or in Python path
pip install -e .
pytest tests/
```

### Debugging Tips

```bash
# Run with verbose output
pytest tests/ -vv

# Show print statements
pytest tests/ -s

# Stop on first failure
pytest tests/ -x

# Run specific test and show full traceback
pytest tests/smoke/test_pagos_smoke.py::TestPagosSmokeTests::test_smoke_crear_pago_basico -vv --tb=long

# Run with debugging
pytest tests/ --pdb  # Drop to debugger on failure
```

## Performance Benchmarks

Expected execution times on typical hardware:

- **Smoke tests**: 20-30 seconds
- **Integration tests**: 30-60 seconds
- **Full suite**: 60-120 seconds
- **Individual test**: < 1 second

If tests are slower, consider:
1. Using in-memory SQLite instead of PostgreSQL
2. Increasing database connection pool
3. Profiling with pytest-benchmark

## Coverage Goals

Current test suite provides:

- **Statement Coverage**: 85%+ of service methods
- **Branch Coverage**: 75%+ of conditional logic
- **Critical Path**: 100% of state transitions and payments

Target improvements:

- Add endpoint (API) tests
- Add error recovery tests
- Add performance regression tests
- Add load testing for concurrent access

## Contributing

When adding new tests:

1. **Test Naming**: Use descriptive names like `test_feature_specific_case`
2. **Documentation**: Add docstring explaining what's being tested
3. **Fixtures**: Use existing fixtures when possible
4. **Grouping**: Place tests in appropriate class
5. **Coverage**: Include both success and error cases
6. **Cleanup**: Verify database state is cleaned up
7. **Performance**: Keep individual tests under 1 second

Example:

```python
def test_crear_pago_valido_detalle(
    db_session: Session, 
    test_cliente, 
    pagos_service
):
    """Test that creating a valid pago stores all required fields correctly.
    
    This test verifies:
    - Pago is created with correct monto
    - All required fields are populated
    - Pago is persisted to database
    - Timestamps are set automatically
    """
    datos = {
        "cliente_id": test_cliente.id,
        "cedula_cliente": test_cliente.cedula,
        "monto_pagado": Decimal("500.00"),
        "referencia_pago": "REF-001",
    }
    
    pago = pagos_service.crear_pago(datos)
    
    # Verify creation
    assert pago.id is not None
    assert pago.monto_pagado == Decimal("500.00")
    
    # Verify persistence
    db_pago = db_session.query(Pago).filter(Pago.id == pago.id).first()
    assert db_pago is not None
    
    # Verify timestamps
    assert db_pago.fecha_registro is not None
```

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [SQLAlchemy Testing](https://docs.sqlalchemy.org/en/20/faq/testing.html)
- [Pydantic Testing](https://docs.pydantic.dev/latest/concepts/testing/)
- [Coverage.py](https://coverage.readthedocs.io/)

## Support

For issues or questions about tests:

1. Check the [README.md](./README.md)
2. Review test examples in the relevant test file
3. Check conftest.py for available fixtures
4. Review the troubleshooting section above
