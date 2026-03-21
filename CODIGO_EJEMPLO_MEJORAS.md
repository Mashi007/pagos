# 🛠️ OPORTUNIDADES DE MEJORA - CÓDIGO DE EJEMPLO

## 1. CSRF Token Validation

### Backend (FastAPI)

```python
# app/core/security.py
import secrets
from fastapi import HTTPException, status

class CSRFTokenManager:
    def __init__(self):
        self.tokens = {}
    
    def generate_token(self, session_id: str) -> str:
        """Genera un token CSRF único por sesión"""
        token = secrets.token_urlsafe(32)
        self.tokens[session_id] = token
        return token
    
    def verify_token(self, session_id: str, token: str) -> bool:
        """Verifica que el token sea válido para la sesión"""
        stored_token = self.tokens.get(session_id)
        if not stored_token or stored_token != token:
            return False
        # Invalidar token después de usar (una sola vez)
        del self.tokens[session_id]
        return True

csrf_manager = CSRFTokenManager()

# app/routes/auth.py
from fastapi import APIRouter, Depends, HTTPException, Request
from app.core.security import csrf_manager

router = APIRouter()

@router.get("/login")
async def get_login_form():
    """Retorna el formulario de login con token CSRF"""
    session_id = "user_session_123"  # Obtener de sesión real
    csrf_token = csrf_manager.generate_token(session_id)
    return {
        "csrf_token": csrf_token,
        "form_url": "/auth/login-submit"
    }

@router.post("/login-submit")
async def login_submit(request: Request, email: str, password: str, csrf_token: str):
    """Procesa login - valida CSRF token"""
    session_id = request.session.get("id")
    
    # Verificar CSRF token ANTES de procesar
    if not csrf_manager.verify_token(session_id, csrf_token):
        raise HTTPException(
            status_code=403,
            detail="CSRF token inválido o expirado"
        )
    
    # Procesar login...
    return {"status": "success"}
```

### Frontend (HTML/JavaScript)

```html
<!-- Formulario de login con CSRF token -->
<form id="login-form" action="/auth/login-submit" method="POST">
    <!-- Campo oculto con CSRF token -->
    <input type="hidden" id="csrf_token" name="csrf_token" value="">
    
    <div class="form-group">
        <label for="email">Correo electrónico</label>
        <input type="email" id="email" name="email" required>
    </div>
    
    <div class="form-group">
        <label for="password">Contraseña</label>
        <input type="password" id="password" name="password" required>
    </div>
    
    <div class="form-group">
        <label for="remember">
            <input type="checkbox" id="remember" name="remember">
            Recordarme
        </label>
    </div>
    
    <button type="submit">Iniciar Sesión</button>
</form>

<script>
// Cargar CSRF token al cargar la página
document.addEventListener('DOMContentLoaded', async () => {
    const response = await fetch('/login');
    const data = await response.json();
    document.getElementById('csrf_token').value = data.csrf_token;
});

// Enviar con fetch para mayor control
document.getElementById('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const formData = new FormData(e.target);
    const csrfToken = formData.get('csrf_token');
    
    const response = await fetch('/auth/login-submit', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRF-Token': csrfToken
        },
        body: JSON.stringify({
            email: formData.get('email'),
            password: formData.get('password'),
            remember: formData.get('remember') === 'on',
            csrf_token: csrfToken
        })
    });
    
    if (response.ok) {
        window.location.href = '/dashboard';
    } else {
        alert('Error al iniciar sesión');
    }
});
</script>
```

---

## 2. Secure Cookies

### Backend (FastAPI)

