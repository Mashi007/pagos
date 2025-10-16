# 🔧 Solución al Error de Enum de Roles en Producción

## 🔴 Problema Identificado

Los logs de producción muestran el error:

```
LookupError: 'ADMINISTRADOR_GENERAL' is not among the defined enum values. 
Enum name: userrole. Possible values: USER
```

### Causa Raíz

1. **En el código**: El sistema fue actualizado para usar solo el rol `USER`
2. **En la base de datos**: Existen usuarios con roles antiguos (`ADMINISTRADOR_GENERAL`, `GERENTE`, `COBRANZAS`)
3. **Conflicto**: El enum de PostgreSQL aún contiene los valores antiguos, pero SQLAlchemy intenta leer usuarios con esos roles

## ✅ Solución Implementada

Se crearon 3 herramientas para resolver el problema:

### 1. Migración de Alembic
**Archivo**: `backend/alembic/versions/002_migrate_to_single_role.py`

Migración automática que:
- Actualiza todos los usuarios al rol `USER`
- Modifica el enum de PostgreSQL
- Elimina el usuario `admin@financiamiento.com`
- Verifica el usuario `itmaster@rapicreditca.com`

### 2. Script de Python
**Archivo**: `backend/scripts/run_migration_production.py`

Script standalone para ejecutar en el servidor:
```bash
cd backend
python scripts/run_migration_production.py
```

### 3. Endpoint de Emergencia (RECOMENDADO)
**Archivo**: `backend/app/api/v1/endpoints/emergency_migrate_roles.py`

Endpoints disponibles:

#### a) Verificar estado actual
```bash
GET https://pagos-f2qf.onrender.com/api/v1/emergency/check-roles
```

Respuesta esperada:
```json
{
  "necesita_migracion": true,
  "distribucion_roles": {
    "ADMINISTRADOR_GENERAL": 1,
    "USER": 0
  },
  "enum_valores": ["ADMINISTRADOR_GENERAL", "GERENTE", "COBRANZAS", "USER"],
  "usuarios_clave": [...],
  "mensaje": "⚠️ Ejecutar /emergency/migrate-roles"
}
```

#### b) Ejecutar migración
```bash
POST https://pagos-f2qf.onrender.com/api/v1/emergency/migrate-roles
```

Respuesta esperada:
```json
{
  "status": "success",
  "message": "Migración de roles completada exitosamente",
  "estado_inicial": {"ADMINISTRADOR_GENERAL": 1},
  "estado_final": {"USER": 1},
  "usuarios_actualizados": 1,
  "usuarios_eliminados": 0,
  "acciones": [
    "✅ Todos los usuarios migrados a rol USER",
    "✅ Enum actualizado a solo USER",
    "✅ Usuario itmaster@rapicreditca.com verificado"
  ],
  "siguiente_paso": "⚠️ ELIMINAR este endpoint del código y hacer redeploy"
}
```

## 📋 Pasos para Ejecutar la Solución

### Opción A: Usando el Endpoint (MÁS FÁCIL)

1. **Verificar el estado actual**:
   ```bash
   curl https://pagos-f2qf.onrender.com/api/v1/emergency/check-roles
   ```

2. **Ejecutar la migración**:
   ```bash
   curl -X POST https://pagos-f2qf.onrender.com/api/v1/emergency/migrate-roles
   ```

3. **Verificar que funcionó**:
   ```bash
   curl https://pagos-f2qf.onrender.com/api/v1/emergency/check-roles
   ```
   
   Debe mostrar: `"necesita_migracion": false`

4. **Hacer commit y push** para deployar la nueva versión
5. **Eliminar el endpoint de emergencia** después del deploy

### Opción B: Usando Alembic (Servidor con acceso directo)

Si tienes acceso SSH al servidor:

```bash
cd backend
alembic upgrade head
```

### Opción C: Usando el Script Python (Servidor con acceso directo)

Si tienes acceso SSH al servidor:

```bash
cd backend
python scripts/run_migration_production.py
```

## 🧹 Limpieza Post-Migración

Después de ejecutar exitosamente la migración:

1. **Eliminar archivos temporales**:
   ```bash
   rm backend/app/api/v1/endpoints/emergency_migrate_roles.py
   rm backend/scripts/run_migration_production.py
   ```

2. **Actualizar `main.py`**:
   Remover la línea:
   ```python
   emergency_migrate_roles,
   ```
   Y:
   ```python
   app.include_router(emergency_migrate_roles.router, ...)
   ```

3. **Commit y push**:
   ```bash
   git add .
   git commit -m "feat: Limpieza post-migración de roles"
   git push origin main
   ```

## 🔍 Verificación Final

Después de la migración, verificar:

1. ✅ **Login funcional**: `itmaster@rapicreditca.com` puede iniciar sesión
2. ✅ **Endpoints funcionan**: `/api/v1/clientes/` responde sin errores
3. ✅ **No hay errores de enum** en los logs
4. ✅ **Base de datos limpia**: Solo rol `USER` existe

## 🚨 Notas Importantes

- ⚠️ **Esta migración es irreversible en producción**
- ⚠️ **NO requiere autenticación** por ser endpoint de emergencia
- ⚠️ **Ejecutar solo UNA vez**
- ⚠️ **Eliminar el endpoint después de usar**
- ✅ **Es seguro ejecutar**: Usa transacciones y rollback en caso de error
- ✅ **Hace backup lógico**: Muestra el estado inicial antes de modificar

## 📊 Impacto Esperado

### Antes de la Migración
- ❌ Error en cada request: `LookupError: 'ADMINISTRADOR_GENERAL' is not among...`
- ❌ Connection timeout por pool bloqueado
- ❌ Sistema inaccesible

### Después de la Migración
- ✅ Todos los endpoints funcionan
- ✅ Login exitoso
- ✅ Sin errores de roles
- ✅ Sistema completamente funcional

## 🔗 Archivos Relacionados

- `backend/alembic/versions/002_migrate_to_single_role.py` - Migración de Alembic
- `backend/scripts/run_migration_production.py` - Script standalone
- `backend/app/api/v1/endpoints/emergency_migrate_roles.py` - Endpoint de emergencia
- `backend/app/main.py` - Registro del endpoint
- `backend/app/core/permissions.py` - Sistema de permisos simplificado
- `backend/app/models/user.py` - Modelo de usuario
- `backend/app/schemas/user.py` - Schemas de usuario

## 📞 Contacto

Si tienes problemas ejecutando la migración, revisa los logs y verifica:
1. Conexión a base de datos funcional
2. Permisos para modificar tablas y enums
3. Espacio suficiente en disco
4. No hay otros procesos bloqueando la tabla `usuarios`

