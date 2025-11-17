# 🗑️ Lista de Scripts Eliminables - Proyecto Pagos

**Fecha**: 2025-01-XX
**Estado**: ✅ Verificado - Sin impacto en otros procesos

---

## 📊 Resumen Ejecutivo

| Categoría | Scripts Eliminables | Impacto |
|-----------|---------------------|---------|
| Validación/Diagnóstico Duplicados | 4 scripts | ✅ Ninguno |
| Test Gmail Duplicados | 2 scripts | ✅ Ninguno |
| **TOTAL** | **6 scripts** | ✅ **Seguro eliminar** |

---

## ✅ Scripts que se pueden ELIMINAR de forma segura

### 1. Scripts de Validación/Diagnóstico Duplicados

#### ❌ `scripts/powershell/validacion_soluciones_integrales.ps1`
- **Razón**: Versión obsoleta (existe versión "corregido")
- **Versión activa**: `validacion_soluciones_integrales_corregido.ps1`
- **Impacto**: ✅ Ninguno - La versión corregida es la que se debe usar
- **Acción**: **ELIMINAR**

#### ❌ `scripts/powershell/validacion_causa_raiz_completa.ps1`
- **Razón**: Versión obsoleta (existe versión "actualizada")
- **Versión activa**: `validacion_causa_raiz_actualizada.ps1`
- **Impacto**: ✅ Ninguno - La versión actualizada es la que se debe usar
- **Acción**: **ELIMINAR**

#### ❌ `scripts/powershell/tercer_enfoque_diagnostico_completo.ps1`
- **Razón**: Script experimental/temporal de diagnóstico
- **Estado**: No referenciado en documentación activa
- **Impacto**: ✅ Ninguno - Script de prueba/experimentación
- **Acción**: **ELIMINAR** (o mover a obsolete si se quiere mantener historial)

#### ❌ `scripts/powershell/probar_diagnostico_corregido.ps1`
- **Razón**: Script temporal de prueba
- **Estado**: No referenciado en documentación activa
- **Impacto**: ✅ Ninguno - Script de prueba temporal
- **Acción**: **ELIMINAR** (o mover a obsolete si se quiere mantener historial)

---

### 2. Scripts de Test Gmail Duplicados

#### ❌ `backend/test_gmail_connection_simple.py`
- **Razón**: Versión simplificada (menos funcional que la completa)
- **Versión activa**: `backend/test_gmail_connection.py` (más completa)
- **Impacto**: ✅ Ninguno - La versión completa cubre todas las funcionalidades
- **Acción**: **ELIMINAR**

#### ❌ `backend/test_gmail_quick.py`
- **Razón**: Versión rápida (funcionalidad duplicada)
- **Versión activa**: `backend/test_gmail_connection.py` (más completa y documentada)
- **Impacto**: ✅ Ninguno - La versión completa es preferible
- **Acción**: **ELIMINAR** (o mantener solo si se usa frecuentemente para pruebas rápidas)

---

## ⚠️ Scripts a REVISAR (no eliminar todavía)

### Scripts de Validación que necesitan verificación de uso:

1. **`scripts/powershell/validacion_simple.ps1`**
   - Estado: ⚠️ Verificar si se usa en CI/CD o manualmente
   - Acción: Revisar uso antes de eliminar

2. **`scripts/powershell/validacion_completa_final.ps1`**
   - Estado: ⚠️ Verificar si es la versión activa o si hay otra más reciente
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

## ✅ Scripts que se deben MANTENER

### Scripts de Organización (todos tienen propósitos distintos):
- ✅ `scripts/organizar_documentos.ps1` - PowerShell Windows
- ✅ `scripts/organizar_documentos.py` - Python multiplataforma
- ✅ `scripts/organizar_sql.ps1` - PowerShell Windows
- ✅ `scripts/organizar_sql.py` - Python multiplataforma
- ✅ `scripts/organizar_archivos_completo.ps1` - Versión combinada útil
- ✅ `scripts/organizar_documentos_por_fecha.ps1` - Reorganización histórica

