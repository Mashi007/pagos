# 📱 Guía de Configuración de WhatsApp con Meta Developers

## ⚡ RESUMEN RÁPIDO - Qué Necesitas

### 🔴 **CAMPOS OBLIGATORIOS** (Debes completarlos):

1. **Access Token** ⭐
   - **Dónde**: Meta Developers → WhatsApp → API Setup
   - **Qué es**: Token que comienza con `EAA...`
   - **Enlace**: https://developers.facebook.com/apps/1093645312947179/whatsapp-business/cloud-api/get-started

2. **Phone Number ID** ⭐
   - **Dónde**: Misma página (WhatsApp → API Setup)
   - **Qué es**: Número largo (15-17 dígitos) del número de teléfono
   - **Enlace**: Mismo que arriba

### 🟡 **CAMPOS OPCIONALES** (Puedes dejarlos vacíos por ahora):

3. **Business Account ID** - Opcional
4. **Webhook Verify Token** - Opcional (solo si recibes mensajes)

### ✅ **YA CONFIGURADO**:
- **API URL**: `https://graph.facebook.com/v18.0` (no cambiar)

---

## 🎯 Información de tu Aplicación Meta

Basándote en la imagen de configuración que compartiste, tienes:

- **Application ID**: `1093645312947179`
- **Application Name**: `Angelica`
- **Contact Email**: `contacto@kohde.us`
- **Privacy Policy URL**: `https://kohde.us/privacidad`

---

## 🎯 CAMPOS IMPORTANTES - Dónde Encontrarlos en Meta Developers

### ⭐ **CAMPOS OBLIGATORIOS** (Debes completarlos)

---

### 1. **Access Token (Token de Acceso)** ⭐ **MÁS IMPORTANTE**

**📍 Dónde encontrarlo:**

1. **Abre tu navegador** y ve a: https://developers.facebook.com/apps/1093645312947179
2. **En el menú lateral izquierdo**, busca y haz clic en **"WhatsApp"**
3. **Dentro de WhatsApp**, haz clic en **"API Setup"** (Configuración de API)
4. **En la página de API Setup**, busca la sección que dice:
   - **"Temporary access token"** (Token de acceso temporal) O
   - **"Access tokens"** (Tokens de acceso)
5. **Verás un campo de texto** con un token que comienza con `EAA...`
6. **Haz clic en el botón "Copy"** o selecciona y copia todo el token

**📋 Qué buscar visualmente:**
- Busca un campo que diga "Access Token" o "Temporary access token"
- El token es una cadena larga que comienza con `EAA`
- Ejemplo: `EAAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

**⚠️ IMPORTANTE**:
- Los tokens temporales expiran en 1 hora
- Para producción, necesitas generar un token permanente
- **Copia el token completo** (es muy largo, asegúrate de copiarlo todo)

**🔗 Enlace directo**: https://developers.facebook.com/apps/1093645312947179/whatsapp-business/cloud-api/get-started

---

### 2. **Phone Number ID (ID del Número de Teléfono)** ⭐ **OBLIGATORIO**

**📍 Dónde encontrarlo:**

1. **En la MISMA página** donde encontraste el Access Token (WhatsApp → API Setup)
2. **Busca la sección** que dice **"From"** o **"Phone number ID"**
3. **Verás un número largo** (15-17 dígitos) junto al nombre de tu número de teléfono
4. **Copia ese número** completo

**📋 Qué buscar visualmente:**
- Busca un campo que muestre tu número de teléfono de WhatsApp
- Al lado o debajo del número, verás un ID numérico largo
- Ejemplo: `123456789012345` o `12345678901234567`
- Puede estar etiquetado como "Phone number ID" o simplemente mostrar el número

**⚠️ IMPORTANTE**:
- Este es el ID del número de teléfono que usarás para enviar mensajes
- Debe estar verificado en Meta Business
- Si no tienes un número, necesitas agregar uno primero

**🔗 Enlace directo**: https://developers.facebook.com/apps/1093645312947179/whatsapp-business/cloud-api/get-started

---

### 3. **API URL** ✅ (Ya está configurado)

**📍 Valor por defecto:**
- `https://graph.facebook.com/v18.0`
- **NO necesitas cambiarlo**, ya está correcto en tu formulario

---

### ⭐ **CAMPOS OPCIONALES** (Puedes completarlos después)

---

### 4. **Business Account ID (ID de la Cuenta de Negocio)** - Opcional

**📍 Dónde encontrarlo:**

1. **En la misma página** de WhatsApp → API Setup
2. **Busca la sección** que dice:
   - **"WhatsApp Business Account ID"** O
   - **"Business Account ID"** O
   - **"Account ID"**
