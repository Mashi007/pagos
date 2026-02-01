# 🔐 Cómo Crear el Verify Token para WhatsApp

## ✅ Respuesta Rápida

**El Verify Token lo CREAS TÚ** - No se obtiene de Meta. Es un token secreto que tú inventas y debes usar el mismo en:
1. Tu aplicación (archivo `.env` o Render)
2. Meta Developers (al configurar el webhook)

---

## 🎯 ¿Qué es el Verify Token?

Es un **string secreto** que Meta usa para verificar que el webhook realmente pertenece a tu aplicación. Puede ser cualquier texto seguro que tú elijas.

---

## 📝 Cómo Crear el Verify Token

### Opción 1: Crear uno Manualmente (Más Simple)

Simplemente inventa un string seguro, por ejemplo:

```
rapicredit_2024_secure_token_xyz123
```

O algo más complejo:

```
mi_token_secreto_whatsapp_2024_abc123xyz
```

### Opción 2: Generar uno Aleatorio con Python

Si quieres uno más seguro y aleatorio:

```python
import secrets

# Generar token seguro
token = secrets.token_urlsafe(32)
print(token)
```

Esto generará algo como:
```
xK9mP2qR7vN4wL8tY3zA6bC1dE5fG0hI
```

### Opción 3: Generar con OpenSSL (Terminal)

```bash
openssl rand -hex 32
```

---

## ✅ Pasos para Usar el Verify Token

### Paso 1: Crear el Token

Elige uno de los métodos anteriores y crea tu token. Ejemplo:
```
rapicredit_2024_secure_token_xyz123
```

### Paso 2: Configurarlo en tu Aplicación

**En desarrollo local** (`backend/.env`):
```bash
WHATSAPP_VERIFY_TOKEN=rapicredit_2024_secure_token_xyz123
```

**En Render** (Dashboard > Environment):
```
WHATSAPP_VERIFY_TOKEN=rapicredit_2024_secure_token_xyz123
```

### Paso 3: Configurarlo en Meta Developers

1. Ve a [Meta Developers](https://developers.facebook.com/)
2. Selecciona tu aplicación
3. Ve a **WhatsApp** > **Configuration**
4. En la sección **Webhook**, haz clic en **Edit** o **Configurar**
5. En el campo **"Verify Token"**, ingresa **EXACTAMENTE** el mismo token:
   ```
   rapicredit_2024_secure_token_xyz123
   ```
6. Guarda la configuración

---

## ⚠️ IMPORTANTE

1. **Debe ser EXACTAMENTE el mismo** en ambos lados:
   - Tu aplicación (`.env` o Render)
   - Meta Developers (configuración del webhook)

2. **Puede ser cualquier texto** que elijas, pero:
   - Usa algo seguro (no "123" o "password")
   - Guárdalo en un lugar seguro
   - No lo compartas públicamente

3. **No lo cambies** una vez configurado, a menos que necesites reconfigurar el webhook

---

## 🧪 Probar que Funciona

Una vez configurado en ambos lados, Meta enviará un GET request para verificar:

```
GET /api/v1/whatsapp/webhook?hub.mode=subscribe&hub.challenge=123456789&hub.verify_token=rapicredit_2024_secure_token_xyz123
```

Si el token coincide, tu aplicación responderá con el `hub.challenge` y Meta confirmará que el webhook está configurado correctamente.

---

## 📋 Resumen

| Item | Dónde Obtenerlo |
|------|----------------|
| **Verify Token** | ✅ **TÚ LO CREAS** - No viene de Meta |
| **Access Token** | ✅ **De Meta Developers** - Ya lo tienes |
| **Phone Number ID** | ✅ **De Meta Developers** - Ya lo tienes (953020801227915) |
| **Business Account ID** | ✅ **De Meta Developers** - Ya lo tienes (1668996594067091) |

---

## 💡 Ejemplo Completo

1. **Crear token**: `rapicredit_2024_secure_token_xyz123`

2. **En `.env` o Render**:
   ```bash
   WHATSAPP_VERIFY_TOKEN=rapicredit_2024_secure_token_xyz123
   ```

3. **En Meta Developers**:
   - Webhook > Verify Token: `rapicredit_2024_secure_token_xyz123`

4. **¡Listo!** El webhook se verificará automáticamente cuando Meta lo intente.

---

**En resumen**: El Verify Token es como una contraseña secreta que tú inventas y compartes solo con Meta para verificar que eres tú quien controla el webhook. 🎯
