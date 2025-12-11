# 🔧 Solución: Error de Codificación en DATABASE_URL

## ❌ Problema Detectado

**Error:**
```
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xf3 in position 85: invalid continuation byte
```

**Causa:**
La `DATABASE_URL` en `backend/.env` contiene caracteres especiales (probablemente en la contraseña) que no están codificados correctamente para URLs.

El byte `0xf3` en latin-1 corresponde a "ó", lo que sugiere que hay caracteres acentuados o especiales en la contraseña que no están codificados.

## ✅ Solución Aplicada

Se mejoró el código en `backend/app/db/session.py` para:

1. **Detectar y decodificar correctamente** la URL si viene como bytes
2. **Codificar automáticamente** username y password usando `urllib.parse.quote_plus()`
3. **Reconstruir la URL** con los caracteres especiales correctamente codificados

## 🔧 Cómo Corregir Manualmente

Si el problema persiste, puedes corregir manualmente la `DATABASE_URL` en `backend/.env`:

### Opción 1: Codificar la Contraseña Manualmente

Si tu contraseña tiene caracteres especiales (ó, ñ, etc.), codifícala usando Python:

```python
from urllib.parse import quote_plus

password = "tu_contraseña_con_ó"
password_encoded = quote_plus(password)
print(password_encoded)
```

Luego usa `password_encoded` en tu `DATABASE_URL`:

```
DATABASE_URL=postgresql://usuario:password_encoded@host:puerto/database
```

### Opción 2: Usar Caracteres ASCII

Cambia la contraseña en PostgreSQL para usar solo caracteres ASCII (sin acentos ni caracteres especiales).

### Opción 3: Verificar el Archivo .env

Asegúrate de que el archivo `backend/.env` esté guardado en **UTF-8 sin BOM**.

## 📋 Verificación

Para verificar que la corrección funcionó:

1. **Verificar que el archivo .env existe:**
```powershell
cd backend
Test-Path .env
```

2. **Verificar que DATABASE_URL está configurada:**
```powershell
Get-Content .env | Select-String "DATABASE_URL"
```

3. **Probar conexión:**
```python
from app.db.session import SessionLocal, test_connection
if test_connection():
    print("✅ Conexión exitosa")
else:
    print("❌ Error de conexión")
```

## 🎯 Estado Actual

- ✅ Código mejorado en `session.py` para manejar codificación
- ⚠️ Necesita verificar que la `DATABASE_URL` en `.env` esté correctamente codificada
- ⚠️ Si el problema persiste, aplicar una de las soluciones manuales arriba