3. **Copia el ID numérico** (similar al Phone Number ID)

**📋 Qué buscar visualmente:**
- Un número largo similar al Phone Number ID
- Puede estar en una sección separada o cerca del Phone Number ID
- Si no lo ves, es posible que no lo necesites (es opcional)

**⚠️ NOTA**: Este campo es opcional. Si no lo encuentras, puedes dejarlo vacío.

---

### 5. **Webhook Verify Token (Token de Verificación del Webhook)** - Opcional

**📍 Dónde configurarlo (TÚ lo creas):**

1. **Ve a**: WhatsApp → **"Configuration"** (Configuración) → **"Webhook"**
2. **En el campo "Verify token"**, **TÚ debes escribir** un token secreto
   - Ejemplo: `mi_token_secreto_2024_kohde`
   - Debe ser una cadena segura y única que tú elijas
3. **Guarda ese token** que acabas de crear
4. **Usa el mismo token** en tu aplicación

**📋 Qué hacer:**
- Este token **NO existe todavía**, **TÚ lo creas**
- Elige una cadena segura (puede ser cualquier cosa que tú quieras)
- Ejemplo: `kohde_whatsapp_token_2024` o `mi_token_secreto`
- **IMPORTANTE**: Debe ser el mismo en Meta y en tu aplicación

**⚠️ IMPORTANTE**:
- Este token es para verificar que los webhooks vienen de Meta
- Solo es necesario si vas a recibir mensajes de clientes
- Si solo vas a enviar mensajes, puedes dejarlo vacío

**🔗 Enlace directo**: https://developers.facebook.com/apps/1093645312947179/whatsapp-business/cloud-api/webhooks

---

## 📸 PASOS VISUALES - Cómo Encontrar los Valores

### Paso 1: Acceder a Meta Developers

1. **Abre tu navegador** (Chrome, Firefox, Edge, etc.)
2. **Ve a esta URL**: https://developers.facebook.com/apps/1093645312947179
3. **Inicia sesión** con tu cuenta de Facebook/Meta si es necesario
4. **Verás el panel** de tu aplicación "Angelica"

### Paso 2: Ir a WhatsApp API Setup

1. **En el menú lateral izquierdo**, busca la sección **"WhatsApp"**
   - Puede estar en la parte superior del menú
   - O en una sección expandible
2. **Haz clic en "WhatsApp"**
3. **Dentro de WhatsApp**, busca y haz clic en **"API Setup"**
   - También puede decir "Configuración de API" o "API Setup"

### Paso 3: Encontrar el Access Token

**En la página de API Setup, busca:**

```
┌─────────────────────────────────────────┐
│  WhatsApp API Setup                    │
├─────────────────────────────────────────┤
│                                         │
│  Temporary access token                 │
│  ┌───────────────────────────────────┐  │
│  │ EAAxxxxxxxxxxxxxxxxxxxxxxxxxxxxx │  │  ← ESTE ES EL TOKEN
│  └───────────────────────────────────┘  │
│  [Copy] [Generate New Token]            │
│                                         │
└─────────────────────────────────────────┘
```

**Qué hacer:**
- Busca el campo que dice "Temporary access token" o "Access token"
- Verás un token largo que comienza con `EAA`
- Haz clic en **"Copy"** o selecciona y copia todo el token
- **Pégalo en tu aplicación** en el campo "Access Token"

### Paso 4: Encontrar el Phone Number ID

**En la MISMA página de API Setup, busca:**

```
┌─────────────────────────────────────────┐
│  From                                   │
│  ┌───────────────────────────────────┐  │
│  │ +58 412 1234567                  │  │  ← Tu número de teléfono
│  └───────────────────────────────────┘  │
│                                         │
│  Phone number ID                        │
│  123456789012345                        │  ← ESTE ES EL ID
│                                         │
└─────────────────────────────────────────┘
```

**O puede aparecer así:**

```
┌─────────────────────────────────────────┐
│  Phone number ID: 123456789012345      │  ← Copia este número
│                                         │
└─────────────────────────────────────────┘
```

**Qué hacer:**
- Busca la sección "From" o "Phone number ID"
- Verás un número largo (15-17 dígitos)
- **Copia ese número completo**
- **Pégalo en tu aplicación** en el campo "Phone Number ID"

### Paso 5: (Opcional) Business Account ID

**En la misma página, busca:**

```
┌─────────────────────────────────────────┐
│  WhatsApp Business Account ID           │
│  987654321098765                        │  ← Si lo ves, cópialo
│                                         │
└─────────────────────────────────────────┘
```

