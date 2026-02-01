# 🔐 Auditoría Integral del Sistema de Login

**Fecha de Auditoría**: 2026-02-01  
**Auditor**: Sistema Automatizado  
**Alcance**: Análisis completo de autenticación, autorización y seguridad del sistema de login

---

## 📋 Resumen Ejecutivo

### Estado Actual
- ❌ **Sistema de login NO implementado**: No existe código de autenticación de usuarios
- ✅ **Configuración base presente**: Variables de entorno para JWT configuradas
- ✅ **Dependencias de seguridad disponibles**: PyJWT, bcrypt, passlib instalados
- ✅ **Autenticación parcial**: Solo webhooks de WhatsApp implementados

### Nivel de Riesgo General
**🔴 ALTO** - La ausencia de un sistema de login implementado representa un riesgo crítico si la aplicación maneja datos sensibles o requiere autenticación de usuarios.

---

## 🔍 Análisis Detallado

### 1. Estado de Implementación

#### 1.1 Sistema de Autenticación de Usuarios
**Estado**: ❌ NO IMPLEMENTADO

**Hallazgos**:
- No existen endpoints de login (`/api/v1/auth/login`)
- No existe endpoint de registro (`/api/v1/auth/register`)
- No existe endpoint de refresh token (`/api/v1/auth/refresh`)
- No existe endpoint de logout (`/api/v1/auth/logout`)
- No existe middleware de autenticación JWT
- No existen modelos de base de datos para usuarios (`User`, `Session`, `RefreshToken`)
- No existen schemas Pydantic para autenticación (`LoginRequest`, `TokenResponse`)

**Archivos que deberían existir pero NO existen**:
```
backend/app/api/v1/endpoints/auth.py          ❌ NO EXISTE
backend/app/core/security.py                  ❌ NO EXISTE (solo security_whatsapp.py)
backend/app/models/user.py                    ❌ NO EXISTE
backend/app/schemas/auth.py                   ❌ NO EXISTE
backend/app/services/auth_service.py          ❌ NO EXISTE
```

#### 1.2 Configuración de Seguridad
**Estado**: ⚠️ PARCIALMENTE CONFIGURADA

**Variables de entorno configuradas** (`backend/app/core/config.py`):
```python
✅ SECRET_KEY: str                    # Requerida - Clave secreta para JWT
✅ ALGORITHM: str = "HS256"           # Configurado correctamente
✅ ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # Configurado
```

**Problemas identificados**:
1. ⚠️ **SECRET_KEY no validada**: No hay validación de complejidad mínima
2. ⚠️ **No hay configuración de refresh token**: Falta `REFRESH_TOKEN_EXPIRE_DAYS`
3. ⚠️ **No hay rate limiting configurado**: Falta configuración de límites de intentos de login
4. ⚠️ **No hay configuración de bloqueo de cuenta**: Falta `MAX_LOGIN_ATTEMPTS`, `LOCKOUT_TIME`

#### 1.3 Dependencias de Seguridad
**Estado**: ✅ ADECUADAS

**Dependencias instaladas** (`requirements.txt`):
```python
✅ PyJWT==2.8.0              # Para generación/validación de tokens JWT
✅ passlib[bcrypt]==1.7.4    # Para hashing de contraseñas
✅ bcrypt==4.1.1              # Algoritmo de hashing seguro
✅ cryptography>=41.0.0      # Para encriptación adicional
✅ slowapi==0.1.9             # Para rate limiting (no configurado)
```

**Versiones**: Todas las versiones son actuales y seguras.

---

### 2. Análisis de Vulnerabilidades

#### 2.1 Vulnerabilidades Críticas

##### 🔴 CRIT-001: Ausencia de Sistema de Autenticación
**Severidad**: CRÍTICA  
**Descripción**: No existe implementación de autenticación de usuarios.

**Impacto**:
- Cualquier usuario puede acceder a endpoints protegidos si se implementan sin autenticación
- No hay control de acceso a datos sensibles
- No hay trazabilidad de acciones de usuarios

**Recomendación**: Implementar sistema completo de autenticación JWT.

