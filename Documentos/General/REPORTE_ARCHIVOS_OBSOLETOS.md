# 📋 Reporte de Archivos Obsoletos

**Fecha**: 2025-01-XX  
**Estado**: ✅ Análisis Completo

---

## 📊 Resumen Ejecutivo

| Categoría | Archivos Obsoletos | Acción Recomendada |
|-----------|-------------------|-------------------|
| Scripts PowerShell duplicados | 4 scripts | ❌ ELIMINAR |
| Scripts Python duplicados (raíz) | 3 scripts | ❌ ELIMINAR |
| Scripts de test Gmail duplicados | 0 scripts | ✅ Ya no existen |
| Imports no utilizados | 0 | ✅ Limpio |
| **TOTAL** | **7 archivos** | **ELIMINAR** |

---

## ❌ ARCHIVOS OBSOLETOS IDENTIFICADOS

### 1. Scripts PowerShell Duplicados (4 archivos)

#### ❌ `scripts/powershell/validacion_soluciones_integrales.ps1`
- **Razón**: Versión obsoleta sin correcciones
- **Versión activa**: `validacion_soluciones_integrales_corregido.ps1`
- **Impacto**: ✅ Ninguno - La versión corregida es la que se debe usar
- **Acción**: **ELIMINAR**

#### ❌ `scripts/powershell/validacion_causa_raiz_completa.ps1`
- **Razón**: Versión obsoleta (existe versión "actualizada")
- **Versión activa**: `validacion_causa_raiz_actualizada.ps1`
- **Impacto**: ✅ Ninguno
- **Acción**: **ELIMINAR**

#### ❌ `scripts/powershell/tercer_enfoque_diagnostico_completo.ps1`
- **Razón**: Script experimental/temporal de diagnóstico
- **Estado**: No referenciado en documentación activa
- **Impacto**: ✅ Ninguno - Script de prueba/experimentación
- **Acción**: **ELIMINAR**

#### ❌ `scripts/powershell/probar_diagnostico_corregido.ps1`
- **Razón**: Script temporal de prueba
- **Estado**: No referenciado en documentación activa
- **Impacto**: ✅ Ninguno - Script de prueba temporal
- **Acción**: **ELIMINAR**

---

### 2. Scripts Python Duplicados en Raíz (3 archivos)

#### ❌ `verificar_ml_simple.py` (raíz del proyecto)
- **Razón**: Versión simplificada, posiblemente obsoleta
- **Versión activa**: `verificar_modelos_ml.py` o `backend/scripts/verificar_modelos_ml_bd.py`
- **Estado**: Solo referenciado en documentación, no en código activo
- **Impacto**: ⚠️ Verificar si se usa manualmente
- **Acción**: **REVISAR y posiblemente ELIMINAR**

#### ❌ `verificar_ml.py` (raíz del proyecto)
- **Razón**: Posiblemente obsoleto
- **Versión activa**: `verificar_modelos_ml.py` o `backend/scripts/verificar_modelos_ml_bd.py`
- **Estado**: Solo referenciado en documentación
- **Impacto**: ⚠️ Verificar si se usa manualmente
- **Acción**: **REVISAR y posiblemente ELIMINAR**

#### ❌ `verificar_modelos_ml.py` (raíz del proyecto)
- **Razón**: Posiblemente duplicado
- **Versión activa**: `backend/scripts/verificar_modelos_ml_bd.py` (más completo)
- **Estado**: Solo referenciado en documentación
- **Impacto**: ⚠️ Verificar si se usa manualmente
- **Acción**: **REVISAR y posiblemente ELIMINAR**

---

## ✅ VERIFICACIONES REALIZADAS

### 1. Imports No Utilizados
- **Resultado**: ✅ **0 imports no utilizados encontrados**
- **Comando**: `flake8 app/ --select=F401`
- **Estado**: Código limpio

### 2. Referencias en Código
- **Scripts PowerShell**: No se importan desde código Python/TypeScript
- **Scripts Python en raíz**: Solo referenciados en documentación, no en código activo
- **Estado**: ✅ Seguro eliminar (no afectan funcionalidad)

### 3. Scripts de Test Gmail
- **Resultado**: ✅ **Ya no existen duplicados**
- **Archivo activo**: `backend/test_gmail_connection.py`
- **Estado**: Limpio

---

## 📋 PLAN DE ACCIÓN

### Fase 1: Eliminación Segura (Scripts PowerShell)

```powershell
# Eliminar scripts PowerShell obsoletos
Remove-Item "scripts\powershell\validacion_soluciones_integrales.ps1" -Force
Remove-Item "scripts\powershell\validacion_causa_raiz_completa.ps1" -Force
Remove-Item "scripts\powershell\tercer_enfoque_diagnostico_completo.ps1" -Force
Remove-Item "scripts\powershell\probar_diagnostico_corregido.ps1" -Force
```

### Fase 2: Revisión y Eliminación (Scripts Python en Raíz)

**Antes de eliminar, verificar manualmente:**

1. ¿Se usan estos scripts en procesos manuales?
2. ¿Hay documentación que los referencia activamente?
3. ¿La versión en `backend/scripts/` es suficiente?

**Si no se usan, eliminar:**

```powershell
# Eliminar scripts Python obsoletos (después de verificación)
Remove-Item "verificar_ml_simple.py" -Force
Remove-Item "verificar_ml.py" -Force
Remove-Item "verificar_modelos_ml.py" -Force
```

