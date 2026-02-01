# 🔧 Configuración de Variables de Entorno - WhatsApp

## 📋 Variables Necesarias según tus Datos de Meta

Basado en la información de tu cuenta de Meta Developers, estas son las variables que debes configurar:

### ✅ Variables de WhatsApp (OBLIGATORIAS)

```bash
# Token de verificación del webhook (TÚ LO CREAS - debe ser seguro)
# Este token debe coincidir EXACTAMENTE con el que configures en Meta Developers
WHATSAPP_VERIFY_TOKEN=tu_token_secreto_super_seguro_aqui

# Access Token de WhatsApp Business API
# Lo obtienes en: Meta Developers > Tu App > WhatsApp > API Setup > "Token de acceso temporal"
# O genera uno permanente en: Configuración > Básica > Token de acceso
WHATSAPP_ACCESS_TOKEN=tu_access_token_de_meta_aqui

# Phone Number ID (de tu imagen: 953020801227915)
# Identificador del número de teléfono de WhatsApp Business
WHATSAPP_PHONE_NUMBER_ID=953020801227915

# WhatsApp Business Account ID (de tu imagen: 1668996594067091)
# Identificador de la cuenta de WhatsApp Business
WHATSAPP_BUSINESS_ACCOUNT_ID=1668996594067091
```

### 📱 Información de tu Cuenta (para referencia)

- **Application ID**: `25594371996899430`
- **Número de WhatsApp**: `+58 424 4359435`
- **Phone Number ID**: `953020801227915`
- **Business Account ID**: `1668996594067091`
- **Modo**: En desarrollo

---

## 🔍 Dónde Obtener Cada Variable

### 1. WHATSAPP_VERIFY_TOKEN
**TÚ LO CREAS** - Puede ser cualquier string seguro, por ejemplo:
```bash
WHATSAPP_VERIFY_TOKEN=rapicredit_2024_secure_token_xyz123
```

**Importante**: Este mismo token debes ingresarlo en Meta Developers cuando configures el webhook.

### 2. WHATSAPP_ACCESS_TOKEN
**Obtener en Meta Developers**:
1. Ve a [Meta Developers](https://developers.facebook.com/)
2. Selecciona tu aplicación (ID: 25594371996899430)
3. Ve a **WhatsApp** > **API Setup**
4. Busca **"Token de acceso temporal"** o genera uno permanente
5. Copia el token completo

```bash
WHATSAPP_ACCESS_TOKEN=EAAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 3. WHATSAPP_PHONE_NUMBER_ID
**Ya lo tienes**: `953020801227915`
```bash
WHATSAPP_PHONE_NUMBER_ID=953020801227915
```

### 4. WHATSAPP_BUSINESS_ACCOUNT_ID
**Ya lo tienes**: `1668996594067091`
```bash
WHATSAPP_BUSINESS_ACCOUNT_ID=1668996594067091
```

---

## 📝 Archivo .env Completo (Ejemplo)

Crea el archivo `backend/.env` con este contenido:

```bash
# ============================================
# CONFIGURACIÓN GENERAL
# ============================================
DEBUG=True
PROJECT_NAME="Sistema de Pagos"
VERSION="1.0.0"

# ============================================
# BASE DE DATOS (configurar según tu BD)
# ============================================
DATABASE_URL=postgresql://usuario:password@localhost:5432/pagos_db

# ============================================
# SEGURIDAD - JWT
# ============================================
SECRET_KEY=tu-clave-secreta-super-segura-aqui-cambiar-en-produccion
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# ============================================
# WHATSAPP / META BUSINESS API
# ============================================
# Token de verificación del webhook (TÚ LO CREAS)
WHATSAPP_VERIFY_TOKEN=rapicredit_2024_secure_token_xyz123

# Access Token de WhatsApp Business API (obtener de Meta Developers)
WHATSAPP_ACCESS_TOKEN=tu_access_token_de_meta_aqui

# Phone Number ID (de tu configuración)
WHATSAPP_PHONE_NUMBER_ID=953020801227915

# Business Account ID (de tu configuración)
WHATSAPP_BUSINESS_ACCOUNT_ID=1668996594067091

# ============================================
# EMAIL (SMTP) - Opcional
# ============================================
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=tu_email@gmail.com
SMTP_PASSWORD=tu_password_de_aplicacion
SMTP_FROM_EMAIL=tu_email@gmail.com

# ============================================
# REDIS (Cache) - Opcional
# ============================================
REDIS_URL=redis://localhost:6379/0

# ============================================
# SENTRY (Monitoreo) - Opcional
# ============================================
SENTRY_DSN=tu_sentry_dsn_aqui

# ============================================
# CORS
# ============================================
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```

---

## ✅ Checklist de Configuración

- [ ] Crear archivo `backend/.env` (copiar de `.env.example`)
- [ ] Configurar `WHATSAPP_VERIFY_TOKEN` (crear uno seguro)
- [ ] Obtener `WHATSAPP_ACCESS_TOKEN` de Meta Developers
- [ ] Configurar `WHATSAPP_PHONE_NUMBER_ID=953020801227915`
- [ ] Configurar `WHATSAPP_BUSINESS_ACCOUNT_ID=1668996594067091`
- [ ] Configurar `DATABASE_URL` (si usas base de datos)
- [ ] Configurar `SECRET_KEY` (generar uno seguro)

---

## 🔐 Generar Tokens Seguros

### Para WHATSAPP_VERIFY_TOKEN:
```python
import secrets
print(secrets.token_urlsafe(32))
```

### Para SECRET_KEY:
```python
import secrets
print(secrets.token_urlsafe(64))
```

---

## 🚨 Importante

1. **NUNCA** compartas tu `.env` o lo subas a Git
2. El `.env` ya está en `.gitignore` para protegerlo
3. En producción, usa variables de entorno del servidor (Render.com)
4. El `WHATSAPP_VERIFY_TOKEN` debe ser EXACTAMENTE el mismo en:
   - Tu archivo `.env`
   - La configuración del webhook en Meta Developers

---

## 📡 Configurar Webhook en Meta

Una vez que tengas las variables configuradas:

1. Ve a Meta Developers > Tu App > WhatsApp > Configuration
2. En **Webhook**, haz clic en **Edit**
3. Configura:
   - **Callback URL**: `https://tu-dominio.com/api/v1/whatsapp/webhook`
   - **Verify Token**: El mismo valor que `WHATSAPP_VERIFY_TOKEN` en tu `.env`
4. Haz clic en **Verify and Save**
5. Suscríbete a eventos: ✅ **messages**

---

## 🧪 Probar la Configuración

Después de configurar las variables:

```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

Luego prueba la verificación del webhook:
```bash
curl "http://localhost:8000/api/v1/whatsapp/webhook?hub.mode=subscribe&hub.challenge=123456789&hub.verify_token=rapicredit_2024_secure_token_xyz123"
```

Deberías recibir: `123456789`
