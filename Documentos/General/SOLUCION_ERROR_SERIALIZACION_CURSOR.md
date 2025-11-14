# 🔧 Solución al Error de Serialización de Cursor con Alembic

## 📋 Problema

Cuando intentas trabajar con migraciones de Alembic en Cursor, aparece este error:

```
ConnectError: [internal] Serialization error in aiserver.v1.StreamUnifiedChatRequestWithTools
```

Este es un **error interno de Cursor**, no un problema con tu código. Ocurre cuando Cursor intenta procesar un contexto muy grande o hay problemas de conexión con los servidores.

## ✅ Soluciones

### Solución 1: Usar el Script Helper de Python (NUEVO - Recomendado)

He creado un script helper que ejecuta Alembic correctamente desde cualquier directorio:

```powershell
# Desde la raíz del proyecto o desde backend/
cd backend
python scripts/alembic_helper.py current
python scripts/alembic_helper.py heads
python scripts/alembic_helper.py upgrade head
```

**Ventajas:**
- ✅ No requiere cambiar de directorio manualmente
- ✅ Evita problemas de serialización
- ✅ Funciona desde cualquier ubicación

**Comandos disponibles:**
```powershell
python scripts/alembic_helper.py current      # Ver migración actual
python scripts/alembic_helper.py heads        # Ver migraciones disponibles
python scripts/alembic_helper.py history     # Ver historial
python scripts/alembic_helper.py upgrade head # Ejecutar migraciones
python scripts/alembic_helper.py downgrade -1 # Revertir última migración
```

### Solución 2: Usar el Script de PowerShell (Alternativa)

He creado un script que ejecuta las migraciones directamente sin depender de Cursor:

```powershell
# Desde la raíz del proyecto
.\scripts\powershell\ejecutar_migraciones_alembic.ps1
```

**Opciones disponibles:**

```powershell
# Ejecutar todas las migraciones pendientes
.\scripts\powershell\ejecutar_migraciones_alembic.ps1

# Verificar migraciones (sintaxis, dependencias, etc.)
.\scripts\powershell\ejecutar_migraciones_alembic.ps1 -Check

# Ver historial de migraciones
.\scripts\powershell\ejecutar_migraciones_alembic.ps1 -History

# Ver migración actual aplicada
.\scripts\powershell\ejecutar_migraciones_alembic.ps1 -Current

# Ver el SQL que se ejecutará (sin ejecutarlo)
.\scripts\powershell\ejecutar_migraciones_alembic.ps1 -SQL

# Revertir la última migración
.\scripts\powershell\ejecutar_migraciones_alembic.ps1 -Action downgrade -Target -1
```

### Solución 2: Comandos Directos en PowerShell

Si prefieres ejecutar los comandos directamente:

```powershell
# 1. Navegar al directorio backend
cd backend

# 2. Ver estado actual
py -m alembic current

# 3. Ver historial
py -m alembic history

# 4. Ejecutar todas las migraciones pendientes
py -m alembic upgrade head

# 5. Verificar migraciones
python check_migrations.py
```

### Solución 3: Usar Terminal Integrado de Cursor

En lugar de pedirle a Cursor que ejecute los comandos, usa el terminal integrado:

1. Abre el terminal en Cursor (`` Ctrl+` `` o `Terminal > New Terminal`)
2. Ejecuta los comandos manualmente:

```powershell
cd backend
py -m alembic upgrade head
```

### Solución 4: Dividir la Consulta

Si necesitas ayuda de Cursor sobre migraciones específicas:

- ❌ **NO hagas:** "Migra todas las últimas tablas a Alembic"
- ✅ **SÍ haz:** "Crea una migración para la tabla X" (una a la vez)

## 🔍 Verificar Estado de las Migraciones

### Ver qué migraciones están pendientes:

```powershell
cd backend
py -m alembic heads
py -m alembic current
```

### Verificar que todas las migraciones son válidas:

```powershell
cd backend
python check_migrations.py
```

Este script verifica:
- ✅ Sintaxis correcta
- ✅ Dependencias válidas
- ✅ Imports correctos
- ✅ Verificaciones de existencia

## 📝 Migraciones Recientes

Las últimas migraciones creadas son:

1. `20251114_create_documentos_ai` - Tabla para documentos de AI
2. `20251109_endpoint_optimization_indexes` - Índices para optimización de endpoints
3. `20251108_add_updated_at` - Columna updated_at en users
4. `20251108_add_last_login` - Columna last_login en users
5. `20251104_group_by_indexes` - Índices funcionales para GROUP BY
6. `20251104_critical_indexes` - Índices críticos de rendimiento

## ⚠️ Notas Importantes

1. **Variables de Entorno**: Asegúrate de tener configurado tu archivo `.env` en `backend/` con `DATABASE_URL`

2. **Backup**: Siempre haz backup de tu base de datos antes de ejecutar migraciones en producción

3. **Una a la vez**: Si tienes problemas, ejecuta las migraciones una por una en lugar de todas juntas

## 🐛 Si el Error Persiste

Si el error de serialización de Cursor persiste incluso con consultas pequeñas:

1. **Reinicia Cursor**: Cierra y vuelve a abrir Cursor
2. **Limpia la caché**: Cierra Cursor y elimina la carpeta de caché (si es necesario)
3. **Usa el terminal**: Ejecuta los comandos directamente en el terminal sin usar Cursor AI
4. **Reporta el bug**: Si el problema persiste, puede ser un bug de Cursor que deberías reportar

## 📚 Referencias

- [Documentación de Alembic](https://alembic.sqlalchemy.org/)
- [Ejecutar Migraciones](./EJECUTAR_MIGRACIONES.md)
- [Comandos PowerShell](./EJECUTAR_MIGRACIONES_POWERSHELL.md)