##### 🔴 CRIT-002: SECRET_KEY Sin Validación
**Severidad**: CRÍTICA  
**Descripción**: La `SECRET_KEY` no tiene validación de complejidad mínima.

**Código actual** (`backend/app/core/config.py:32-35`):
```python
SECRET_KEY: str = Field(
    ...,
    description="Clave secreta para JWT"
)
```

**Problemas**:
- No valida longitud mínima (debería ser ≥ 32 caracteres)
- No valida complejidad (debería ser aleatoria y segura)
- Permite valores débiles como "secret" o "123456"

**Recomendación**: Agregar validación de `SECRET_KEY`:
```python
@validator('SECRET_KEY')
def validate_secret_key(cls, v):
    if len(v) < 32:
        raise ValueError('SECRET_KEY debe tener al menos 32 caracteres')
    if v.lower() in ['secret', 'password', '123456', 'admin']:
        raise ValueError('SECRET_KEY no puede ser un valor común')
    return v
```

#### 2.2 Vulnerabilidades Altas

##### 🟠 HIGH-001: Comparación de Tokens No Segura
**Severidad**: ALTA  
**Descripción**: En `whatsapp.py:50` se compara token con `==` en lugar de comparación timing-safe.

**Código actual** (`backend/app/api/v1/endpoints/whatsapp.py:50`):
```python
if hub_mode == "subscribe" and hub_verify_token == verify_token:
```

**Problema**: Comparación con `==` es vulnerable a timing attacks.

**Recomendación**: Usar `secrets.compare_digest()`:
```python
import secrets
if hub_mode == "subscribe" and secrets.compare_digest(hub_verify_token, verify_token):
```

**Nota**: Ya se usa `hmac.compare_digest()` en `security_whatsapp.py:47` ✅ (correcto)

##### 🟠 HIGH-002: Falta Rate Limiting en Endpoints
**Severidad**: ALTA  
**Descripción**: No hay rate limiting configurado en ningún endpoint.

**Impacto**:
- Vulnerable a ataques de fuerza bruta en login (cuando se implemente)
- Vulnerable a DoS por spam de requests
- No hay protección contra abuso de API

**Recomendación**: Configurar `slowapi` para rate limiting:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@router.post("/login")
@limiter.limit("5/minute")  # Máximo 5 intentos por minuto
async def login(...):
    ...
```

#### 2.3 Vulnerabilidades Medias

##### 🟡 MED-001: Logging de Información Sensible
**Severidad**: MEDIA  
**Descripción**: Se loguea información parcial de tokens que podría ser útil para atacantes.

**Código actual** (`backend/app/api/v1/endpoints/whatsapp.py:57`):
```python
f"Token recibido: {hub_verify_token[:5]}..."
```

**Problema**: Aunque solo muestra 5 caracteres, cualquier información sobre tokens puede ser útil para atacantes.

**Recomendación**: Solo loguear en modo DEBUG, no en WARNING:
```python
logger.debug(f"Token recibido: {hub_verify_token[:5]}...")
```

##### 🟡 MED-002: Manejo de Errores Expone Información
**Severidad**: MEDIA  
**Descripción**: Algunos mensajes de error pueden exponer información del sistema.

**Código actual** (`backend/app/api/v1/endpoints/whatsapp.py:64`):
```python
raise HTTPException(status_code=500, detail="Error verificando webhook")
```

**Problema**: En producción, los errores 500 no deberían exponer detalles internos.

**Recomendación**: Usar mensajes genéricos en producción:
```python
detail = "Error interno del servidor" if not settings.DEBUG else str(e)
```

#### 2.4 Vulnerabilidades Bajas

##### 🟢 LOW-001: Falta Validación de Expiración de Tokens
**Severidad**: BAJA  
**Descripción**: No hay código que valide expiración de tokens (porque no hay tokens implementados).

**Recomendación**: Cuando se implemente JWT, validar expiración:
```python
from datetime import datetime, timedelta
import jwt

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt
```

##### 🟢 LOW-002: Falta Rotación de SECRET_KEY
**Severidad**: BAJA  
**Descripción**: No hay mecanismo para rotar `SECRET_KEY` sin invalidar todos los tokens.

**Recomendación**: Implementar sistema de rotación de claves (para futuro).

---

### 3. Revisión de Seguridad de Webhooks (Referencia)

#### 3.1 Verificación de Firma de Webhook
**Estado**: ✅ BIEN IMPLEMENTADO

**Código** (`backend/app/core/security_whatsapp.py:12-51`):
- ✅ Usa `hmac.compare_digest()` (timing-safe)
- ✅ Valida firma SHA256 correctamente
- ✅ Maneja errores apropiadamente
- ⚠️ Solo verifica si `app_secret` está configurado (opcional)

**Recomendación**: Hacer obligatoria la verificación de firma en producción:
```python
if not app_secret:
    if not settings.DEBUG:
        raise HTTPException(status_code=500, detail="App Secret no configurado")
    logger.warning("App Secret no configurado - modo desarrollo")
