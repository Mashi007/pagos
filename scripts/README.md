# Scripts del Proyecto

Este directorio contiene todos los scripts organizados por categorías para el mantenimiento y desarrollo del proyecto.

## Estructura de Carpetas

### 📁 maintenance/
Scripts útiles para el mantenimiento del proyecto:
- `fix_critical_syntax_errors.py` - Corregir errores críticos de sintaxis
- `fix_specific_errors.py` - Corregir errores específicos complejos

### 📁 analysis/
Scripts para análisis y diagnóstico del sistema:
- `analisis_integridad_datos.py` - Análisis completo de integridad de datos (Clientes, Préstamos, Pagos, Cuotas)

### 📁 development/
Scripts para desarrollo y testing.

### 📁 powershell/
Scripts de PowerShell para automatización en Windows:
- Scripts de diagnóstico avanzado
- Scripts de validación
- Scripts de configuración

### 📁 obsolete/
Carpeta para scripts obsoletos (actualmente vacía).

## Scripts Principales

### Scripts de Mantenimiento
Los scripts en `maintenance/` son los más importantes para mantener la calidad del código:

1. **fix_critical_syntax_errors.py**
   - Corrige automáticamente errores críticos de sintaxis
   - Útil cuando GitHub Actions detecta errores E999, F63, F7, F82
   - Corrigió 75 archivos automáticamente

2. **fix_specific_errors.py**
   - Corrige errores específicos más complejos
   - Requiere corrección manual para casos especiales
   - Complementa al script anterior

### Scripts de PowerShell
Los scripts en `powershell/` están organizados por funcionalidad:
- **Diagnóstico**: Scripts para diagnosticar problemas del sistema
- **Validación**: Scripts para validar configuraciones y datos
- **Configuración**: Scripts para configurar el entorno

## Uso Recomendado

### Para Análisis de Integridad de Datos

**Script principal:** `analisis_integridad_datos.py`

Este script realiza un análisis completo de la integridad de datos en el sistema:

1. **Análisis de Clientes:**
   - Total de clientes (activos/inactivos)
   - Cédulas duplicadas
   - Clientes sin cédula
   - Emails duplicados

2. **Análisis de Préstamos:**
   - Préstamos por estado
   - Préstamos aprobados sin cuotas
   - Préstamos con número de cuotas inconsistente
   - Préstamos con cédulas sin cliente

3. **Análisis de Pagos:**
   - Pagos por estado
   - Estado de conciliación
   - Pagos con cédulas sin préstamos
   - Pagos sin número de documento

4. **Análisis de Cuotas:**
   - Cuotas por estado
   - Cuotas sin préstamo asociado
   - Relación entre cuotas y pagos

5. **Análisis de Relaciones:**
   - Clientes con/sin préstamos
   - Préstamos con/sin pagos
   - Integridad referencial general

**Ejecución:**

**Windows (PowerShell):**
```powershell
.\scripts\ejecutar_analisis_integridad.ps1
```

**Linux/Mac (Bash):**
```bash
chmod +x scripts/ejecutar_analisis_integridad.sh
./scripts/ejecutar_analisis_integridad.sh
```

**Directamente con Python:**
```bash
python scripts/analisis_integridad_datos.py
```

### Para Corrección de Errores de Sintaxis
```bash
# 1. Ejecutar corrección automática
python scripts/maintenance/fix_critical_syntax_errors.py

# 2. Ejecutar corrección específica
python scripts/maintenance/fix_specific_errors.py

# 3. Verificar resultados
cd backend
flake8 app/ --count --select=E9,F63,F7,F82
```

### Para Diagnóstico del Sistema
```powershell
# Ejecutar diagnóstico completo
.\scripts\powershell\diagnostico_auth_avanzado.ps1
```

## Limpieza Realizada

Se eliminaron **42 scripts obsoletos** del directorio raíz que eran temporales y ya no se necesitaban:
- Scripts de análisis de encoding
- Scripts de corrección de indentación obsoletos
- Scripts de reescritura de archivos
- Scripts de análisis de patrones

## Mantenimiento

- Los scripts vigentes están organizados por categoría
- Cada carpeta tiene su propio README.md con documentación específica
- Los scripts obsoletos se pueden mover a `obsolete/` antes de eliminar
- Mantener actualizada la documentación cuando se agreguen nuevos scripts
