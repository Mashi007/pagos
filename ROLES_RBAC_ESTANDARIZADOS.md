# Sistema de Roles Estandarizados RBAC

## Normas Internacionales Aplicadas

- **ISO/IEC 12207**: Processes and tools for software engineering
- **NIST SP 800-53**: Access Control guidelines
- **RFC 2119**: Key words for use in RFCs

---

## 4 Roles Estándar (Jerarquía)

```
┌─────────────────────────────────────────┐
│          ADMIN (Nivel 4)                │  Full System Access
│  - Acceso total                         │
│  - Gestión de usuarios                  │
│  - Configuración del sistema            │
└─────────────────────────────────────────┘
                  ▲
                  │
┌─────────────────────────────────────────┐
│        MANAGER (Nivel 3)                │  Operational Management
│  - Gestión de operaciones               │
│  - Revisión y aprobación                │
│  - Auditoria de cartera                 │
└─────────────────────────────────────────┘
                  ▲
                  │
┌─────────────────────────────────────────┐
│        OPERATOR (Nivel 2)               │  Basic Operations
│  - Crear y editar registros básicos     │
│  - Reportes operacionales               │
│  - Sin acceso a auditoria               │
└─────────────────────────────────────────┘
                  ▲
                  │
┌─────────────────────────────────────────┐
│         VIEWER (Nivel 1)                │  Read-Only Access
│  - Solo lectura                         │
│  - Ver reportes                         │
│  - Sin modificación de datos            │
└─────────────────────────────────────────┘
```

---

## Rol 1: ADMIN

### Características
- **Nivel de Acceso**: 4 (Máximo)
- **Alcance**: Sistema completo
- **Autenticación**: Bearer token con scope='access'

### Permisos

| Función | Permiso |
|---------|---------|
| Portal interno | ✅ Acceso total |
| Gestión de usuarios | ✅ Crear, editar, eliminar |
| Configuración sistema | ✅ Todas las opciones |
| Finiquito gestión | ✅ Acceso total |
| Auditoria de cartera | ✅ Acceso total |
| Revisión manual préstamos | ✅ Crear y editar |
| Rechazo de préstamos | ✅ Autorizado |
| Regularización de datos | ✅ Autorizado |
| Reportes avanzados | ✅ Acceso total |

### Caso de Uso
Administrador del Sistema, Ejecutivo Senior, Director de Operaciones

### SQL Constraint
```sql
WHERE rol = 'admin'
```

---

## Rol 2: MANAGER

### Características
- **Nivel de Acceso**: 3 (Gerencial)
- **Alcance**: Operaciones y reportes
- **Autenticación**: Bearer token con scope='access'

### Permisos

| Función | Permiso |
|---------|---------|
| Portal interno | ✅ Acceso completo |
| Gestión de usuarios | ❌ Bloqueado |
| Configuración sistema | ⚠️ Lectura solo |
| Finiquito gestión | ✅ Acceso total |
| Auditoria de cartera | ✅ Acceso total |
| Revisión manual préstamos | ✅ Crear y editar |
| Rechazo de préstamos | ✅ Autorizado |
| Regularización de datos | ❌ Bloqueado |
| Reportes avanzados | ✅ Acceso total |

### Caso de Uso
Gerente de Cobranza, Supervisor de Operaciones, Jefe de Área

### SQL Constraint
```sql
WHERE rol IN ('admin', 'manager')
```

---

## Rol 3: OPERATOR

### Características
- **Nivel de Acceso**: 2 (Operacional)
- **Alcance**: Operaciones básicas y reportes básicos
- **Autenticación**: Bearer token con scope='access'

### Permisos

| Función | Permiso |
|---------|---------|
| Portal interno | ✅ Acceso limitado |
| Gestión de usuarios | ❌ Bloqueado |
| Configuración sistema | ❌ Bloqueado |
| Finiquito gestión | ❌ Bloqueado |
| Auditoria de cartera | ❌ BLOQUEADO |
| Revisión manual préstamos | ⚠️ Ver solo |
| Rechazo de préstamos | ❌ Bloqueado |
| Regularización de datos | ❌ Bloqueado |
| Reportes básicos | ✅ Acceso total |

### Caso de Uso
Operario, Ejecutivo de Cuenta, Ejecutivo de Cobranza

### SQL Constraint
```sql
WHERE rol IN ('admin', 'manager', 'operator')
```

---

## Rol 4: VIEWER

### Características
- **Nivel de Acceso**: 1 (Mínimo)
- **Alcance**: Solo lectura
- **Autenticación**: Bearer token con scope='access'

### Permisos

| Función | Permiso |
|---------|---------|
| Portal interno | ✅ Acceso lectura |
| Gestión de usuarios | ❌ Bloqueado |
| Configuración sistema | ❌ Bloqueado |
| Finiquito gestión | ❌ Bloqueado |
| Auditoria de cartera | ❌ BLOQUEADO |
| Revisión manual préstamos | ❌ Bloqueado |
| Rechazo de préstamos | ❌ Bloqueado |
| Regularización de datos | ❌ Bloqueado |
| Reportes lectura | ✅ Ver solo |

### Caso de Uso
Consultor, Auditor Externo, Usuario de Demostración

### SQL Constraint
```sql
WHERE rol = 'viewer'
```

---

## Tabla Comparativa Completa

