# Flake8 - Análisis de Código Python

## 📋 Descripción

Flake8 es una herramienta para analizar el código Python y detectar problemas de estilo, errores potenciales y violaciones de estándares de codificación.

## 🔧 Instalación

Flake8 y sus extensiones ya están agregadas a `requirements.txt`. Para instalarlos:

```bash
# Desde el directorio raíz del proyecto
pip install -r requirements.txt

# O solo las herramientas de linting
pip install flake8 flake8-docstrings flake8-bugbear flake8-import-order mccabe
```

## ⚙️ Configuración

La configuración de Flake8 se encuentra en:
- `backend/.flake8` - Archivo principal de configuración
- `backend/setup.cfg` - Configuración alternativa (compatible con flake8)

### Configuración Actual:
- **Longitud máxima de línea**: 120 caracteres
- **Excluye**: migrations, __pycache__, tests, alembic/versions
- **Ignora**: E203, E501, W503, F401, F403

## 🚀 Uso

### Ejecutar Flake8 Manualmente

#### Opción 1: Desde línea de comandos
```bash
# Desde el directorio backend
cd backend
python -m flake8 app --config=.flake8 --statistics --count
```

#### Opción 2: Usando scripts incluidos

**Windows (PowerShell):**
```powershell
.\backend\scripts\ejecutar_flake8.ps1
```

**Windows (CMD):**
```cmd
backend\scripts\ejecutar_flake8.bat
```

### Análisis específico de archivos

```bash
# Analizar un archivo específico
python -m flake8 app/api/v1/endpoints/pagos.py

# Analizar un directorio específico
python -m flake8 app/api/v1/endpoints/

# Analizar con estadísticas
python -m flake8 app --statistics --count
```

## 📊 Extensiones Incluidas

1. **flake8**: Herramienta base de análisis
2. **flake8-docstrings**: Verifica documentación de funciones/clases
3. **flake8-bugbear**: Detecta bugs comunes y problemas de seguridad
4. **flake8-import-order**: Verifica el orden de los imports
5. **mccabe**: Análisis de complejidad ciclomática

## 🔍 Códigos de Error Comunes

- **E**: Errores de estilo (PEP 8)
- **W**: Advertencias
- **F**: Pyflakes (errores de sintaxis e imports)
- **C**: Complejidad ciclomática
- **N**: Convenciones de nombres
- **D**: Docstrings

## 📝 Ejemplos

### Analizar todo el proyecto
```bash
python -m flake8 app --config=.flake8
```

### Analizar con detalles
```bash
python -m flake8 app --config=.flake8 --show-source --statistics
```

### Ignorar errores específicos
```bash
python -m flake8 app --ignore=E501,W503
```

## 🔄 Integración con IDE

### VS Code
Agregar a `.vscode/settings.json`:
```json
{
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.flake8Path": "${workspaceFolder}/backend",
  "python.linting.flake8Args": ["--config=.flake8"]
}
```

### PyCharm
1. Ir a Settings → Tools → External Tools
2. Agregar flake8 como herramienta externa
3. Configurar el path al ejecutable flake8

## ⚠️ Notas

- El análisis excluye automáticamente:
  - Migraciones de Alembic
  - Archivos de tests
  - Directorios `__pycache__`
  - Archivos compilados `.pyc`

- Algunos errores pueden ser intencionales y pueden ignorarse según el contexto.

- Los imports no utilizados en `__init__.py` están permitidos.

## 📚 Referencias

- [Documentación oficial de Flake8](https://flake8.pycqa.org/)
- [PEP 8 - Style Guide for Python Code](https://pep8.org/)
- [Flake8 Error Codes](https://flake8.pycqa.org/en/latest/user/error-codes.html)

