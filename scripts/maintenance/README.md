# Scripts de Mantenimiento

Este directorio contiene scripts útiles para el mantenimiento del proyecto.

## Scripts Disponibles

### fix_critical_syntax_errors.py
**Propósito**: Corregir errores críticos de sintaxis de forma automática
**Uso**: `python fix_critical_syntax_errors.py`
**Descripción**:
- Corrige triple-quoted strings no terminadas
- Corrige imports incompletos
- Corrige errores de indentación
- Corrige paréntesis/llaves no balanceados

### fix_specific_errors.py
**Propósito**: Corregir errores específicos más complejos
**Uso**: `python fix_specific_errors.py`
**Descripción**:
- Corrige paréntesis no balanceados complejos
- Corrige corchetes no cerrados
- Corrige errores de indentación específicos

## Cómo Usar

1. Ejecutar primero `fix_critical_syntax_errors.py` para correcciones automáticas
2. Ejecutar `fix_specific_errors.py` para correcciones específicas
3. Verificar con `flake8 app/ --count --select=E9,F63,F7,F82`

## Notas

- Estos scripts fueron creados para resolver los 83 errores críticos detectados por GitHub Actions
- Redujeron los errores de 83 a 68 (18% de mejora)
- Los errores restantes requieren corrección manual