| Operación | Admin | Manager | Operator | Viewer |
|-----------|-------|---------|----------|--------|
| Ver reportes | ✅ | ✅ | ✅ | ✅ |
| Crear reportes | ✅ | ✅ | ⚠️ | ❌ |
| Auditoria cartera | ✅ | ✅ | ❌ | ❌ |
| Finiquito | ✅ | ✅ | ❌ | ❌ |
| Revisar préstamos | ✅ | ✅ | ⚠️* | ❌ |
| Rechazar préstamos | ✅ | ✅ | ❌ | ❌ |
| Regularizar datos | ✅ | ❌ | ❌ | ❌ |
| Gestión usuarios | ✅ | ❌ | ❌ | ❌ |
| Configuración | ✅ | ⚠️ | ❌ | ❌ |
| Eliminar datos | ✅ | ❌ | ❌ | ❌ |

*⚠️ Operator: puede ver pero no editar

---

## Dependencias FastAPI

### require_admin
```python
def require_admin(current: UserResponse = Depends(get_current_user)) -> UserResponse:
    """Solo admin - acceso total"""
    if current.rol.lower() != "admin":
        raise HTTPException(403, "Solo administradores...")
    return current
```
**Uso**: Endpoints críticos del sistema

### require_manager_or_admin
```python
def require_manager_or_admin(current: UserResponse = Depends(get_current_user)) -> UserResponse:
    """Admin o Manager - operaciones críticas"""
    if current.rol.lower() not in ("admin", "manager"):
        raise HTTPException(403, "Se requiere rol gerencial...")
    return current
```
**Uso**: Gestión de operaciones, finiquito

### require_operator_or_higher
```python
def require_operator_or_higher(current: UserResponse = Depends(get_current_user)) -> UserResponse:
    """Admin, Manager u Operator - operaciones básicas"""
    if current.rol.lower() not in ("admin", "manager", "operator"):
        raise HTTPException(403, "Se requiere operario o superior...")
    return current
```
**Uso**: Operaciones básicas

### require_auditoria_cartera_access
```python
def require_auditoria_cartera_access(current: UserResponse = Depends(get_current_user)):
    """Denegado para operator y viewer"""
    if current.rol.lower() in ("operator", "viewer"):
        raise HTTPException(403, "No disponible para su rol...")
    return current
```
**Uso**: Auditoria de cartera

---

## Flujo de Autenticación

```
1. Usuario envía credenciales
   │
   ├─► Validación en BD
   │
   ├─► Se crea token con rol del usuario
   │   ├─ admin    → acceso total
   │   ├─ manager  → gestión operativa
   │   ├─ operator → operaciones básicas
   │   └─ viewer   → lectura
   │
   ├─► Token enviado al cliente
   │
   ├─► Cliente incluye: Authorization: Bearer <token>
   │
   ├─► Backend valida token y rol
   │
   └─► Si rol no tiene permisos → 403 Forbidden
```

---

## Asignación de Roles

### Por Cargo/Posición

| Posición | Rol Recomendado | Justificación |
|----------|-----------------|---------------|
| Director General | admin | Control total |
| Gerente Operaciones | manager | Supervisión |
| Supervisor Área | manager | Gestión equipo |
| Ejecutivo Cobranza | operator | Operaciones |
| Ejecutivo Cuenta | operator | Gestión cliente |
| Analista | viewer | Reportes |
| Auditor | viewer | Revisión |

---

## Cambio de Roles

### Procedimiento de Migración
```sql
-- Migración del rol existente al nuevo
UPDATE usuarios SET rol = 'admin' WHERE rol = 'administrador';
UPDATE usuarios SET rol = 'viewer' WHERE rol = 'operativo';
```

### Validación Post-Migración
```python
roles_validos = {'admin', 'manager', 'operator', 'viewer'}
usuarios = db.query(User).all()

for u in usuarios:
    assert u.rol in roles_validos, f"Usuario {u.email} con rol inválido: {u.rol}"
```

---

## Estándares Aplicados

### RBAC (Role-Based Access Control)
- ✅ Jerarquía clara de roles
- ✅ Principio de menor privilegio
- ✅ Separación de obligaciones

### ISO/IEC 12207
- ✅ Procesos definidos
- ✅ Control de acceso
- ✅ Auditoria de cambios

### NIST SP 800-53
- ✅ AC-2: Account Management
- ✅ AC-3: Access Enforcement
- ✅ AC-6: Least Privilege

### OWASP
- ✅ Autenticación fuerte
- ✅ Autorización granular
- ✅ Auditar accesos

---

## Notas de Implementación

1. **Rol por defecto**: `viewer` (mínimo privilegio)
2. **Cambio de rol**: Requiere operación en BD (no autoservicio)
3. **Tokens**: Incluyen rol al momento de generación
4. **Auditoria**: Todos los cambios de rol se registran en `auditoria`
5. **Sincronización**: Si cambia rol en BD, necesita nuevo login para reflejar

---

## Ejemplos de Uso en Endpoints

```python
# Solo admin
@router.delete("/admin/usuarios/{id}")
def eliminar_usuario(id: int, admin: UserResponse = Depends(require_admin)):
    return {"eliminado": id}

# Admin o Manager
@router.patch("/finiquito/{id}/estado")
def cambiar_estado(id: int, user: UserResponse = Depends(require_manager_or_admin)):
    return {"actualizado": id}

# Cualquier rol autenticado
@router.get("/reportes/mis-datos")
def get_datos(current: UserResponse = Depends(get_current_user)):
    return {"usuario": current}
```

---

## Recursos

- OWASP: https://cheatsheetseries.owasp.org/cheatsheets/Access_Control_Cheat_Sheet.html
- NIST: https://csrc.nist.gov/publications/detail/sp/800-53/rev-5/final
- ISO/IEC 12207: Software and systems engineering
