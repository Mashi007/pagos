# Nuevo Rol: Finiquitador - Guía de Implementación

## Descripción

Se ha agregado un nuevo rol de usuario **`finiquitador`** que proporciona acceso **exclusivo** a la página de gestión de finiquito (`/pagos/finiquitos/gestion`). Este rol no puede acceder a otras funcionalidades del sistema.

## Cambios Realizados

### 1. Backend - Alembic Migration
**Archivo**: `backend/alembic/versions/038_add_rol_finiquitador.py`

- Agrega validación del nuevo rol `finiquitador` en la tabla `usuarios`
- Mantiene compatibilidad con roles existentes: `administrador`, `operativo`

**Para aplicar**:
```bash
cd backend
alembic upgrade head
```

### 2. Backend - Dependencies (`deps.py`)
**Archivo**: `backend/app/core/deps.py`

**Agregado**: Nueva función `require_finiquitador()`
```python
def require_finiquitador(current: UserResponse = Depends(get_current_user)) -> UserResponse:
    """Solo rol finiquitador o administrador (acceso exclusivo a finiquito gestion)."""
    rol = (current.rol or "").lower()
    if rol not in ("administrador", "finiquitador"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo finiquitadores y administradores pueden acceder a este recurso.",
        )
    return current
```

### 3. Backend - Endpoints Finiquito (`finiquito.py`)
**Archivo**: `backend/app/api/v1/endpoints/finiquito.py`

**Cambios**:
- `GET /admin/casos` - Usa `require_finiquitador`
- `GET /admin/casos/{caso_id}/revision-datos` - Usa `require_finiquitador`
- `PATCH /admin/casos/{caso_id}/estado` - Usa `require_finiquitador`

**Nota**: Endpoints públicos (`/public/*`) y OTP se mantienen sin cambios.

### 4. Model - Usuario (`user.py`)
**Archivo**: `backend/app/models/user.py`

- Documentación actualizada para incluir el nuevo rol

### 5. Frontend - Permissions Hook (`usePermissions.ts`)
**Archivo**: `frontend/src/hooks/usePermissions.ts`

**Agregado**: Nueva función `isFiniquitador()`
```typescript
const isFiniquitador = (): boolean => {
  const rol = (user?.rol || 'operativo').toLowerCase()
  return rol === 'finiquitador' || rol === 'administrador'
}
```

### 6. Frontend - Página Finiquito (`FiniquitoGestionPage.tsx`)
**Archivo**: `frontend/src/pages/FiniquitoGestionPage.tsx`

**Cambios**:
- Importa `usePermissions` hook
- Verifica `isFiniquitador()` al renderizar
- Muestra mensaje de acceso denegado si el usuario no tiene permisos

## Instalación y Uso

### 1. Aplicar Migración
```bash
cd backend
alembic upgrade head
```

### 2. Crear Usuario con Rol Finiquitador
En la base de datos:
```sql
INSERT INTO usuarios (email, password_hash, nombre, apellido, cargo, rol, is_active)
VALUES (
  'finiquitador@ejemplo.com',
  '<password_hash>',
  'Juan',
  'Pérez',
  'Gestor de Finiquitos',
  'finiquitador',
  true
);
```

O a través de la API (si tienes endpoint de creación de usuarios):
```json
{
  "email": "finiquitador@ejemplo.com",
  "password": "password_seguro",
  "nombre": "Juan",
  "apellido": "Pérez",
  "cargo": "Gestor de Finiquitos",
  "rol": "finiquitador"
}
```

### 3. Verificar Compilación

**Backend**:
```bash
cd backend
python -m pytest tests/  # Si existen tests
```

**Frontend**:
```bash
cd frontend
npm run type-check
npm run lint
```

## Control de Acceso

### Finiquitador
- ✅ Ver casos en gestión de finiquito
- ✅ Filtrar por cédula
- ✅ Cambiar estado de casos (REVISION → ACEPTADO → RECHAZADO)
- ✅ Marcar como EN_PROCESO y TERMINADO
- ✅ Descargar estado de cuenta PDF
- ❌ Acceso a reportes, préstamos, o cualquier otra funcionalidad

### Administrador
- ✅ Acceso total (incluyendo finiquito gestion)
- ✅ Todas las funcionalidades del sistema

### Operativo
- ✅ Reportes limitados
- ✅ Gestión de préstamos
- ❌ Finiquito gestion

## Seguridad

- **Backend**: `require_finiquitador()` valida en cada endpoint
- **Frontend**: `isFiniquitador()` bloquea renderizado si no tiene permisos
- **BD**: Validación CHECK en tabla usuarios limita valores de `rol`

## Reversión

Si necesitas revertir los cambios:

```bash
cd backend
alembic downgrade -1
```

Esto removerá la validación del rol `finiquitador`, pero **los registros de usuarios con este rol permanecerán**. Para limpiar:

```sql
UPDATE usuarios SET rol = 'operativo' WHERE rol = 'finiquitador';
```

## Notas

- Un usuario con rol `finiquitador` que intente acceder a `/pagos/reportes` verá error 403
- Los endpoints públicos de finiquito (`/public/*`) siguen disponibles sin cambios
- El rol se valida en cada petición al backend
- El frontend también valida permisos para mejor UX
