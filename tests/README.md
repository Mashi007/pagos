# Pagos and Prestamos Tests

Comprehensive test suite for pagos and prestamos services with integration tests, smoke tests, and fixtures.

## Structure

```
tests/
├── conftest.py                           # Shared pytest configuration and fixtures
├── integration/
│   └── services/
│       ├── pagos/
│       │   └── test_pagos_integration.py     # 20+ integration tests
│       └── prestamos/
│           └── test_prestamos_integration.py # 25+ integration tests
└── smoke/
    ├── test_pagos_smoke.py                   # 10 critical smoke tests
    └── test_prestamos_smoke.py               # 10 critical smoke tests
```

## Running Tests

### Run all tests
```bash
pytest tests/
```

### Run integration tests only
```bash
pytest tests/integration/
```

### Run smoke tests only (must pass before deploy)
```bash
pytest tests/smoke/
```

### Run specific test file
```bash
pytest tests/integration/services/pagos/test_pagos_integration.py
```

### Run with verbose output
```bash
pytest tests/ -v
```

### Run with coverage report
```bash
pytest tests/ --cov=app --cov-report=html
```

### Run pagos tests
```bash
pytest tests/ -k "pagos" -v
```

### Run prestamos tests
```bash
pytest tests/ -k "prestamos" -v
```

### Run specific test
```bash
pytest tests/smoke/test_pagos_smoke.py::TestPagosSmokeTests::test_smoke_crear_pago_basico -v
```

## Database Configuration

### Test Database Setup

The test suite uses a test database configured via `conftest.py`:

- **Default**: SQLite in-memory database (`:memory:`) for fast tests
- **Custom**: Set `TEST_DATABASE_URL` environment variable for PostgreSQL or other database

```bash
# Use PostgreSQL for testing
export TEST_DATABASE_URL="postgresql://user:pass@localhost:5432/test_db"
pytest tests/

# Use SQLite file-based
export TEST_DATABASE_URL="sqlite:///test_db.sqlite"
pytest tests/
```

## Fixtures

### Database Fixtures
- `db_session`: Test database session with automatic rollback after each test
- `db_engine`: Test database engine (session-scoped)

### Model Fixtures
- `test_cliente`: Sample cliente record
- `test_cliente_2`: Second sample cliente
- `test_prestamo`: Sample prestamo in DRAFT state
- `test_prestamo_aprobado`: Sample prestamo in APROBADO state with amortization
- `test_cuota`: Sample cuota
- `test_pago`: Sample pago
- `test_pago_con_prestamo`: Pago linked to prestamo

### Service Fixtures
- `prestamos_service`: PrestamosService instance
- `pagos_service`: PagosService instance
- `amortizacion_service`: AmortizacionService instance

### Data Fixtures
- `test_cliente_data`: Dict with test cliente data
- `test_prestamo_data`: Dict with test prestamo data
- `test_cuota_data`: Dict with test cuota data
- `test_pago_data`: Dict with test pago data

### Helper Functions
- `create_test_prestamo()`: Helper to create prestamos
- `create_test_pago()`: Helper to create pagos

## Test Categories

### Integration Tests

#### Pagos Integration Tests (20+)
- crear_pago with various validations
- obtener_pago operations
- actualizar_pago with field updates
- eliminar_pago
- obtener_pagos_cliente with filtering
- obtener_resumen_pagos and aggregations
- Conciliation workflow
- Transactional integrity
- Edge cases (large amounts, precision, etc.)
- Backward compatibility

#### Prestamos Integration Tests (25+)
- crear_prestamo with validations
- obtener_prestamo operations
- actualizar_prestamo
- State transitions (DRAFT -> APROBADO -> ACTIVO, etc.)
- Amortization table generation and retrieval
- Payment recording and tracking
- Prestamo summary and statistics
- Database consistency and persistence
- Edge cases (zero interest, single cuota, many cuotas)
- Overdue prestamos

### Smoke Tests

#### Pagos Smoke Tests (10)
1. Basic pago creation
2. Read pago
3. Update pago
4. Delete pago
5. Search pagos by cliente
6. Get pago summary
7. Conciliation workflow
8. Performance test
9. Database integrity
10. Transactional consistency

#### Prestamos Smoke Tests (10)
1. Basic prestamo creation
2. Read prestamo
3. Change prestamo estado
4. Generate amortization
5. Search prestamos by cliente
6. Get prestamo summary
7. Get statistics
8. Amortization workflow
9. Payment recording workflow
10. Estado transitions

## Key Testing Patterns

### Transactional Isolation
Each test runs in its own transaction which is rolled back after the test completes:

```python
def test_example(db_session: Session):
    # Changes here won't affect other tests
    pass  # Automatic rollback
```

### Service Testing
Services are tested with real database access:

```python
def test_crear_pago(db_session: Session, test_cliente, pagos_service):
    # pagos_service uses the test db_session
    pago = pagos_service.crear_pago(datos)
    assert pago.id is not None
```

### Fixture Composition
Fixtures build on each other:

```python
# test_prestamo depends on test_cliente
def test_prestamo(db_session: Session, test_cliente):
    prestamo = Prestamo(cliente_id=test_cliente.id, ...)
```

## Best Practices Used

1. **Isolation**: Each test is independent and doesn't affect others
2. **Clarity**: Test names clearly describe what's being tested
3. **Assertions**: Multiple specific assertions per test
4. **Error Testing**: Includes both success and failure cases
5. **Edge Cases**: Tests boundary conditions and special cases
6. **Performance**: Tests include performance assertions
7. **Database Consistency**: Verifies data persistence
8. **Backward Compatibility**: Tests old and new functionality together

## Performance

- Smoke tests: < 30 seconds total
- Integration tests: < 60 seconds total
- Full suite: < 2 minutes

## CI/CD Integration

### GitHub Actions Example
```yaml
- name: Run Smoke Tests
  run: pytest tests/smoke/ -v

- name: Run Integration Tests
  run: pytest tests/integration/ -v

- name: Run All Tests with Coverage
  run: pytest tests/ --cov=app --cov-report=lcov
```

## Troubleshooting

### Database Connection Issues
- Ensure `TEST_DATABASE_URL` is set correctly
- Check PostgreSQL is running if using remote database
- Default SQLite in-memory usually works without setup

### Import Errors
- Ensure `PYTHONPATH` includes project root: `export PYTHONPATH=".:$PYTHONPATH"`
- Verify all models and services are importable

### Test Failures
- Run with `-v` for verbose output: `pytest tests/ -v`
- Run with `--tb=short` for shorter tracebacks
- Check recent code changes in services

## Contributing

When adding new tests:

1. Use descriptive test names starting with `test_`
2. Add docstrings explaining what's being tested
3. Use existing fixtures when possible
4. Group related tests in classes
5. Include both success and failure cases
6. Verify database state changes
7. Keep tests fast (< 1 second each)

## Maintenance

- Review and update fixtures as models change
- Keep test data realistic and up-to-date
- Monitor test performance and optimize slow tests
- Add tests for new service methods
- Maintain backward compatibility test coverage