```python
# app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Configuración de cookies seguras
    COOKIE_NAME: str = "rapicredit_session"
    COOKIE_MAX_AGE: int = 3600  # 1 hora
    COOKIE_SECURE: bool = True  # Solo HTTPS en producción
    COOKIE_HTTPONLY: bool = True
    COOKIE_SAMESITE: str = "strict"

settings = Settings()

# app/routes/auth.py
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from app.core.config import settings
from datetime import timedelta

router = APIRouter()

@router.post("/login")
async def login(email: str, password: str):
    """Login con cookie segura"""
    # Validar credenciales...
    user_id = "123"
    
    # Crear response
    response = JSONResponse({
        "status": "success",
        "message": "Sesión iniciada"
    })
    
    # Configurar cookie segura
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=f"{user_id}:session_token",
        max_age=settings.COOKIE_MAX_AGE,
        expires=timedelta(seconds=settings.COOKIE_MAX_AGE),
        path="/",
        domain=None,  # Usar None para dominio actual
        secure=settings.COOKIE_SECURE,  # HTTPS only
        httponly=settings.COOKIE_HTTPONLY,  # No accesible desde JS
        samesite=settings.COOKIE_SAMESITE  # strict | lax | none
    )
    
    return response

@router.post("/logout")
async def logout():
    """Logout - borrar cookie"""
    response = JSONResponse({"status": "success"})
    
    # Borrar cookie
    response.delete_cookie(
        key=settings.COOKIE_NAME,
        path="/",
        secure=settings.COOKIE_SECURE,
        httponly=settings.COOKIE_HTTPONLY,
        samesite=settings.COOKIE_SAMESITE
    )
    
    return response
```

### Validación en Request

```python
# app/core/database.py - Middleware para validar cookie
from fastapi import Request, HTTPException, status

async def validate_session(request: Request):
    """Validar que la cookie de sesión sea válida"""
    cookie_value = request.cookies.get("rapicredit_session")
    
    if not cookie_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autorizado"
        )
    
    user_id, session_token = cookie_value.split(":")
    
    # Verificar en BD que la sesión sea válida
    # ...
    
    return user_id
```

---

## 3. Content Security Policy (CSP) Mejorada

### Backend (FastAPI)

```python
# app/middleware/security.py
from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

class CSPMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # CSP header mejorado
        csp_policy = " ".join([
            "default-src 'self'",
            "script-src 'self' 'nonce-{nonce}'",
            "style-src 'self' 'nonce-{nonce}'",
            "img-src 'self' https: data:",
            "font-src 'self'",
            "connect-src 'self' https://pagos-f2qf.onrender.com",
            "frame-src 'none'",
            "object-src 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "frame-ancestors 'none'",
            "upgrade-insecure-requests"
        ])
        
        response.headers["Content-Security-Policy"] = csp_policy
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        
        return response

# app/main.py
from fastapi import FastAPI
from app.middleware.security import CSPMiddleware

app = FastAPI()
app.add_middleware(CSPMiddleware)
```

---

## 4. Form Feedback Visual (Frontend)

### HTML + CSS + JavaScript

