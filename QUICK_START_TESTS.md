# Quick Start: Running Tests

## 30-Second Setup

```bash
# 1. Install test dependencies (incluye driver PostgreSQL)
pip install -r requirements-test.txt

# 2. Variables minimas (Settings de la app carga al importar conftest)
export PYTHONPATH="/ruta/al/repo/backend:$PYTHONPATH"
export SECRET_KEY="cadena_aleatoria_de_al_menos_32_caracteres_distintos"
export DATABASE_URL="postgresql+psycopg2://usuario:clave@127.0.0.1:5432/nombre_bd_test"

# 3. Opcional: motor de pytest distinto al de la app
# export TEST_DATABASE_URL="postgresql+psycopg2://..."

# 4. Ejecutar tests
pytest tests/ -v
```

Solo tests unitarios que no usan `db_session` pueden correr sin `create_all`; smoke e integracion necesitan **PostgreSQL** (el modelo usa `JSONB`, incompatible con SQLite).

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

### PostgreSQL (recomendado para smoke / integracion)

`tests/conftest.py` usa, en este orden: **`TEST_DATABASE_URL`**, si no existe **`DATABASE_URL`** si ya es Postgres, y si no **SQLite en memoria** (fallara al crear tablas por tipos `JSONB`).

```bash
export DATABASE_URL="postgresql+psycopg2://user:password@localhost:5432/pagos_test"
export SECRET_KEY="..."   # minimo 32 caracteres, ver validador en Settings
export PYTHONPATH="/abs/path/pagos/backend:$PYTHONPATH"
pytest tests/
```

Solo con Postgres (y `psycopg2-binary` instalado) `Base.metadata.create_all` suele completarse.

### Motor de tests distinto al de la app

```bash
export TEST_DATABASE_URL="postgresql+psycopg2://user:password@localhost:5432/otra_bd_solo_pytest"
pytest tests/
```

## Common Issues

### "ModuleNotFoundError: No module named 'app'"
```bash
export PYTHONPATH="/ruta/al/repo/backend:$PYTHONPATH"
pytest tests/
```

### "No tests found"
Ensure you're in the project root directory:
```bash
cd /path/to/pagos
pytest tests/
```

### Slow tests
Use una base dedicada en Postgres con datos minimos, o ejecute solo un archivo (`pytest tests/unit/...`).

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
