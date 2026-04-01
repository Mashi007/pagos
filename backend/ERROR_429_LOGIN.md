# Solución: Error 429 en Login (Demasiados Intentos)

## 📋 Qué Pasó

El servidor bloqueó los intentos de login porque:
- **5+ intentos de login en 60 segundos** desde tu IP → Error 429
- Es una protección contra ataques de fuerza bruta

## ✅ Soluciones

### Solución 1: Esperar 1 Minuto (Más Simple)

Simplemente **espera 60 segundos** y vuelve a intentar.

El rate limit se limpia automáticamente después de 1 minuto.

---

### Solución 2: Limpiar Rate Limit (Inmediato)

Si necesitas acceso inmediato, hay un endpoint de admin que limpia el rate limit:

#### Paso 1: Necesitas el SECRET para limpiar

En **Render → Environment Variables**, busca: `ADMIN_SECRET_CLEAR_LIMITS`

#### Paso 2: Ejecuta en terminal o Postman

```bash
curl -X POST https://pagos-f2qf.onrender.com/api/v1/auth/clear-rate-limits \
  -H "X-Admin-Secret: TU_ADMIN_SECRET_CLEAR_LIMITS" \
  -H "Content-Type: application/json"
```

#### Respuesta esperada:
```json
{
  "message": "Rate limits limpiados",
  "ips_cleared": 1
}
```

#### Paso 3: Vuelve a intentar login

Ahora puedes intentar login de nuevo.

---

### Solución 3: Usar Admin Desde ENV (Bypass BD)

Si el usuario no existe en BD, puedes usar las credenciales de admin desde variables de entorno:

**En Render → Environment Variables:**
- `ADMIN_EMAIL`: email del admin
- `ADMIN_PASSWORD`: contraseña del admin

Si configuras estos, login funcionará incluso sin usuarios en BD.

---

## 🛡️ Rate Limit Actual

```
Login: 5 intentos por 60 segundos
Olvido de contraseña: 3 solicitudes por 15 minutos
```

---

## 🔧 Cambiar Rate Limit (Para Developers)

Si necesitas ajustar el rate limit, edita:

**Archivo:** `backend/app/api/v1/endpoints/auth.py`

```python
# Líneas 42-43
_LOGIN_RATE_LIMIT_WINDOW = 60  # segundos (cambiar aquí)
_LOGIN_RATE_LIMIT_MAX = 5      # intentos (cambiar aquí)
```

Ejemplo: Para 10 intentos en 2 minutos:
```python
_LOGIN_RATE_LIMIT_WINDOW = 120  # 2 minutos
_LOGIN_RATE_LIMIT_MAX = 10      # 10 intentos
```

Luego:
```bash
git add -A
git commit -m "Adjust login rate limit"
git push
```

---

## 📊 Debugging

### Ver intentos de login bloqueados

En logs de Render, busca:
```
Demasiados intentos de inicio de sesión
```

### Ver todas las IPs bloqueadas

El servidor mantiene en memoria todas las IPs con intentos recientes. Se limpia automáticamente después de 60 segundos.

---

## ✔️ Checklist para Recuperar Acceso

- [ ] ¿Espaste 60 segundos?
- [ ] ¿Email y password correctos?
- [ ] ¿Configuraste ADMIN_EMAIL y ADMIN_PASSWORD en Render?
- [ ] ¿El usuario existe en BD?
- [ ] ¿Es una conexión privada o empresa con firewall?

---

## 🎯 Paso a Paso para Ingresar Ahora

### 1. Espera 60 segundos
```
Intento bloqueado a las 15:30 → Intenta de nuevo a las 15:31
```

### 2. Ve a login: `https://pagos-f2qf.onrender.com`

### 3. Ingresa credenciales:
- Email: El que creaste
- Password: El que configuraste

### 4. ¿Sigue dando 429?
- [ ] Sí → Usa Solución 2 (limpiar rate limit con secreto)
- [ ] No → Intenta credenciales ADMIN_EMAIL / ADMIN_PASSWORD

---

## 🚨 Error 500 + 429

Si ves ambos errores:

1. **Primero 500** → Error en backend
2. **Luego 429** → Rate limit por intentos fallidos

**Solución:**
1. Verifica logs del backend en Render
2. Espera 60 segundos
3. Vuelve a intentar

---

## 🔐 Configurar Credenciales Admin en Render

Si no tienes usuario en BD, configura en **Render → Environment Variables**:

```
ADMIN_EMAIL=tuadmin@empresa.com
ADMIN_PASSWORD=TuPasswordSeguro123
```

Luego login funcionará con esas credenciales.

---

## 📝 Resumen Rápido

| Situación | Solución |
|-----------|----------|
| Bloqueado por 429 | Espera 60 segundos |
| Necesita acceso inmediato | Limpia rate limit con secreto |
| No hay usuarios en BD | Configura ADMIN_EMAIL/PASSWORD |
| Sigue fallando | Revisa logs de Render |

¡Listo! 🚀