```

#### 3.2 Validación de Token de Verificación
**Estado**: ⚠️ MEJORABLE

**Problema**: Usa comparación directa `==` en lugar de `secrets.compare_digest()`.

**Recomendación**: Ya mencionada en HIGH-001.

---

### 4. Recomendaciones para Implementación Segura

#### 4.1 Arquitectura Recomendada

```
backend/app/
├── api/v1/endpoints/
│   └── auth.py                    # Endpoints: login, register, refresh, logout
├── core/
│   └── security.py                # Funciones: create_token, verify_token, get_current_user
├── models/
│   └── user.py                    # Modelo User (SQLAlchemy)
├── schemas/
│   └── auth.py                    # Schemas: LoginRequest, TokenResponse, UserResponse
└── services/
    └── auth_service.py            # Lógica de negocio: authenticate_user, create_user
```

#### 4.2 Checklist de Implementación

##### Fase 1: Configuración Base
- [ ] Validar `SECRET_KEY` con longitud mínima de 32 caracteres
- [ ] Agregar `REFRESH_TOKEN_EXPIRE_DAYS` a configuración
- [ ] Agregar `MAX_LOGIN_ATTEMPTS` y `LOCKOUT_TIME` a configuración
- [ ] Configurar rate limiting con `slowapi`

##### Fase 2: Modelos de Base de Datos
- [ ] Crear modelo `User` con campos:
  - `id`, `email`, `username`, `hashed_password`
  - `is_active`, `is_superuser`, `created_at`, `updated_at`
  - `failed_login_attempts`, `locked_until`
- [ ] Crear modelo `RefreshToken` con campos:
  - `id`, `user_id`, `token`, `expires_at`, `created_at`
- [ ] Crear migraciones Alembic

##### Fase 3: Schemas Pydantic
- [ ] `LoginRequest`: `username/email`, `password`
- [ ] `RegisterRequest`: `email`, `username`, `password`, `password_confirm`
- [ ] `TokenResponse`: `access_token`, `refresh_token`, `token_type`, `expires_in`
- [ ] `UserResponse`: `id`, `email`, `username`, `is_active`, `created_at`
- [ ] Validaciones: email válido, password fuerte (min 8 chars, mayúsculas, números)

##### Fase 4: Servicios
- [ ] `authenticate_user()`: Verificar credenciales con bcrypt
- [ ] `create_user()`: Crear usuario con password hasheado
- [ ] `create_access_token()`: Generar JWT con expiración
- [ ] `create_refresh_token()`: Generar refresh token
- [ ] `verify_token()`: Validar y decodificar JWT
- [ ] `get_user_by_token()`: Obtener usuario desde token

##### Fase 5: Endpoints
- [ ] `POST /api/v1/auth/register`: Registro de usuarios
  - Validar email único
  - Hash password con bcrypt
  - Rate limit: 3/minuto
- [ ] `POST /api/v1/auth/login`: Login
  - Verificar credenciales
  - Incrementar contador de intentos fallidos
  - Bloquear cuenta después de N intentos
  - Rate limit: 5/minuto por IP
  - Retornar access_token y refresh_token
- [ ] `POST /api/v1/auth/refresh`: Renovar access token
  - Validar refresh_token
  - Generar nuevo access_token
  - Rate limit: 10/minuto
- [ ] `POST /api/v1/auth/logout`: Logout
  - Invalidar refresh_token
  - Rate limit: 20/minuto
- [ ] `GET /api/v1/auth/me`: Obtener usuario actual
  - Requiere autenticación
  - Rate limit: 30/minuto

##### Fase 6: Middleware y Dependencias
- [ ] `get_current_user`: Dependency de FastAPI para obtener usuario autenticado
- [ ] `get_current_active_user`: Verificar que usuario esté activo
- [ ] `get_current_superuser`: Verificar que usuario sea superusuario
- [ ] Middleware de logging de intentos de login fallidos

##### Fase 7: Seguridad Adicional
- [ ] Implementar comparación timing-safe de tokens (`secrets.compare_digest`)
- [ ] Agregar headers de seguridad (CORS ya configurado ✅)
- [ ] Implementar logging de eventos de seguridad
- [ ] Configurar alertas para múltiples intentos fallidos
- [ ] Implementar CAPTCHA después de N intentos fallidos (opcional)

#### 4.3 Mejores Prácticas de Seguridad

##### Contraseñas
```python
# ✅ CORRECTO: Usar bcrypt con rounds adecuados
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
```

##### Tokens JWT
```python
# ✅ CORRECTO: Incluir expiración y validar
from datetime import datetime, timedelta
import jwt

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=30))
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def verify_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
```

##### Rate Limiting
```python
# ✅ CORRECTO: Limitar intentos de login
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, ...):
    # Máximo 5 intentos por minuto por IP
    ...
