# Sistema de Permisos y Niveles de Usuarios

## 📋 Resumen Ejecutivo

El sistema tiene **3 roles principales** con acceso diferenciado:

| Rol | Descripción | Acceso |
|-----|-------------|--------|
| **administrador** | Control total del sistema | Portal interno + Finiquito |
| **operativo** | Acceso limitado a reportes | Portal interno (limitado) |
| **finiquitador** | Gestión exclusiva de finiquitos | Portal Finiquito + /pagos/finiquitos/gestion |

---

## 🔐 Rol: ADMINISTRADOR

### Características
- **Acceso Total**: Todas las funcionalidades del portal interno
- **Base de Datos**: Acceso a todos los datos
- **Gestión**: Puede crear, editar, eliminar registros

### Permisos Específicos
✅ Portal interno completo  
✅ Finiquito (gestión completa)  
✅ Auditoria de cartera  
✅ Configuración del sistema  
✅ Gestión de usuarios  
✅ Revisión manual de préstamos  
✅ Rechazo de préstamos  
✅ Regularización de datos  

### Token
- **scope**: `access`
- **Acceso**: `Authorization: Bearer <token>`

---

## 👤 Rol: OPERATIVO

### Características
- **Acceso Limitado**: Solo reportes y préstamos básicos
- **Bloqueos**: 
  - ❌ NO puede acceder a auditoria de cartera
  - ❌ NO puede acceder a finiquitos
  - ❌ NO puede realizar operaciones administrativas

### Permisos Específicos
✅ Reportes (lectura)  
✅ Listado de préstamos (lectura)  
✅ Listado de pagos (lectura)  
✅ Operaciones básicas de lectura  
❌ Auditoria de cartera  
❌ Finiquito  
❌ Revisión manual  
❌ Configuración  

### Token
- **scope**: `access`
- **Acceso**: `Authorization: Bearer <token>`

### Validación en Endpoints
```python
if role not in ("administrador"):
    # Denegar acceso a auditoria/cartera
    raise HTTPException(403, "No disponible para su rol")
```

---

## 💳 Rol: FINIQUITADOR

### Características
- **Especializado**: Gestión exclusiva de finiquitos
- **Portales**: Acceso a portal Finiquito + gestión
- **Flujo**: Revisión → Aceptación → Proceso → Terminado

### Permisos Específicos
✅ Portal Finiquito (público)  
✅ /pagos/finiquitos/gestion (admin)  
✅ Solicitar códigos OTP  
✅ Verificar códigos  
✅ Cambiar estados de casos  
✅ Ver detalles de finiquitos  
❌ Portal interno completo  
❌ Reportes generales  
❌ Gestión de usuarios  

### Token
- **scope**: `finiquito`
- **sub**: ID del usuario en `finiquito_usuario_acceso`
- **Acceso**: Separado del portal interno

### Validación
```python
if payload.get("scope") != "finiquito":
    raise HTTPException(401, "Token no válido para portal Finiquito")
```

---

## 🛡️ Restricciones por Rol

### Auditoria de Cartera
```
ROLES_BLOQUEADOS_AUDITORIA_CARTERA = {"operativo", "usuario", "usuarios"}

✅ administrador - acceso completo
✅ finiquitador - acceso completo
❌ operativo - BLOQUEADO
```

### Finiquito (Gestión)
```
✅ administrador
✅ finiquitador
❌ operativo
```

### Revisión Manual de Préstamos
```
✅ administrador - puede editar siempre
❌ operativo - rechazado si está en revisión
```

---

## 🗄️ Estructura de la Base de Datos

### Tabla: `usuarios`
```sql
CREATE TABLE usuarios (
    id INTEGER PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100),
    cargo VARCHAR(100),
    rol VARCHAR(20) NOT NULL -- 'administrador' | 'operativo' | 'finiquitador'
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);
```

### Tabla: `finiquito_usuario_acceso`
```sql
CREATE TABLE finiquito_usuario_acceso (
    id INTEGER PRIMARY KEY,
    cedula VARCHAR(255),
    email VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    -- Para tokens con scope='finiquito'
);
```

---

## 🔑 Gestión de Tokens

### Access Token (Portal Interno)
```python
payload = {
    "sub": usuario.email,
    "type": "access",
    "scope": "access",  # scope='access' para portal interno
    "iat": timestamp,
    "exp": timestamp + expiration
}
```

### Finiquito Token
```python
payload = {
    "sub": finiquito_usuario.id,
    "type": "access",
    "scope": "finiquito",  # scope='finiquito' para portal Finiquito
    "iat": timestamp,
    "exp": timestamp + expiration
}
```

