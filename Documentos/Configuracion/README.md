# ⚙️ DOCUMENTACIÓN DE CONFIGURACIÓN

## **📋 RESUMEN**

Este documento describe todas las configuraciones del sistema de préstamos y cobranza, incluyendo variables de entorno, configuraciones de base de datos, servicios externos y parámetros del sistema.

---

## **🔧 VARIABLES DE ENTORNO**

### **Variables Principales:**

#### **Base de Datos:**
```bash
# PostgreSQL
DATABASE_URL=postgresql://user:password@host:port/database
DB_ECHO=false
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600
```

#### **Autenticación:**
```bash
# JWT
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
ALGORITHM=HS256
```

#### **Administrador:**
```bash
# Usuario Admin
ADMIN_EMAIL=itmaster@rapicreditca.com
ADMIN_PASSWORD=R@pi_2025**
```

#### **Aplicación:**
```bash
# Configuración General
APP_NAME=Sistema de Préstamos y Cobranza
APP_VERSION=1.0.0
ENVIRONMENT=production
DEBUG=false
API_V1_PREFIX=/api/v1
```

#### **CORS:**
```bash
# Configuración CORS
CORS_ORIGINS=["https://yourdomain.com", "https://www.yourdomain.com"]
CORS_ORIGINS_DEV=["http://localhost:3000", "http://localhost:5173"]
```

---

## **🗄️ CONFIGURACIÓN DE BASE DE DATOS**

### **PostgreSQL - Configuración de Producción:**

#### **Parámetros Recomendados:**
```sql
-- Configuración de conexiones
max_connections = 100
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB

-- Configuración de logging
log_statement = 'mod'
log_min_duration_statement = 1000
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
```

#### **Índices Optimizados:**
```sql
-- Índices principales
CREATE INDEX CONCURRENTLY idx_clientes_cedula ON clientes(cedula);
CREATE INDEX CONCURRENTLY idx_clientes_email ON clientes(email);
CREATE INDEX CONCURRENTLY idx_clientes_telefono ON clientes(telefono);
CREATE INDEX CONCURRENTLY idx_clientes_estado ON clientes(estado);
CREATE INDEX CONCURRENTLY idx_clientes_activo ON clientes(activo);

-- Índices compuestos
CREATE INDEX CONCURRENTLY idx_clientes_estado_activo ON clientes(estado, activo);
CREATE INDEX CONCURRENTLY idx_pagos_cedula_fecha ON pagos(cedula_cliente, fecha_pago);
```

---

## **🌐 CONFIGURACIÓN DE SERVICIOS EXTERNOS**

### **Email Service (SMTP):**
```bash
# Configuración SMTP
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_TLS=true
SMTP_SSL=false
```

### **WhatsApp Service:**
```bash
# Configuración WhatsApp
WHATSAPP_API_URL=https://api.whatsapp.com
WHATSAPP_TOKEN=your-whatsapp-token
WHATSAPP_PHONE_NUMBER=+58412123456
```

### **Monitoreo (Sentry):**
```bash
# Configuración Sentry
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1
```

---

## **📊 CONFIGURACIÓN DE MONITOREO**

### **Prometheus Metrics:**
```python
# Configuración de métricas
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090
PROMETHEUS_PATH=/metrics

# Métricas personalizadas
METRICS_ENABLED=true
METRICS_INTERVAL=60  # segundos
```

### **Health Checks:**
```python
# Configuración de health checks
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_INTERVAL=30  # segundos
HEALTH_CHECK_TIMEOUT=5  # segundos
HEALTH_CHECK_CACHE_DURATION=30  # segundos
```

---

## **🔐 CONFIGURACIÓN DE SEGURIDAD**

### **Rate Limiting:**
```python
# Configuración de rate limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=60
RATE_LIMIT_BURST=10
```

### **CORS Security:**
```python
# Configuración CORS segura
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
CORS_ALLOW_HEADERS=["*"]
CORS_EXPOSE_HEADERS=["*"]
```

### **Headers de Seguridad:**
```python
# Headers de seguridad
SECURITY_HEADERS={
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": "default-src 'self'"
}
```

---

## **📁 CONFIGURACIÓN DE ARCHIVOS**

### **Upload Configuration:**
```python
# Configuración de uploads
UPLOAD_DIR=uploads/
MAX_UPLOAD_SIZE=10485760  # 10MB
ALLOWED_EXTENSIONS={'.xlsx', '.xls', '.csv', '.pdf', '.png', '.jpg', '.jpeg'}
```

### **Logging Configuration:**
```python
# Configuración de logging
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=logs/app.log
LOG_MAX_SIZE=10485760  # 10MB
LOG_BACKUP_COUNT=5
```