```

##### Validación de Entrada
```python
# ✅ CORRECTO: Validar con Pydantic
from pydantic import BaseModel, EmailStr, validator

class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password debe tener al menos 8 caracteres')
        return v
```

---

### 5. Checklist de Seguridad Completo

#### 5.1 Autenticación
- [ ] ✅ Usar bcrypt para hashing de contraseñas (no MD5, SHA1, SHA256)
- [ ] ✅ Validar complejidad de contraseñas (min 8 chars, mayúsculas, números)
- [ ] ✅ Implementar rate limiting en endpoints de login
- [ ] ✅ Bloquear cuentas después de N intentos fallidos
- [ ] ✅ Usar comparación timing-safe para tokens (`secrets.compare_digest`)
- [ ] ✅ Validar expiración de tokens JWT
- [ ] ✅ Implementar refresh tokens para renovación segura
- [ ] ✅ Invalidar refresh tokens en logout
- [ ] ✅ No exponer información sensible en mensajes de error

#### 5.2 Autorización
- [ ] ✅ Implementar roles y permisos (is_superuser, roles)
- [ ] ✅ Verificar permisos en cada endpoint protegido
- [ ] ✅ Validar que usuario esté activo antes de permitir acceso
- [ ] ✅ Implementar middleware de autenticación reutilizable

#### 5.3 Configuración
- [ ] ✅ Validar `SECRET_KEY` con longitud mínima de 32 caracteres
- [ ] ✅ Usar variables de entorno para secretos (nunca hardcodear)
- [ ] ✅ Configurar CORS apropiadamente (ya configurado ✅)
- [ ] ✅ Configurar rate limiting global
- [ ] ✅ Configurar logging de eventos de seguridad

#### 5.4 Base de Datos
- [ ] ✅ Usar prepared statements (SQLAlchemy lo hace automáticamente ✅)
- [ ] ✅ Validar entrada antes de guardar en BD
- [ ] ✅ Implementar índices en campos de búsqueda (email, username)
- [ ] ✅ No almacenar contraseñas en texto plano (solo hash)

#### 5.5 Logging y Monitoreo
- [ ] ✅ Loggear intentos de login fallidos
- [ ] ✅ Loggear cambios de contraseña
- [ ] ✅ Loggear creación/eliminación de usuarios
- [ ] ✅ No loggear contraseñas ni tokens completos
- [ ] ✅ Configurar alertas para actividad sospechosa

#### 5.6 Headers de Seguridad
- [ ] ✅ Configurar CORS apropiadamente (ya configurado ✅)
- [ ] ✅ Agregar headers de seguridad (X-Content-Type-Options, X-Frame-Options)
- [ ] ✅ Implementar HTTPS en producción (obligatorio)
- [ ] ✅ Configurar SameSite para cookies (si se usan)

---

### 6. Código de Referencia Seguro

#### 6.1 Estructura de Archivos Recomendada

**`backend/app/core/security.py`**:
```python
"""
Utilidades de seguridad para autenticación JWT
"""
from datetime import datetime, timedelta
from typing import Optional
import jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")

