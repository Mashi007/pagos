# 🚀 Configuración en Render.com - ¿Qué se Genera Automáticamente?

## ✅ Lo que Render GENERA Automáticamente

### 1. **URL del Servicio** ✅ AUTOMÁTICO
Render genera automáticamente una URL para tu servicio:
- Ejemplo: `https://pagos-backend.onrender.com`
- Esta URL la usarás como **Callback URL** en Meta Developers

### 2. **Certificado SSL** ✅ AUTOMÁTICO
Render proporciona SSL/HTTPS automáticamente (requerido por Meta para webhooks)

### 3. **Variables de Entorno Básicas** ✅ ALGUNAS AUTOMÁTICAS
Render puede generar automáticamente algunas variables del sistema, pero **NO las de WhatsApp**

---

## ❌ Lo que DEBES Configurar MANUALMENTE

### 1. **Variables de Entorno de WhatsApp** ❌ MANUAL

**Render NO genera automáticamente** las variables de WhatsApp. Debes configurarlas manualmente:

1. Ve a tu servicio en Render Dashboard
2. Ve a **Environment** (Variables de Entorno)
3. Agrega manualmente cada variable:

```
WHATSAPP_VERIFY_TOKEN=rapicredit_2024_secure_token_xyz123
WHATSAPP_ACCESS_TOKEN=tu_access_token_de_meta
WHATSAPP_PHONE_NUMBER_ID=953020801227915
WHATSAPP_BUSINESS_ACCOUNT_ID=1668996594067091
DATABASE_URL=postgresql://...
SECRET_KEY=tu-clave-secreta
```

### 2. **Webhook en Meta Developers** ❌ MANUAL

Debes configurar manualmente el webhook en Meta Developers usando la URL que Render genera:

1. Copia la URL de tu servicio en Render (ej: `https://pagos-backend.onrender.com`)
2. Ve a Meta Developers > Tu App > WhatsApp > Configuration
3. Configura el webhook manualmente con:
   - **Callback URL**: `https://pagos-backend.onrender.com/api/v1/whatsapp/webhook`
   - **Verify Token**: El mismo que configuraste en Render

---

## 📋 Checklist de Configuración en Render

### Paso 1: Crear Servicio Backend en Render

1. Ve a [Render Dashboard](https://dashboard.render.com/)
2. Click en **New** > **Web Service**
3. Conecta tu repositorio de GitHub
4. Configura:
   - **Name**: `pagos-backend`
   - **Root Directory**: `backend`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app.main:app --bind 0.0.0.0:$PORT`

### Paso 2: Configurar Variables de Entorno en Render

En el dashboard de Render, ve a **Environment** y agrega:

```bash
# WhatsApp (OBLIGATORIAS)
WHATSAPP_VERIFY_TOKEN=rapicredit_2024_secure_token_xyz123
WHATSAPP_ACCESS_TOKEN=tu_access_token_de_meta_aqui
WHATSAPP_PHONE_NUMBER_ID=953020801227915
WHATSAPP_BUSINESS_ACCOUNT_ID=1668996594067091

# Base de Datos (si usas PostgreSQL en Render)
DATABASE_URL=postgresql://usuario:password@host:5432/dbname

# Seguridad
SECRET_KEY=tu-clave-secreta-super-segura-aqui

# General
DEBUG=False
PROJECT_NAME=Sistema de Pagos
VERSION=1.0.0
```

### Paso 3: Obtener URL del Servicio

Una vez desplegado, Render te dará una URL como:
```
https://pagos-backend.onrender.com
```

### Paso 4: Configurar Webhook en Meta

Usa la URL de Render para configurar el webhook:

1. Ve a Meta Developers
2. WhatsApp > Configuration > Webhook
3. **Callback URL**: `https://pagos-backend.onrender.com/api/v1/whatsapp/webhook`
4. **Verify Token**: El mismo `WHATSAPP_VERIFY_TOKEN` que configuraste en Render

---

## 🔄 Actualizar render.yaml (Opcional)

Puedes agregar la configuración del backend al `render.yaml`:

```yaml
services:
  # Frontend (ya existe)
  - type: web
    name: pagos-frontend
    env: node
    buildCommand: npm install && npm run build
    staticPublishPath: ./frontend/dist
    envVars:
      - key: NODE_VERSION
        value: 20.11.0

  # Backend (nuevo)
  - type: web
    name: pagos-backend
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app.main:app --bind 0.0.0.0:$PORT
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
      # NOTA: Las variables de WhatsApp DEBES agregarlas manualmente en Render Dashboard
      # porque contienen información sensible
```

**⚠️ IMPORTANTE**: Aunque agregues configuración en `render.yaml`, las variables de entorno sensibles (como tokens) **DEBES configurarlas manualmente** en el dashboard de Render por seguridad.

---

## ✅ Resumen: ¿Qué es Automático vs Manual?

| Item | Automático en Render | Manual |
|------|---------------------|--------|
| URL del servicio | ✅ Sí | ❌ |
| SSL/HTTPS | ✅ Sí | ❌ |
| Variables de entorno básicas | ⚠️ Algunas | ✅ La mayoría |
| Variables de WhatsApp | ❌ No | ✅ **SÍ - DEBES CONFIGURARLAS** |
| Webhook en Meta | ❌ No | ✅ **SÍ - DEBES CONFIGURARLO** |
| Access Token de Meta | ❌ No | ✅ **SÍ - DEBES OBTENERLO DE META** |

---

## 🎯 Respuesta Directa

**NO**, las variables de WhatsApp **NO se generan automáticamente** en Render. Debes:

1. ✅ Configurarlas **MANUALMENTE** en Render Dashboard > Environment
2. ✅ Obtener el Access Token **MANUALMENTE** de Meta Developers
3. ✅ Configurar el webhook **MANUALMENTE** en Meta Developers usando la URL de Render

Lo único que Render genera automáticamente es la **URL del servicio** y el **certificado SSL**.
