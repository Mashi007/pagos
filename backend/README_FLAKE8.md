# Análisis de Código con Flake8

## Instalación

Flake8 ya está instalado en las dependencias de desarrollo. Para instalarlo:

```bash
# Activa tu entorno virtual primero
cd backend
pip install -r requirements/dev.txt
```

## Ejecución

### Opción 1: Usando el script Python
```bash
cd backend
python scripts/analizar_codigo.py
```

### Opción 2: Usando el script Batch (Windows)
```bash
cd backend
.\scripts\ejecutar_flake8.bat
```

### Opción 3: Comando directo
```bash
cd backend
python -m flake8 app --config=setup.cfg
```

## Configuración

La configuración de flake8 está en `backend/setup.cfg`:

- **Longitud máxima de líneas**: 120 caracteres
- **Ignorar errores**: E203, E501, W503, F401, F403
- **Excluir**: migrations, alembic/versions, __pycache__, etc.

## Reglas de Flake8

- **E**: Errores de estilo (pycodestyle)
- **W**: Advertencias de estilo (pycodestyle)
- **F**: Problemas de PyFlakes (imports no usados, variables no definidas, etc.)
- **C**: Complejidad de código (mccabe)
- **N**: Convenciones de nombres (pep8-naming)

## Correcciones Comunes

### Líneas muy largas (>120 caracteres)
```python
# ❌ Malo
mensaje = f"Este es un mensaje muy largo que supera los 120 caracteres y necesita ser dividido en varias líneas"

# ✅ Bueno
mensaje = (
    f"Este es un mensaje muy largo que supera los 120 caracteres "
    f"y necesita ser dividido en varias líneas"
)
```

### Imports no utilizados
```python
# ❌ Malo - import sin usar
from datetime import datetime, timedelta
# timedelta no se usa

# ✅ Bueno
from datetime import datetime
```

### Espacios en blanco innecesarios
```python
# ❌ Malo
def funcion( param1,param2 ):

# ✅ Bueno
def funcion(param1, param2):
```

## Integración con CI/CD

Puedes agregar flake8 a tu pipeline de CI/CD:

```yaml
# Ejemplo para GitHub Actions
- name: Run flake8
  run: |
    cd backend
    pip install -r requirements/dev.txt
    python -m flake8 app --config=setup.cfg
```

