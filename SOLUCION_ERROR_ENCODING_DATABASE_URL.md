# 🔧 SOLUCIÓN: Error de Encoding en DATABASE_URL

## 🚨 Problema

Error al ejecutar el script de reconciliación:
```
UnicodeDecodeError: 'utf-8' codec can't decode byte 0xf3 in position 85: invalid continuation byte
```

**Causa:** La variable de entorno `DATABASE_URL` contiene caracteres especiales (probablemente en la contraseña) que no son UTF-8 válidos.

---

## ✅ SOLUCIÓN

### Opción 1: Codificar la contraseña en la URL (Recomendado)

Si tu contraseña tiene caracteres especiales, debes codificarlos usando URL encoding.

**Ejemplo:**
```powershell
# Si tu contraseña es: "mí_contraseña123"
# Debe codificarse como: "m%C3%AD_contrase%C3%B1a123"

# URL original (con error):
# postgresql://usuario:mí_contraseña123@host:5432/database

# URL corregida:
# postgresql://usuario:m%C3%AD_contrase%C3%B1a123@host:5432/database
```

**Herramienta para codificar:**
```python
from urllib.parse import quote_plus
password = "mí_contraseña123"
encoded = quote_plus(password)
print(encoded)  # m%C3%AD_contrase%C3%B1a123
```

---

### Opción 2: Configurar DATABASE_URL en PowerShell

```powershell
# 1. Obtener la URL actual (si existe)
$env:DATABASE_URL

# 2. Si tiene caracteres especiales, codificarlos manualmente
# Ejemplo: Si la contraseña es "mí_contraseña123"
# Usar: "m%C3%AD_contrase%C3%B1a123"

# 3. Configurar la URL codificada
$env:DATABASE_URL = "postgresql://usuario:contraseña_codificada@host:5432/database"

# 4. Verificar que se configuró correctamente
$env:DATABASE_URL

# 5. Ejecutar el script
py backend/scripts/reconciliar_pagos_cuotas.py
```

---

### Opción 3: Usar archivo .env (Recomendado para desarrollo)

1. **Crear archivo `.env` en la raíz del proyecto:**
```env
DATABASE_URL=postgresql://usuario:contraseña_codificada@host:5432/database
```

2. **Instalar python-dotenv:**
```powershell
py -m pip install python-dotenv
```

3. **Modificar el script para cargar .env:**
```python
from dotenv import load_dotenv
load_dotenv()
```

---

### Opción 4: Script Python para codificar la URL

Crea un script temporal para codificar tu contraseña:

```python
# codificar_password.py
from urllib.parse import quote_plus

# Ingresa tu contraseña aquí
password = input("Ingresa tu contraseña: ")
encoded = quote_plus(password)
print(f"Contraseña codificada: {encoded}")
print(f"\nURL completa (reemplaza [PASSWORD] con la contraseña codificada):")
print(f"postgresql://usuario:{encoded}@host:5432/database")
```

**Ejecutar:**
```powershell
py codificar_password.py
```

---

## 🔍 VERIFICAR DATABASE_URL

Para verificar si tu `DATABASE_URL` tiene problemas de encoding:

```powershell
# Ver la URL actual
$env:DATABASE_URL

# Intentar decodificarla
python -c "import os; print(os.getenv('DATABASE_URL', '').encode('utf-8', errors='replace'))"
```

---

## 📝 PASOS RECOMENDADOS

1. **Obtener tu DATABASE_URL actual:**
   ```powershell
   $env:DATABASE_URL
   ```

2. **Si tiene caracteres especiales, codificarlos:**
   - Usa la herramienta online: https://www.urlencoder.org/
   - O usa el script Python de arriba

3. **Configurar la URL codificada:**
   ```powershell
   $env:DATABASE_URL = "postgresql://usuario:contraseña_codificada@host:5432/database"
   ```

4. **Ejecutar el script:**
   ```powershell
   py backend/scripts/reconciliar_pagos_cuotas.py
   ```

---

## ⚠️ IMPORTANTE

- **NUNCA** compartas tu `DATABASE_URL` con contraseñas en texto plano
- **SIEMPRE** codifica caracteres especiales en contraseñas
- **USA** variables de entorno o archivos `.env` (no los subas a Git)

---

## 🆘 Si el problema persiste

Si después de codificar la contraseña el problema persiste:

1. Verifica que la URL esté correctamente formateada
2. Verifica que tengas acceso a la base de datos
3. Prueba conectarte manualmente con `psql` o DBeaver
4. Revisa los logs del servidor de base de datos

