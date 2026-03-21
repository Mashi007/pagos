# Quick Start: Running Tests

## 30-Second Setup

```bash
# 1. Install test dependencies
pip install pytest sqlalchemy psycopg2-binary pytest-cov

# 2. Run all tests
pytest tests/ -v

# 3. Run smoke tests only (pre-deploy check)
pytest tests/smoke/ -v
```

## One-Command Examples

### Run Everything
```bash
pytest tests/
```

### Run Smoke Tests (< 30 seconds, must pass before deploy)
```bash
pytest tests/smoke/
```

### Run Integration Tests
```bash
pytest tests/integration/
```

### Run Pagos Tests
```bash
pytest tests/ -k pagos -v
```

### Run Prestamos Tests
```bash
pytest tests/ -k prestamos -v
```

### Run with Coverage Report
```bash
pytest tests/ --cov=app --cov-report=html
# Open htmlcov/index.html to view report
```

### Run Specific Test File
```bash
pytest tests/smoke/test_pagos_smoke.py -v
```

### Run Specific Test
```bash
pytest tests/smoke/test_pagos_smoke.py::TestPagosSmokeTests::test_smoke_crear_pago_basico -v
```

## Using Test Runner Scripts

### Linux/Mac
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

### Windows (PowerShell)
```powershell
.\run_tests.ps1 smoke        # Run smoke tests
.\run_tests.ps1 integration  # Run integration tests
.\run_tests.ps1 pagos        # Run pagos tests
.\run_tests.ps1 prestamos    # Run prestamos tests
.\run_tests.ps1 coverage     # Run with coverage report
.\run_tests.ps1 all          # Run all tests
.\run_tests.ps1 all vv       # Run all tests with extra verbosity
```

## Database Configuration

### Default (SQLite in-memory - fastest)
No configuration needed!
```bash
pytest tests/
```

### PostgreSQL
```bash
export TEST_DATABASE_URL="postgresql://user:password@localhost:5432/test_db"
pytest tests/
```

## Common Issues

### "ModuleNotFoundError: No module named 'app'"
```bash
export PYTHONPATH=".:$PYTHONPATH"
pytest tests/
```

### "No tests found"
Ensure you're in the project root directory:
```bash
cd /path/to/pagos
pytest tests/
```

### Slow tests
Use in-memory SQLite (default):
```bash
unset TEST_DATABASE_URL
pytest tests/
```

## Pre-Deploy Checklist

✅ Run smoke tests (must pass):
```bash
pytest tests/smoke/ -v
# Expected: All 20 tests pass in < 30 seconds
```

✅ Run integration tests:
```bash
pytest tests/integration/ -v
# Expected: All 45+ tests pass in < 60 seconds
```

✅ Check coverage:
```bash
pytest tests/ --cov=app --cov-report=term-missing | grep -E "^app|TOTAL"
# Expected: >80% coverage on critical files
```

## Test Suite Overview

| Category | Count | Time | Must Pass |
|----------|-------|------|-----------|
| Smoke Tests | 20 | < 30s | ✅ YES |
| Integration Tests | 45+ | < 60s | ✅ YES |
| Total | 65+ | < 2m | ✅ YES |

### Smoke Tests (Pre-Deploy)
- 10 Pagos tests
- 10 Prestamos tests
- Must complete in < 30 seconds
- Must pass before any deployment

### Integration Tests
- 20+ Pagos integration tests
- 25+ Prestamos integration tests
- Comprehensive coverage of all operations
- Validates database persistence and consistency

## Test Organization

```
tests/
├── conftest.py                   # Shared fixtures
├── integration/                  # Integration tests
│   └── services/
│       ├── pagos/test_*.py       # 20+ tests
│       └── prestamos/test_*.py   # 25+ tests
└── smoke/                        # Critical tests
    ├── test_pagos_smoke.py       # 10 tests
    └── test_prestamos_smoke.py   # 10 tests
```

## Key Fixtures

Available in all tests (from `conftest.py`):

```python
# Database
db_session: Session                          # Test database with auto-rollback

# Models
test_cliente: Cliente                        # Sample cliente
test_prestamo: Prestamo                      # Sample prestamo (DRAFT)
test_prestamo_aprobado: Prestamo             # Sample prestamo (APROBADO)
test_cuota: Cuota                            # Sample cuota
test_pago: Pago                              # Sample pago

# Services
prestamos_service: PrestamosService          # Ready to use
pagos_service: PagosService                  # Ready to use
amortizacion_service: AmortizacionService    # Ready to use
```

## Example Test Usage

```python
def test_criar_pago(db_session: Session, test_cliente, pagos_service):
    """Example test that creates a pago."""
    datos = {
        "cliente_id": test_cliente.id,
        "cedula_cliente": test_cliente.cedula,
        "monto_pagado": Decimal("500.00"),
        "referencia_pago": "REF-001",
    }
    
    pago = pagos_service.crear_pago(datos)
    
    # Assertions
    assert pago.id is not None
    assert pago.monto_pagado == Decimal("500.00")
    
    # Verify in database
    db_pago = db_session.query(Pago).filter(Pago.id == pago.id).first()
    assert db_pago is not None
    
    # Test automatically rolls back after completion
```

## Performance

Typical execution times:

| Operation | Time |
|-----------|------|
| Run 1 smoke test | < 100ms |
| Run all smoke tests (20) | 15-30s |
| Run all integration tests (45+) | 30-60s |
| Full suite (65+) | < 2 minutes |

## CI/CD Integration

Ready for GitHub Actions, GitLab CI, Jenkins, etc.

Example GitHub Actions:
```yaml
- name: Run Smoke Tests
  run: pytest tests/smoke/ -v
```

## Additional Resources

- **Comprehensive Guide**: [TESTING_GUIDE.md](./TESTING_GUIDE.md)
- **Test Reference**: [tests/README.md](./tests/README.md)
- **Implementation Summary**: [TEST_SUITE_SUMMARY.md](./TEST_SUITE_SUMMARY.md)

## Support

For more information:
1. Check [TESTING_GUIDE.md](./TESTING_GUIDE.md) for detailed documentation
2. Review test files in `tests/` directory
3. Check [conftest.py](./tests/conftest.py) for available fixtures
4. Review example tests in `tests/smoke/` for patterns

---

**Ready to test!** 🚀

Start with smoke tests:
```bash
pytest tests/smoke/ -v
```