### Validación
```python
# Endpoint interno
if payload.get("scope") == "finiquito":
    raise HTTPException(401, "Use el token solo en el portal Finiquito")

# Endpoint Finiquito
if payload.get("scope") != "finiquito":
    raise HTTPException(401, "Token no válido para portal Finiquito")
```

---

## 🚀 Endpoints Protegidos por Rol

### Solo Administrador
- `PATCH /pagos/prestamos/{id}/rechazar` - Rechazar préstamo
- `PATCH /pagos/prestamos/{id}/regularizar-tabla-amortizacion` - Regularizar datos
- `GET /auditoria/prestamos/cartera/*` - Auditoria completa
- `POST /configuracion` - Cambios de configuración

### Solo Finiquitador o Administrador
- `PATCH /pagos/finiquitos/gestion/{id}/estado` - Cambiar estado
- `GET /pagos/finiquitos/gestion/*` - Ver gestión
- `POST /pagos/finiquitos/casos` - Crear casos

### Bloqueado para Operativo
- Auditoria de cartera
- Finiquito
- Operaciones administrativas

---

## 📊 Dependencias en FastAPI

### `require_administrador`
```python
def require_administrador(current: UserResponse = Depends(get_current_user)):
    if current.rol.lower() != "administrador":
        raise HTTPException(403, "Solo administradores...")
    return current
```

### `require_finiquitador`
```python
def require_finiquitador(current: UserResponse = Depends(get_current_user)):
    if current.rol.lower() not in ("administrador", "finiquitador"):
        raise HTTPException(403, "Solo finiquitadores...")
    return current
```

### `require_auditoria_cartera_access`
```python
def require_auditoria_cartera_access(current: UserResponse = Depends(get_current_user)):
    if current.rol.lower() in ROLES_BLOQUEADOS_AUDITORIA_CARTERA:
        raise HTTPException(403, "No disponible para su rol")
    return current
```

---

## 🔄 Flujo de Autenticación

```
1. Usuario envía login (email + password)
   ↓
2. Backend valida credenciales
   ↓
3. Backend crea token con rol del usuario
   ↓
4. Frontend almacena token
   ↓
5. Frontend incluye token en cada request: Authorization: Bearer <token>
   ↓
6. Backend valida token y rol en cada endpoint protegido
   ↓
7. Si rol no tiene permisos → 403 Forbidden
```

---

## 💡 Resumen de Permisos

### Tabla Comparativa

| Operación | Admin | Operativo | Finiquitador |
|-----------|-------|-----------|--------------|
| Ver reportes | ✅ | ✅ | ❌ |
| Auditoria cartera | ✅ | ❌ | ✅ |
| Finiquito gestion | ✅ | ❌ | ✅ |
| Rechazar préstamo | ✅ | ❌ | ❌ |
| Revisar manual | ✅ | ⚠️* | ❌ |
| Regularizar datos | ✅ | ❌ | ❌ |
| Configuración | ✅ | ❌ | ❌ |

*⚠️ Operativo puede ver pero no puede editar si está en revisión

---

## 🛠️ Cómo Usar en Endpoints

### Endpoint que requiere admin
```python
from fastapi import Depends
from app.core.deps import require_administrador

@router.delete("/users/{id}")
def delete_user(id: int, current: UserResponse = Depends(require_administrador)):
    # Solo administrador llega aquí
    return {"deleted": id}
```

### Endpoint que requiere admin o finiquitador
```python
from app.core.deps import require_finiquitador

@router.patch("/finiquitos/{id}/estado")
def cambiar_estado(id: int, current: UserResponse = Depends(require_finiquitador)):
    # Solo admin o finiquitador llegan aquí
    return {"estado_actualizado": id}
```

### Endpoint para cualquier usuario autenticado
```python
from app.core.deps import get_current_user

@router.get("/mi-perfil")
def get_perfil(current: UserResponse = Depends(get_current_user)):
    # Cualquier rol autenticado
    return {"user": current}
```

---

## 📝 Notas Importantes

1. **Rol por defecto**: `operativo` - si no se especifica al crear usuario
2. **Usuario admin**: Se puede forzar desde variable de entorno `ADMIN_PASSWORD`
3. **Tokens**: Los tokens se validan en `decode_token()` en `security.py`
4. **Scope**: Diferencia entre `access` (portal interno) y `finiquito` (portal finiquito)
5. **Base de datos**: La BD es única; la separación es por rol y token scope