**Nota**: Si no lo ves, no te preocupes, es opcional.

---

## 🔧 Configuración en tu Aplicación (Interfaz de Usuario)

Una vez que tengas los valores de Meta Developers, debes configurarlos en tu aplicación:

### Campos Requeridos (Obligatorios):

1. **API URL**
   - Valor por defecto: `https://graph.facebook.com/v18.0`
   - Generalmente no necesitas cambiarlo

2. **Access Token** ⭐ **REQUERIDO**
   - Valor: El token que obtuviste de Meta Developers
   - Formato: `EAAxxxxxxxxxxxxx`

3. **Phone Number ID** ⭐ **REQUERIDO**
   - Valor: El ID del número de teléfono de Meta
   - Formato: Número largo (ej: `123456789012345`)

### Campos Opcionales:

4. **Business Account ID**
   - Valor: El ID de la cuenta de negocio (si lo tienes)

5. **Webhook Verify Token**
   - Valor: El token que configuraste en Meta para verificar webhooks

### Configuración de Ambiente:

6. **Ambiente de Envío**
   - **Producción**: Envía mensajes reales a los clientes
   - **Pruebas**: Todos los mensajes se redirigen a un número de prueba

7. **Teléfono de Pruebas** (solo si usas modo pruebas)
   - Formato: `+584121234567` (con código de país)

---

## 📋 Checklist de Configuración

### En Meta Developers:

- [ ] ✅ Application ID ya configurado: `1093645312947179`
- [ ] ✅ Application Name configurado: `Angelica`
- [ ] ✅ Contact Email configurado: `contacto@kohde.us`
- [ ] ✅ Privacy Policy URL configurada: `https://kohde.us/privacidad`
- [ ] ⚠️ **Obtener Application Secret Key** (hacer clic en "Mostrar")
- [ ] ⚠️ **Obtener Access Token** (WhatsApp → API Setup)
- [ ] ⚠️ **Obtener Phone Number ID** (WhatsApp → API Setup)
- [ ] ⚠️ **Obtener Business Account ID** (opcional, WhatsApp → API Setup)
- [ ] ⚠️ **Configurar Webhook Verify Token** (WhatsApp → Configuration → Webhook)

### En tu Aplicación (Interfaz de Configuración):

- [ ] Configurar **Access Token**
- [ ] Configurar **Phone Number ID**
- [ ] Configurar **Business Account ID** (opcional)
- [ ] Configurar **Webhook Verify Token** (opcional)
- [ ] Seleccionar **Ambiente** (Producción o Pruebas)
- [ ] Si usas modo pruebas, configurar **Teléfono de Pruebas**
- [ ] Guardar configuración
- [ ] Ejecutar **Test Completo** para verificar

---

## 🔗 Enlaces Útiles

- **Meta Developers Dashboard**: https://developers.facebook.com/apps
- **Tu App específica**: https://developers.facebook.com/apps/1093645312947179
- **WhatsApp API Setup**: https://developers.facebook.com/apps/1093645312947179/whatsapp-business/cloud-api/get-started
- **Documentación de WhatsApp API**: https://developers.facebook.com/docs/whatsapp

---

## ⚠️ Notas Importantes

1. **Seguridad del Access Token**:
   - Nunca compartas tu Access Token públicamente
   - Los tokens temporales expiran rápidamente
   - Para producción, usa tokens permanentes

2. **Webhook Configuration**:
   - Si planeas recibir mensajes de clientes, necesitas configurar el webhook
   - El webhook requiere una URL pública accesible desde internet
   - Debe usar HTTPS en producción

3. **Modo Pruebas vs Producción**:
   - **Pruebas**: Todos los mensajes van a un número de prueba (recomendado para desarrollo)
   - **Producción**: Los mensajes van a los números reales de los clientes

4. **Rate Limits de Meta**:
   - 1,000 mensajes por día (nivel gratuito)
   - 80 mensajes por segundo
   - Tu aplicación maneja estos límites automáticamente

---

## 🧪 Pruebas

Después de configurar todo:

1. **Test Completo**: Usa el botón "Test Completo" en la interfaz de configuración
2. **Mensaje de Prueba**: Envía un mensaje de prueba a tu número
3. **Verificar Envíos**: Revisa la sección "Verificación de Envíos Recientes"

---

## 📞 Soporte

Si tienes problemas:
1. Revisa los logs de la aplicación
2. Verifica que todos los campos requeridos estén completos
3. Asegúrate de que el Access Token no haya expirado
4. Verifica que el Phone Number ID sea correcto

