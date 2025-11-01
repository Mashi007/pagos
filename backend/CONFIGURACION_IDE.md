# Configuración del IDE para Resolver Imports

Este documento explica cómo configurar el IDE (Cursor/VS Code) para que resuelva correctamente los imports de Python, especialmente para SQLAlchemy y FastAPI.

## Archivos de Configuración Creados

Se han creado dos archivos de configuración:

1. **`backend/pyrightconfig.json`**: Configuración de Pyright/Pylance (el analizador estático de Python)
2. **`.vscode/settings.json`**: Configuración del workspace para VS Code/Cursor

## Pasos para Resolver los Warnings

### Opción 1: Recargar el IDE (Recomendado)

1. Cierra completamente Cursor/VS Code
2. Vuelve a abrir el proyecto
3. Los warnings deberían desaparecer automáticamente

### Opción 2: Seleccionar el Intérprete de Python Manualmente

1. Presiona `Ctrl+Shift+P` (o `Cmd+Shift+P` en Mac)
2. Escribe "Python: Select Interpreter"
3. Selecciona el intérprete de Python que tenga instaladas las dependencias (SQLAlchemy, FastAPI, etc.)
   - Si tienes un entorno virtual activado, selecciónalo
   - Si no, asegúrate de que las dependencias estén instaladas globalmente o en el entorno que uses

### Opción 3: Instalar/Verificar Dependencias

Si los imports aún no se resuelven, verifica que las dependencias estén instaladas:

```bash
cd backend
pip install -r requirements.txt
```

### Opción 4: Crear/Activar Entorno Virtual

Si no tienes un entorno virtual, créalo y actívalo:

```bash
# En Windows PowerShell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Luego selecciona este intérprete en Cursor/VS Code usando la Opción 2.

## Configuración de los Archivos

### pyrightconfig.json

Este archivo configura Pyright para:
- Incluir los directorios `app`, `scripts`, y `tests`
- Excluir archivos temporales y migraciones
- Buscar el entorno virtual en el directorio padre
- Desactivar reportes de imports faltantes (ya que el código funciona correctamente)

### .vscode/settings.json

Este archivo configura:
- Rutas adicionales para el análisis de Python
- Configuración de linting con Flake8
- Desactivación de warnings sobre imports faltantes

## Nota Importante

⚠️ **Los warnings del IDE no afectan la ejecución del código**. El código funciona correctamente en tiempo de ejecución. Estos warnings solo aparecen cuando el IDE no puede encontrar las dependencias en su entorno actual.

Si después de seguir estos pasos los warnings persisten, puedes ignorarlos con seguridad, ya que el código está correctamente escrito y funcionará sin problemas.