---

## **🚀 CONFIGURACIÓN DE DESPLIEGUE**

### **Render.com:**
```yaml
# render.yaml
services:
  - type: web
    name: pagos-backend
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: DATABASE_URL
        sync: false
      - key: SECRET_KEY
        generateValue: true
```

### **Railway:**
```json
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port $PORT",
    "healthcheckPath": "/api/v1/health/render"
  }
}
```

---

## **🔧 CONFIGURACIÓN DE DESARROLLO**

### **Backend - requirements.txt:**
```txt
# Core dependencies
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
alembic==1.12.1
psycopg2-binary==2.9.9

# Authentication
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6

# Validation
pydantic==2.5.0
pydantic-settings==2.1.0
email-validator==2.1.0

# Monitoring
sentry-sdk[fastapi]==1.38.0
prometheus-fastapi-instrumentator==6.1.0
psutil==5.9.6

# Development
pytest==7.4.3
pytest-cov==4.1.0
pytest-asyncio==0.21.1
httpx==0.25.2
```

### **Frontend - package.json:**
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.8.0",
    "@tanstack/react-query": "^5.8.4",
    "axios": "^1.6.2",
    "framer-motion": "^10.16.5",
    "tailwindcss": "^3.3.6",
    "date-fns": "^2.30.0"
  },
  "devDependencies": {
    "vitest": "^1.0.0",
    "@testing-library/react": "^13.4.0",
    "@testing-library/jest-dom": "^6.1.5",
    "@testing-library/user-event": "^14.5.1",
    "@vitejs/plugin-react": "^4.1.1",
    "typescript": "^5.2.2"
  }
}
```

---

## **📊 CONFIGURACIÓN DE VALIDACIÓN**

### **Validadores:**
```python
# Configuración de validadores
VALIDATOR_CONFIG={
    "cedula": {
        "min_length": 8,
        "max_length": 20,
        "patterns": ["V", "E", "J"]
    },
    "telefono": {
        "pattern": r"^\+58[1-9]\d{9}$",
        "country": "VENEZUELA"
    },
    "email": {
        "max_length": 255,
        "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    },
    "monto": {
        "min_value": 0.01,
        "max_value": 999999999.99,
        "decimal_places": 2
    }
}
```

---

## **🎯 CONFIGURACIÓN DE BUSINESS RULES**

### **Reglas de Negocio:**
```python
# Configuración de reglas de negocio
BUSINESS_RULES={
    "prestamos": {
        "monto_minimo": 1000000,  # 1M VES
        "monto_maximo": 50000000,  # 50M VES
        "plazo_minimo": 1,  # 1 mes
        "plazo_maximo": 60,  # 60 meses
        "tasa_interes_minima": 0.01,  # 1%
        "tasa_interes_maxima": 0.50,  # 50%
        "cuota_maxima_porcentaje_ingreso": 0.40  # 40%
    },
    "clientes": {
        "edad_minima": 18,
        "edad_maxima": 100,
        "cedulas_duplicadas_permitidas": True,
        "validacion_tiempo_real": True
    }
}
```

---

## **🔍 CONFIGURACIÓN DE DEBUGGING**

### **Desarrollo:**
```python
# Configuración de debugging
DEBUG_CONFIG={
    "enabled": True,
    "log_level": "DEBUG",
    "sql_echo": True,
    "cors_origins": ["http://localhost:3000", "http://localhost:5173"],
    "reload": True
}
```

### **Producción:**
```python
# Configuración de producción
PRODUCTION_CONFIG={
    "enabled": False,
    "log_level": "INFO",
    "sql_echo": False,
    "cors_origins": ["https://yourdomain.com"],
    "reload": False
}
```

---

## **📚 RECURSOS ADICIONALES**

### **Documentación de Configuración:**
- [FastAPI Configuration](https://fastapi.tiangolo.com/advanced/settings/)
- [SQLAlchemy Configuration](https://docs.sqlalchemy.org/en/20/core/engines.html)
- [Pydantic Settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)

### **Mejores Prácticas:**
- ✅ **Variables de entorno** para configuración sensible
- ✅ **Validación** de configuración al inicio
- ✅ **Documentación** de todas las variables
- ✅ **Separación** entre desarrollo y producción

---

## **✅ CONCLUSIÓN**

La configuración del sistema está completamente documentada y optimizada para:

- ✅ **Desarrollo**: Configuración flexible y debugging
- ✅ **Producción**: Configuración segura y optimizada
- ✅ **Monitoreo**: Métricas y health checks
- ✅ **Seguridad**: Headers y rate limiting

**🎉 El sistema está configurado profesionalmente para todos los entornos.**
