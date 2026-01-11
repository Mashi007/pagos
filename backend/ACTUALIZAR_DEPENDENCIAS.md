# 🔒 GUÍA RÁPIDA: ACTUALIZAR DEPENDENCIAS DE SEGURIDAD

## ⚡ Actualización Rápida

```bash
# Desde el directorio backend/
cd backend

# 1. Actualizar pip
python -m pip install --upgrade pip>=25.3

# 2. Actualizar dependencias vulnerables
python -m pip install --upgrade "aiohttp>=3.13.3" "starlette>=0.49.1" "mcp>=1.23.0"

# 3. Verificar vulnerabilidades
python -m pip_audit

# 4. Probar aplicación
python -m uvicorn app.main:app --reload
```

## 📋 Vulnerabilidades Corregidas

- ✅ **aiohttp**: 8 CVEs → Actualizado a 3.13.3
- ✅ **starlette**: 2 CVEs → Actualizado a 0.49.1 (vía fastapi)
- ✅ **mcp**: 2 CVEs → Actualizado a 1.23.0
- ✅ **pip**: 1 CVE → Actualizado a 25.3
- ⚠️ **ecdsa**: 1 CVE → Sin fix (dependencia indirecta)

## ⚠️ Nota sobre ecdsa

`ecdsa` tiene una vulnerabilidad conocida (CVE-2024-23342) pero **no hay fix disponible**. 
Es una dependencia indirecta de `python-jose[cryptography]`. 
El riesgo es bajo para uso general, pero revisar si se usa directamente en código crítico.

## ✅ Verificación

Después de actualizar, ejecutar:
```bash
python -m pip_audit  # Debe mostrar 0 vulnerabilidades (excepto ecdsa)
pytest              # Verificar que tests pasan
```
