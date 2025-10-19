# 🔍 Scripts de Validación Alternativa para Causa Raíz

## 📋 Descripción

Estos scripts proporcionan una **validación alternativa** para identificar la causa raíz de los errores `401 Unauthorized` que están afectando el sistema. En lugar de depender del frontend, estos scripts prueban directamente el backend.

## 🚀 Scripts Disponibles

### 1. **`validacion_maestra_causa_raiz.py`** (Script Principal)
- **Propósito**: Ejecuta todas las validaciones automáticamente
- **Uso**: `python backend/scripts/validacion_maestra_causa_raiz.py`
- **Resultado**: Diagnóstico completo del problema

### 2. **`validar_configuracion_entorno.py`**
- **Propósito**: Verifica configuración del entorno del backend
- **Prueba**: Endpoints públicos, BD, CORS, rate limiting
- **Uso**: `python backend/scripts/validar_configuracion_entorno.py`

### 3. **`validar_configuracion_seguridad.py`**
- **Propósito**: Verifica configuración de seguridad JWT
- **Prueba**: Login, generación de tokens, endpoints protegidos
- **Uso**: `python backend/scripts/validar_configuracion_seguridad.py`

### 4. **`validar_comunicacion_frontend_backend.py`**
- **Propósito**: Simula requests del frontend real
- **Prueba**: Headers, CORS, tokens, comunicación
- **Uso**: `python backend/scripts/validar_comunicacion_frontend_backend.py`

### 5. **`validar_tokens_jwt.py`**
- **Propósito**: Valida tokens JWT específicamente
- **Prueba**: Estructura, expiración, decodificación
- **Uso**: `python backend/scripts/validar_tokens_jwt.py`

## 🛠️ Instalación y Uso

### Requisitos
```bash
pip install requests pyjwt
```

### Ejecución Rápida
```bash
# Ejecutar validación completa
python backend/scripts/validacion_maestra_causa_raiz.py

# O ejecutar validaciones individuales
python backend/scripts/validar_configuracion_entorno.py
python backend/scripts/validar_configuracion_seguridad.py
python backend/scripts/validar_comunicacion_frontend_backend.py
python backend/scripts/validar_tokens_jwt.py
```

## 📊 Interpretación de Resultados

### ✅ **Todas las Validaciones Exitosas**
- **Diagnóstico**: Backend funcionando correctamente
- **Causa**: Problema en frontend (token storage, interceptors, etc.)
- **Acción**: Revisar código del frontend

### ❌ **Validaciones Críticas Fallidas**
- **Diagnóstico**: Problema crítico en backend
- **Causa**: Configuración de servidor, BD, o autenticación
- **Acción**: Revisar configuración del backend

### ⚠️ **Validaciones Parcialmente Fallidas**
- **Diagnóstico**: Problema específico identificado
- **Causa**: Configuración específica (CORS, tokens, etc.)
- **Acción**: Revisar resultados individuales

## 🔧 Configuración

### Credenciales de Prueba
Edita los scripts para usar las credenciales correctas:
```python
TEST_EMAIL = "itmaster@rapicreditca.com"
TEST_PASSWORD = "admin123"  # Cambiar por la contraseña real
```

### URLs
Los scripts usan las URLs de producción por defecto:
- Backend: `https://pagos-f2qf.onrender.com`
- Frontend: `https://rapicredit.onrender.com`

## 📝 Logs y Debugging

Cada script genera logs detallados que incluyen:
- Status codes HTTP
- Headers de respuesta
- Estructura de tokens JWT
- Errores específicos
- Diagnósticos automáticos

## 🎯 Casos de Uso

### 1. **Problema de Autenticación**
- Ejecutar `validar_tokens_jwt.py`
- Verificar estructura y expiración de tokens

### 2. **Problema de CORS**
- Ejecutar `validar_comunicacion_frontend_backend.py`
- Verificar headers CORS

### 3. **Problema de Base de Datos**
- Ejecutar `validar_configuracion_entorno.py`
- Verificar endpoints de BD

### 4. **Problema General**
- Ejecutar `validacion_maestra_causa_raiz.py`
- Obtener diagnóstico completo

## 🚨 Notas Importantes

1. **Credenciales**: Asegúrate de usar credenciales válidas en los scripts
2. **Timeouts**: Los scripts tienen timeouts de 10-60 segundos
3. **Rate Limiting**: Los scripts respetan límites de velocidad
4. **Logs**: Revisa todos los logs generados para diagnóstico completo

## 📞 Soporte

Si los scripts no resuelven el problema, proporciona:
1. Output completo de `validacion_maestra_causa_raiz.py`
2. Logs específicos del backend
3. Configuración actual del entorno
