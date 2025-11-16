# Solución al Problema de Congelamiento de Alembic

## Problema Identificado

El comando `alembic` desde la línea de comandos se congelaba repetidamente (32+ intentos), causando:
- Timeouts infinitos
- Errores de configuración (`No 'script_location' key found`)
- Problemas de serialización al importar modelos

## Solución Implementada

Se crearon **3 scripts robustos** que evitan los congelamientos:

### 1. `alembic_robust.py` ⭐ (Recomendado)

**Características:**
- ✅ Timeouts automáticos (30s por defecto, configurable)
- ✅ Usa API de Python directamente (no CLI)
- ✅ Manejo robusto de errores
- ✅ Evita problemas de serialización
- ✅ Configuración automática de directorios y .env

**Uso:**
```bash
cd backend
python scripts/alembic_robust.py current
python scripts/alembic_robust.py heads
python scripts/alembic_robust.py upgrade head
python scripts/alembic_robust.py check
```

**Con timeout personalizado:**
```bash
python scripts/alembic_robust.py upgrade head --timeout 60
```

### 2. `alembic_quick.py` (Uso rápido)

Versión simplificada para comandos rápidos.

**Uso:**
```bash
cd backend
python scripts/alembic_quick.py current
python scripts/alembic_quick.py heads
python scripts/alembic_quick.py upgrade head
```

### 3. `alembic_robust.ps1` (PowerShell)

Script PowerShell que usa `alembic_robust.py` internamente.

**Uso:**
```powershell
cd scripts\powershell
.\alembic_robust.ps1 current
.\alembic_robust.ps1 heads
.\alembic_robust.ps1 upgrade head
```

## Comandos Disponibles

- `current` - Mostrar revisión actual
- `heads` - Mostrar todas las cabezas
- `history` - Mostrar historial
- `upgrade [target]` - Aplicar migraciones
- `downgrade [target]` - Revertir migraciones
- `stamp [target]` - Marcar revisión
- `check` - Verificar estado sin ejecutar

## Prueba Exitosa

El script fue probado exitosamente:
```
[INFO] Ejecutando comando 'check' con timeout de 30s...
[INFO] Heads detectados: 3
[SUCCESS] Comando completado en 3.46s
```

## Ventajas

1. ✅ **No se congela** - Timeouts automáticos previenen bloqueos
2. ✅ **API directa** - Evita problemas de CLI
3. ✅ **Configuración automática** - Detecta directorios y .env
4. ✅ **Windows compatible** - Manejo correcto de codificación UTF-8
5. ✅ **Mensajes claros** - Errores fáciles de entender

## Migración

**❌ Antes (se congelaba):**
```bash
cd backend
alembic current
alembic upgrade head
```

**✅ Ahora (robusto):**
```bash
cd backend
python scripts/alembic_robust.py current
python scripts/alembic_robust.py upgrade head
```

## Archivos Creados

- `backend/scripts/alembic_robust.py` - Script principal robusto
- `backend/scripts/alembic_quick.py` - Versión rápida
- `scripts/powershell/alembic_robust.ps1` - Wrapper PowerShell
- `backend/scripts/README_ALEMBIC_ROBUST.md` - Documentación completa