def hash_password(password: str) -> str:
    """Hash password con bcrypt"""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verificar password contra hash"""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Crear JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def verify_token(token: str) -> Optional[dict]:
    """Verificar y decodificar JWT token"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Dependency para obtener usuario actual desde token"""
    payload = verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Aquí deberías obtener el usuario de la BD usando payload.get("sub")
    # user = await get_user_by_id(payload.get("sub"))
    # if not user:
    #     raise HTTPException(status_code=404, detail="Usuario no encontrado")
    # return user
    return payload
```

**`backend/app/schemas/auth.py`**:
```python
"""
Schemas para autenticación
"""
from pydantic import BaseModel, EmailStr, validator
from datetime import datetime
from typing import Optional

class LoginRequest(BaseModel):
    """Request de login"""
    email: EmailStr
    password: str

class RegisterRequest(BaseModel):
    """Request de registro"""
    email: EmailStr
    username: str
    password: str
    password_confirm: str
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Password debe tener al menos 8 caracteres')
        if not any(c.isupper() for c in v):
            raise ValueError('Password debe contener al menos una mayúscula')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password debe contener al menos un número')
        return v
    
    @validator('password_confirm')
    def passwords_match(cls, v, values):
        if 'password' in values and v != values['password']:
            raise ValueError('Passwords no coinciden')
        return v

class TokenResponse(BaseModel):
    """Response con tokens"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class UserResponse(BaseModel):
    """Response de usuario"""
    id: int
    email: str
    username: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True
```

---

### 7. Próximos Pasos

1. **Implementar sistema de autenticación completo** siguiendo el checklist de la sección 4.2
2. **Corregir vulnerabilidades identificadas**:
   - HIGH-001: Usar `secrets.compare_digest()` en comparación de tokens
   - CRIT-002: Validar `SECRET_KEY` con longitud mínima
3. **Configurar rate limiting** con `slowapi`
4. **Implementar logging de seguridad** para eventos críticos
5. **Realizar pruebas de penetración** después de implementar login
6. **Configurar monitoreo** de intentos de login fallidos

---

## 📊 Resumen de Vulnerabilidades

| ID | Severidad | Descripción | Estado |
|----|-----------|-------------|--------|
| CRIT-001 | 🔴 Crítica | Ausencia de sistema de autenticación | Pendiente |
| CRIT-002 | 🔴 Crítica | SECRET_KEY sin validación | Pendiente |
| HIGH-001 | 🟠 Alta | Comparación de tokens no segura | Pendiente |
| HIGH-002 | 🟠 Alta | Falta rate limiting | Pendiente |
| MED-001 | 🟡 Media | Logging de información sensible | Pendiente |
| MED-002 | 🟡 Media | Manejo de errores expone información | Pendiente |
| LOW-001 | 🟢 Baja | Falta validación de expiración | N/A (no implementado) |
| LOW-002 | 🟢 Baja | Falta rotación de SECRET_KEY | Pendiente |

---

## ✅ Conclusión

El sistema actual **NO tiene implementado un sistema de login de usuarios**. Aunque existe la configuración base y las dependencias necesarias, falta toda la implementación.

**Prioridades**:
1. 🔴 **CRÍTICO**: Implementar sistema de autenticación completo
2. 🟠 **ALTO**: Corregir vulnerabilidades de seguridad identificadas
3. 🟡 **MEDIO**: Implementar rate limiting y logging de seguridad
4. 🟢 **BAJO**: Mejoras adicionales de seguridad

**Tiempo estimado de implementación**: 2-3 días de desarrollo para un sistema completo y seguro.

---

*Auditoría generada automáticamente el 2026-02-01*
