# 🚀 Guía Rápida de Configuración - WhatsApp

## 📋 Variables que DEBES Configurar

Basado en tu configuración de Meta Developers, necesitas configurar estas **4 variables principales**:

### ✅ 1. WHATSAPP_VERIFY_TOKEN (TÚ LO CREAS)
**Valor**: Crea un token seguro, por ejemplo:
```
rapicredit_2024_secure_token_xyz123
```

**⚠️ IMPORTANTE**: Este mismo token debes ingresarlo en Meta Developers cuando configures el webhook.

### 🔑 2. WHATSAPP_ACCESS_TOKEN (OBTENER DE META)
**Dónde obtenerlo**:
1. Ve a [Meta Developers](https://developers.facebook.com/)
2. Selecciona tu aplicación (ID: `25594371996899430`)
3. Ve a **WhatsApp** > **API Setup**
4. Busca **"Token de acceso temporal"**
5. O genera uno permanente en: **Configuración** > **Básica** > **Token de acceso**

**Ejemplo**:
```
EAAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### ✅ 3. WHATSAPP_PHONE_NUMBER_ID (YA LO TIENES)
**Valor**: `953020801227915`

### ✅ 4. WHATSAPP_BUSINESS_ACCOUNT_ID (YA LO TIENES)
**Valor**: `1668996594067091`

---

## 📝 Pasos para Configurar

### Paso 1: Crear archivo .env

```bash
cd backend
cp .env.example .env
```

### Paso 2: Editar .env con tus valores

Abre `backend/.env` y configura:

```bash
# Token de verificación (CREA UNO SEGURO)
WHATSAPP_VERIFY_TOKEN=rapicredit_2024_secure_token_xyz123

# Access Token (OBTENER DE META DEVELOPERS)
WHATSAPP_ACCESS_TOKEN=tu_access_token_aqui

# Phone Number ID (YA LO TIENES)
WHATSAPP_PHONE_NUMBER_ID=953020801227915

# Business Account ID (YA LO TIENES)
WHATSAPP_BUSINESS_ACCOUNT_ID=1668996594067091
```

### Paso 3: Configurar Webhook en Meta Developers

1. Ve a [Meta Developers](https://developers.facebook.com/)
2. Selecciona tu aplicación
3. Ve a **WhatsApp** > **Configuration**
4. En **Webhook**, haz clic en **Edit**
5. Configura:
   - **Callback URL**: `https://tu-dominio.com/api/v1/whatsapp/webhook`
     - Para desarrollo local con ngrok: `https://tu-url-ngrok.ngrok.io/api/v1/whatsapp/webhook`
   - **Verify Token**: El mismo que configuraste en `.env` (ej: `rapicredit_2024_secure_token_xyz123`)
6. Haz clic en **Verify and Save**
7. Suscríbete a eventos: ✅ **messages**

### Paso 4: Probar

```bash
# Iniciar servidor
cd backend
python -m uvicorn app.main:app --reload --port 8000

# En otra terminal, probar verificación
curl "http://localhost:8000/api/v1/whatsapp/webhook?hub.mode=subscribe&hub.challenge=123456789&hub.verify_token=rapicredit_2024_secure_token_xyz123"
```

Deberías recibir: `123456789`

---

## 📊 Resumen de tus Valores

| Variable | Valor | Estado |
|----------|-------|--------|
| **Application ID** | `25594371996899430` | ✅ Ya lo tienes |
| **Phone Number ID** | `953020801227915` | ✅ Configurar en .env |
| **Business Account ID** | `1668996594067091` | ✅ Configurar en .env |
| **Número WhatsApp** | `+58 424 4359435` | ✅ Referencia |
| **Verify Token** | `tu_token_seguro` | ⚠️ CREAR |
| **Access Token** | `EAA...` | ⚠️ OBTENER DE META |

---

## 🔐 Generar Token Seguro

Para generar un token seguro para `WHATSAPP_VERIFY_TOKEN`:

```python
import secrets
print(secrets.token_urlsafe(32))
```

O simplemente usa algo como:
```
rapicredit_2024_secure_token_xyz123
```

---

## ⚠️ Importante

1. **NUNCA** compartas tu archivo `.env`
2. El `.env` ya está en `.gitignore` (no se subirá a Git)
3. El `WHATSAPP_VERIFY_TOKEN` debe ser **EXACTAMENTE** el mismo en:
   - Tu archivo `.env`
   - La configuración del webhook en Meta Developers
4. Para desarrollo local, usa **ngrok** para exponer tu servidor:
   ```bash
   ngrok http 8000
   ```
   Usa la URL de ngrok como Callback URL en Meta.

---

## 🆘 ¿Necesitas Ayuda?

- Revisa `backend/WHATSAPP_SETUP.md` para guía detallada
- Revisa `backend/CONFIGURACION_VARIABLES.md` para todas las variables
- Ejecuta `python backend/test_whatsapp_webhook.py` para pruebas