```html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Login - RapiCredit</title>
    <style>
        * {
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .login-container {
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
            width: 100%;
            max-width: 420px;
        }
        
        .form-group {
            margin-bottom: 24px;
        }
        
        label {
            display: block;
            font-weight: 500;
            margin-bottom: 8px;
            color: #333;
            font-size: 14px;
        }
        
        input[type="email"],
        input[type="password"],
        input[type="text"] {
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
            transition: all 0.3s ease;
            background-color: #fff;
        }
        
        input[type="email"]:focus,
        input[type="password"]:focus,
        input[type="text"]:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
            background-color: #f8f9ff;
        }
        
        /* Estados de validación */
        input.valid {
            border-color: #10b981;
            background-color: #f0fdf4;
        }
        
        input.valid:focus {
            border-color: #10b981;
            box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.1);
        }
        
        input.invalid {
            border-color: #ef4444;
            background-color: #fef2f2;
        }
        
        input.invalid:focus {
            border-color: #ef4444;
            box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.1);
        }
        
        input:disabled {
            background-color: #f3f4f6;
            cursor: not-allowed;
        }
        
        /* Indicadores de validación */
        .form-group {
            position: relative;
        }
        
        .validation-icon {
            position: absolute;
            right: 16px;
            top: 38px;
            font-size: 18px;
            pointer-events: none;
        }
        
        .validation-icon.valid {
            color: #10b981;
        }
        
        .validation-icon.invalid {
            color: #ef4444;
        }
        
        /* Mensajes de error/éxito */
        .form-message {
            font-size: 13px;
            margin-top: 6px;
            display: flex;
            align-items: center;
            gap: 6px;
            min-height: 20px;
        }
        
        .form-message.error {
            color: #ef4444;
        }
        
        .form-message.success {
            color: #10b981;
        }
        
        .form-message.info {
            color: #667eea;
        }
        
        /* Password strength indicator */
        .password-strength {
            margin-top: 8px;
            height: 4px;
            background: #e0e0e0;
            border-radius: 2px;
            overflow: hidden;
        }
        
        .password-strength-bar {
            height: 100%;
            width: 0;
            transition: width 0.3s ease, background-color 0.3s ease;
            border-radius: 2px;
        }
        
        .password-strength-bar.weak {
            width: 33%;
            background: #ef4444;
        }
        
        .password-strength-bar.medium {
            width: 66%;
            background: #f59e0b;
        }
        
        .password-strength-bar.strong {
            width: 100%;
            background: #10b981;
        }
        
        /* Checkbox accesible */
        .checkbox-group {
            display: flex;
            align-items: center;
            gap: 12px;
        }
        
        .checkbox-group input[type="checkbox"] {
            width: 20px;
            height: 20px;
            cursor: pointer;
            margin: 0;
            accent-color: #667eea;
        }
        
        .checkbox-group label {
            margin: 0;
            cursor: pointer;
            font-weight: 400;
            font-size: 14px;
        }
        
        /* Botón */
        button {
            width: 100%;
            padding: 12px 16px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            background: #667eea;
            color: white;
        }
        
        button:hover {
            background: #5568d3;
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(102, 126, 234, 0.3);
        }
        
        button:active {
            transform: translateY(0);
        }
        
        button:disabled {
            background: #cbd5e1;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }
        
        button .spinner {
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 2px solid rgba(255,255,255,0.3);
            border-top-color: white;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
            margin-right: 8px;
            vertical-align: middle;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .button-text {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <h1>Iniciar Sesión</h1>
        <p>Accede a tu cuenta de RapiCredit</p>
        
        <form id="login-form">
            <!-- Email -->
            <div class="form-group">
                <label for="email">Correo Electrónico</label>
                <div style="position: relative;">
                    <input
                        type="email"
                        id="email"
                        name="email"
                        placeholder="tu@email.com"
                        required
                        aria-label="Correo electrónico"
                        aria-describedby="email-message"
                    >
                    <span class="validation-icon"></span>
                </div>
                <div class="form-message" id="email-message"></div>
            </div>
            
            <!-- Password -->
            <div class="form-group">
                <label for="password">Contraseña</label>
                <div style="position: relative;">
                    <input
                        type="password"
                        id="password"
                        name="password"
                        placeholder="Ingresa tu contraseña"
                        required
                        minlength="8"
                        aria-label="Contraseña"
                        aria-describedby="password-message"
                    >
                    <span class="validation-icon"></span>
                </div>
                <div class="password-strength">
                    <div class="password-strength-bar"></div>
                </div>
                <div class="form-message" id="password-message"></div>
            </div>
            
            <!-- Remember me -->
            <div class="form-group">
                <div class="checkbox-group">
                    <input
                        type="checkbox"
                        id="remember"
                        name="remember"
                        aria-label="Recordarme en este dispositivo"
                    >
                    <label for="remember">Recordarme</label>
                </div>
            </div>
            
            <!-- Submit -->
            <button type="submit" id="submit-btn">
                <span class="button-text">
                    <span>Iniciar Sesión</span>
                </span>
            </button>
        </form>
        
        <div style="margin-top: 16px; text-align: center;">
            <a href="/forgot-password" style="color: #667eea; text-decoration: none;">
                ¿Olvidó su contraseña?
            </a>
        </div>
    </div>
    
    <script>
        const form = document.getElementById('login-form');
        const emailInput = document.getElementById('email');
        const passwordInput = document.getElementById('password');
        const submitBtn = document.getElementById('submit-btn');
        const emailMessage = document.getElementById('email-message');
        const passwordMessage = document.getElementById('password-message');
        
        // Validar email
        function validateEmail(email) {
            const regex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            return regex.test(email);
        }
        
        // Validar contraseña
        function validatePassword(password) {
            return password.length >= 8;
        }
        
        // Calcular fortaleza de contraseña
        function getPasswordStrength(password) {
            if (password.length < 8) return 'weak';
            if (password.length < 12) return 'medium';
            if (/[A-Z]/.test(password) && /[0-9]/.test(password) && /[!@#$%^&*]/.test(password)) {
                return 'strong';
            }
            return 'medium';
        }
        
        // Email validation
        emailInput.addEventListener('blur', () => {
            validateField(emailInput, emailMessage, validateEmail(emailInput.value));
        });
        
        emailInput.addEventListener('input', () => {
            if (emailInput.value) {
                const isValid = validateEmail(emailInput.value);
                emailInput.classList.toggle('valid', isValid);
                emailInput.classList.toggle('invalid', !isValid);
                updateIcon(emailInput, isValid);
                
                if (!isValid && emailInput.value) {
                    emailMessage.textContent = 'Email no válido';
                    emailMessage.className = 'form-message error';
                } else if (isValid) {
                    emailMessage.textContent = '✓ Email válido';
                    emailMessage.className = 'form-message success';
                } else {
                    emailMessage.textContent = '';
                }
            }
        });
        
        // Password validation
        passwordInput.addEventListener('input', () => {
            if (passwordInput.value) {
                const isValid = validatePassword(passwordInput.value);
                const strength = getPasswordStrength(passwordInput.value);
                
                passwordInput.classList.toggle('valid', isValid);
                passwordInput.classList.toggle('invalid', !isValid);
                updateIcon(passwordInput, isValid);
                
                // Update strength bar
                const strengthBar = passwordInput.parentElement.nextElementSibling.querySelector('.password-strength-bar');
                strengthBar.className = `password-strength-bar ${strength}`;
                
                if (!isValid) {
                    passwordMessage.textContent = 'Mínimo 8 caracteres';
                    passwordMessage.className = 'form-message error';
                } else if (strength === 'weak') {
                    passwordMessage.textContent = 'Contraseña débil';
                    passwordMessage.className = 'form-message info';
                } else if (strength === 'medium') {
                    passwordMessage.textContent = 'Contraseña moderada';
                    passwordMessage.className = 'form-message info';
                } else {
                    passwordMessage.textContent = '✓ Contraseña fuerte';
                    passwordMessage.className = 'form-message success';
                }
            }
        });
        
        function updateIcon(input, isValid) {
            const icon = input.parentElement.querySelector('.validation-icon');
            if (input.value) {
                icon.textContent = isValid ? '✓' : '✕';
                icon.className = `validation-icon ${isValid ? 'valid' : 'invalid'}`;
            } else {
                icon.textContent = '';
            }
        }
        
        // Form submit
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const emailValid = validateEmail(emailInput.value);
            const passwordValid = validatePassword(passwordInput.value);
            
            if (!emailValid || !passwordValid) {
                alert('Por favor completa todos los campos correctamente');
                return;
            }
            
            // Mostrar loading
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="button-text"><span class="spinner"></span><span>Iniciando sesión...</span></span>';
            
            try {
                const response = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        email: emailInput.value,
                        password: passwordInput.value,
                        remember: document.getElementById('remember').checked
                    })
                });
                
                if (response.ok) {
                    // Éxito
                    const toast = document.createElement('div');
                    toast.textContent = '✓ Sesión iniciada correctamente';
                    toast.style.cssText = `
                        position: fixed;
                        bottom: 20px;
                        right: 20px;
                        background: #10b981;
                        color: white;
                        padding: 16px 24px;
                        border-radius: 8px;
                        box-shadow: 0 10px 20px rgba(0,0,0,0.2);
                        animation: slideIn 0.3s ease;
                    `;
                    document.body.appendChild(toast);
                    
                    // Redirigir
                    setTimeout(() => {
                        window.location.href = '/dashboard';
                    }, 1000);
                } else {
                    const error = await response.json();
                    const toast = document.createElement('div');
                    toast.textContent = `✕ ${error.detail || 'Error al iniciar sesión'}`;
                    toast.style.cssText = `
                        position: fixed;
                        bottom: 20px;
                        right: 20px;
                        background: #ef4444;
                        color: white;
                        padding: 16px 24px;
                        border-radius: 8px;
                        box-shadow: 0 10px 20px rgba(0,0,0,0.2);
                        animation: slideIn 0.3s ease;
                    `;
                    document.body.appendChild(toast);
                    
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = '<span class="button-text"><span>Iniciar Sesión</span></span>';
                }
            } catch (err) {
                console.error('Error:', err);
                alert('Error de conexión');
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<span class="button-text"><span>Iniciar Sesión</span></span>';
            }
        });
        
        // Animation for toast
        const style = document.createElement('style');
        style.textContent = `
            @keyframes slideIn {
                from {
                    transform: translateX(400px);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }
        `;
        document.head.appendChild(style);
    </script>
</body>
</html>
```

---

## 5. Accesibilidad - Labels y ARIA

### Antes (Incorrecto)

```html
<input type="checkbox" id="remember">

<form>
    <input type="email" placeholder="Email">
    <input type="password" placeholder="Contraseña">
    <button>Enviar</button>
</form>
```

### Después (Correcto)

```html
<!-- Label correctamente asociado -->
<label for="remember">Recordarme</label>
<input type="checkbox" id="remember" name="remember">

<!-- Formulario accesible -->
<form aria-label="Formulario de login">
    <div>
        <label for="email">Correo electrónico</label>
        <input 
            type="email" 
            id="email" 
            name="email"
            aria-label="Correo electrónico"
            aria-describedby="email-help"
            required
        >
        <small id="email-help">Usaremos este email para tu cuenta</small>
    </div>
    
    <div>
        <label for="password">Contraseña</label>
        <input 
            type="password" 
            id="password" 
            name="password"
            aria-label="Contraseña"
            aria-describedby="password-help"
            minlength="8"
            required
        >
        <small id="password-help">Mínimo 8 caracteres</small>
    </div>
    
    <button 
        type="submit"
        aria-label="Iniciar sesión en RapiCredit"
    >
        Iniciar Sesión
    </button>
</form>
```

---

## 6. Sentry Error Tracking

### Setup

```html
<!-- Agregar al <head> -->
<script 
    src="https://browser.sentry-cdn.com/7.x/bundle.min.js"
    integrity="sha384-...">
</script>

<script>
Sentry.init({
    dsn: "https://your-key@sentry.io/project-id",
    environment: "production",
    tracesSampleRate: 0.1,
    integrations: [
        new Sentry.Replay({
            maskAllText: true,
            blockAllMedia: true,
        }),
    ],
    replaysSessionSampleRate: 0.1,
    replaysOnErrorSampleRate: 1.0,
});
</script>
```

### Uso

```javascript
// Capturar eventos
Sentry.captureException(new Error("Something went wrong"));
Sentry.captureMessage("User logged in", "info");

// Contexto
Sentry.setUser({ id: "user123", email: "user@example.com" });
Sentry.setTag("login_page", "v2");
```

---

## 7. Google Analytics 4

```html
<!-- Agregar al <head> -->
<script async src="https://www.googletagmanager.com/gtag/js?id=GA_MEASUREMENT_ID"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'GA_MEASUREMENT_ID');
  
  // Track login
  document.getElementById('login-form').addEventListener('submit', () => {
      gtag('event', 'login', {
          method: 'email'
      });
  });
</script>
```

---

## 8. FastAPI Swagger Documentation

```python
# app/main.py
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

app = FastAPI(
    title="RapiCredit API",
    description="Sistema de Préstamos y Cobranza - API REST",
    version="1.0.0",
    contact={
        "name": "RapiCredit Support",
        "url": "https://rapicredit.onrender.com/support",
        "email": "support@rapicredit.com",
    },
    license_info={
        "name": "MIT",
    },
)

@app.get("/api/auth/login", tags=["Authentication"])
async def login(email: str, password: str):
    """
    Inicia sesión con credenciales.
    
    - **email**: Email del usuario
    - **password**: Contraseña del usuario
    
    Retorna:
    - Cookie de sesión segura
    - Token JWT (opcional)
    """
    pass

# Documentación disponible en:
# - http://localhost:8000/docs (Swagger UI)
# - http://localhost:8000/redoc (ReDoc)
```

---

**Fin del documento de código de ejemplo**