### Scripts de PowerShell Activos (según README):
- ✅ `scripts/powershell/config_variables.ps1`
- ✅ `scripts/powershell/paso_0_obtener_token.ps1`
- ✅ `scripts/powershell/paso_7_verificar_sistema.ps1`
- ✅ `scripts/powershell/paso_manual_1_crear_analista.ps1`
- ✅ `scripts/powershell/paso_manual_2_crear_cliente.ps1`
- ✅ `scripts/powershell/ejecutar_migracion_evaluacion.ps1`

### Scripts de Verificación:
- ✅ `scripts/verificar_organizacion.ps1`
- ✅ `scripts/verificar_dashboard.ps1`
- ✅ `scripts/verificar_conexion_bd_pagos.py`
- ✅ `scripts/verificar_conexion_pagos_staging.py`
- ✅ `scripts/verificar_datos_concesionarios.py`
- ✅ `scripts/verificar_datos_evolucion_morosidad.py`

### Scripts de Test Gmail:
- ✅ `backend/test_gmail_connection.py` - **MANTENER** (versión completa)

---

## 📋 Comandos para Eliminar Scripts

### Eliminar Scripts de Validación Duplicados:

```powershell
# Desde la raíz del proyecto
Remove-Item "scripts\powershell\validacion_soluciones_integrales.ps1" -Force
Remove-Item "scripts\powershell\validacion_causa_raiz_completa.ps1" -Force
Remove-Item "scripts\powershell\tercer_enfoque_diagnostico_completo.ps1" -Force
Remove-Item "scripts\powershell\probar_diagnostico_corregido.ps1" -Force
```

### Eliminar Scripts de Test Gmail Duplicados:

```powershell
# Desde la raíz del proyecto
Remove-Item "backend\test_gmail_connection_simple.py" -Force
Remove-Item "backend\test_gmail_quick.py" -Force
```

### O mover a obsolete (alternativa):

```powershell
# Crear carpeta si no existe
New-Item -ItemType Directory -Path "scripts\obsolete\validacion" -Force | Out-Null
New-Item -ItemType Directory -Path "backend\obsolete" -Force | Out-Null

# Mover scripts de validación
Move-Item "scripts\powershell\validacion_soluciones_integrales.ps1" -Destination "scripts\obsolete\validacion\" -Force
Move-Item "scripts\powershell\validacion_causa_raiz_completa.ps1" -Destination "scripts\obsolete\validacion\" -Force
Move-Item "scripts\powershell\tercer_enfoque_diagnostico_completo.ps1" -Destination "scripts\obsolete\validacion\" -Force
Move-Item "scripts\powershell\probar_diagnostico_corregido.ps1" -Destination "scripts\obsolete\validacion\" -Force

# Mover scripts de test Gmail
Move-Item "backend\test_gmail_connection_simple.py" -Destination "backend\obsolete\" -Force
Move-Item "backend\test_gmail_quick.py" -Destination "backend\obsolete\" -Force
```

---

## ✅ Verificación de Impacto

### Procesos Verificados:

1. **✅ CI/CD Pipeline**
   - No se encontraron referencias a scripts eliminables en workflows
   - Los scripts no están en procesos automatizados

2. **✅ Código de la Aplicación**
   - No se encontraron imports o llamadas a scripts eliminables desde código Python/TypeScript
   - Los scripts son independientes

3. **✅ Documentación**
   - Scripts eliminables no están referenciados en documentación activa
   - Solo referencias históricas en algunos casos

4. **✅ Scripts de Mantenimiento**
   - No hay dependencias entre scripts eliminables y activos
   - Los scripts activos no dependen de los eliminables

### Conclusión:

✅ **SEGURO ELIMINAR** - Los 6 scripts identificados son independientes y no afectan:
- Funcionalidad de la aplicación
- Procesos de CI/CD
- Otros scripts activos
- Base de datos o servicios

---

## 📝 Notas Finales

- **Scripts ya archivados**: Los 5 scripts de Cursor ya fueron movidos a `scripts/obsolete/cursor/`
- **Recomendación**: Eliminar directamente (no mover a obsolete) para mantener el proyecto limpio
- **Alternativa**: Si prefieres mantener historial, mover a `scripts/obsolete/` en lugar de eliminar
- **Próximo paso**: Revisar los 5 scripts marcados como "REVISAR" para determinar si también se pueden eliminar

---

**Total de scripts eliminables identificados**: **6 scripts**
**Impacto estimado**: ✅ **CERO** - Eliminación segura