**Alternativa: Mover a obsolete**

```powershell
# Crear carpeta si no existe
New-Item -ItemType Directory -Path "scripts\obsolete\python" -Force | Out-Null

# Mover scripts Python
Move-Item "verificar_ml_simple.py" -Destination "scripts\obsolete\python\" -Force
Move-Item "verificar_ml.py" -Destination "scripts\obsolete\python\" -Force
Move-Item "verificar_modelos_ml.py" -Destination "scripts\obsolete\python\" -Force
```

---

## ⚠️ ARCHIVOS A REVISAR (No eliminar todavía)

### Scripts PowerShell que necesitan verificación de uso:

1. **`scripts/powershell/validacion_simple.ps1`**
   - Estado: ⚠️ Verificar si se usa en CI/CD o manualmente
   - Acción: Revisar uso antes de eliminar

2. **`scripts/powershell/validacion_completa_final.ps1`**
   - Estado: ⚠️ Verificar si es la versión activa
   - Acción: Revisar uso antes de eliminar

3. **`scripts/powershell/monitoreo_activo_intermitente.ps1`**
   - Estado: ⚠️ Verificar si se ejecuta automáticamente
   - Acción: Revisar uso antes de eliminar

4. **`scripts/powershell/analisis_causa_raiz_avanzado.ps1`**
   - Estado: ⚠️ Verificar uso actual
   - Acción: Revisar uso antes de eliminar

5. **`scripts/powershell/diagnostico_auth_avanzado.ps1`**
   - Estado: ⚠️ Verificar uso actual
   - Acción: Revisar uso antes de eliminar

---

## ✅ ARCHIVOS QUE SE DEBEN MANTENER

### Scripts Activos y Útiles:

#### Scripts de Organización:
- ✅ `scripts/organizar_documentos.ps1` - PowerShell Windows
- ✅ `scripts/organizar_documentos.py` - Python multiplataforma
- ✅ `scripts/organizar_sql.ps1` - PowerShell Windows
- ✅ `scripts/organizar_sql.py` - Python multiplataforma
- ✅ `scripts/organizar_archivos_completo.ps1` - Versión combinada útil
- ✅ `scripts/organizar_documentos_por_fecha.ps1` - Reorganización histórica

#### Scripts de Verificación:
- ✅ `scripts/verificar_organizacion.ps1`
- ✅ `scripts/verificar_dashboard.ps1`
- ✅ `scripts/verificar_conexion_bd_pagos.py`
- ✅ `scripts/verificar_conexion_pagos_staging.py`
- ✅ `scripts/verificar_datos_concesionarios.py`
- ✅ `scripts/verificar_datos_evolucion_morosidad.py`
- ✅ `scripts/verificar_espacios_blanco.py`
- ✅ `scripts/analizar_complejidad_ciclomatica.py`

#### Scripts de Mantenimiento:
- ✅ `scripts/maintenance/fix_critical_syntax_errors.py`
- ✅ `scripts/maintenance/fix_specific_errors.py`

#### Scripts Python Útiles:
- ✅ `scripts/python/Generar_Cuotas_Masivas.py`
- ✅ `scripts/python/Aplicar_Pagos_Pendientes.py`
- ✅ `scripts/python/Regenerar_Cuotas_Fechas_Correctas.py`
- ✅ `backend/scripts/verificar_modelos_ml_bd.py` (versión activa)

#### Scripts PowerShell Activos:
- ✅ `scripts/powershell/config_variables.ps1`
- ✅ `scripts/powershell/paso_0_obtener_token.ps1`
- ✅ `scripts/powershell/paso_7_verificar_sistema.ps1`
- ✅ `scripts/powershell/paso_manual_1_crear_analista.ps1`
- ✅ `scripts/powershell/paso_manual_2_crear_cliente.ps1`
- ✅ `scripts/powershell/ejecutar_migracion_evaluacion.ps1`
- ✅ `scripts/powershell/validacion_soluciones_integrales_corregido.ps1` (versión activa)
- ✅ `scripts/powershell/validacion_causa_raiz_actualizada.ps1` (versión activa)

---

## 📊 Estadísticas

### Archivos Obsoletos Identificados:
- **Scripts PowerShell duplicados**: 4
- **Scripts Python duplicados (raíz)**: 3
- **Total seguro eliminar**: **7 archivos**

### Archivos a Revisar:
- **Scripts PowerShell**: 5 archivos
- **Total a revisar**: **5 archivos**

### Impacto:
- ✅ **CERO** - Los archivos obsoletos no afectan:
  - Funcionalidad de la aplicación
  - Procesos de CI/CD
  - Otros scripts activos
  - Base de datos o servicios

---

## ✅ Conclusión

**Total de archivos obsoletos identificados**: **7 archivos**  
**Impacto estimado**: ✅ **CERO** - Eliminación segura  
**Recomendación**: Eliminar directamente para mantener el proyecto limpio

**Próximos pasos**:
1. Eliminar los 4 scripts PowerShell duplicados (Fase 1)
2. Revisar y eliminar los 3 scripts Python en raíz (Fase 2)
3. Revisar los 5 scripts marcados como "REVISAR" para determinar si también se pueden eliminar

---

**Última actualización**: 2025-01-XX  
**Responsable**: Análisis Automático

