# Scripts Robustos de Alembic

## Problema Resuelto

Los scripts anteriores se congelaban al ejecutar comandos de Alembic. Estos nuevos scripts resuelven el problema usando:

1. **API de Python directamente** (no CLI)
2. **Timeouts** para evitar congelamientos
3. **Manejo robusto de errores**
4. **Configuración automática** de directorios y variables de entorno

## Scripts Disponibles

### 1. `alembic_robust.py` (Recomendado)

Script completo con timeouts y manejo de errores avanzado.

**Uso desde Python:**
```bash
cd backend
python scripts/alembic_robust.py current
python scripts/alembic_robust.py heads
python scripts/alembic_robust.py upgrade head
python scripts/alembic_robust.py check
```

**Opciones:**
- `--timeout N` - Cambiar timeout (default: 30 segundos)
- `--sql` - Mostrar SQL sin ejecutar
- `--verbose, -v` - Modo verbose

**Ejemplo con timeout personalizado:**
```bash
python scripts/alembic_robust.py upgrade head --timeout 60
```

### 2. `alembic_quick.py` (Uso rápido)

Versión simplificada para comandos rápidos sin timeouts complejos.

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
.\alembic_robust.ps1 upgrade head -Timeout 60
```

## Comandos Disponibles

- `current` - Mostrar revisión actual
- `heads` - Mostrar todas las cabezas de migración
- `history` - Mostrar historial completo
- `upgrade [target]` - Aplicar migraciones (default: head)
- `downgrade [target]` - Revertir migraciones (default: -1)
- `stamp [target]` - Marcar revisión sin ejecutar
- `check` - Verificar estado sin ejecutar migraciones

## Ventajas sobre CLI de Alembic

1. ✅ **No se congela** - Timeouts automáticos
2. ✅ **Mejor manejo de errores** - Mensajes claros
3. ✅ **Configuración automática** - Detecta directorios y .env
4. ✅ **Funciona en Windows** - Manejo correcto de codificación
5. ✅ **API directa** - Evita problemas de serialización

## Solución de Problemas

### Si el script se congela

1. Aumenta el timeout:
   ```bash
   python scripts/alembic_robust.py current --timeout 60
   ```

2. Verifica que DATABASE_URL esté configurada:
   ```bash
   echo $env:DATABASE_URL  # PowerShell
   ```

3. Usa `alembic_quick.py` para comandos simples:
   ```bash
   python scripts/alembic_quick.py current
   ```

### Si hay errores de configuración

1. Verifica que `alembic.ini` existe en `backend/`
2. Verifica que `.env` existe y tiene `DATABASE_URL`
3. Asegúrate de estar en el directorio `backend/` al ejecutar

## Migración desde CLI

**Antes (se congelaba):**
```bash
cd backend
alembic current
alembic upgrade head
```

**Ahora (robusto):**
```bash
cd backend
python scripts/alembic_robust.py current
python scripts/alembic_robust.py upgrade head
```

O desde PowerShell:
```powershell
cd scripts\powershell
.\alembic_robust.ps1 current
.\alembic_robust.ps1 upgrade head
```

