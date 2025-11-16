# 🔧 Configuración de Producción

**Última actualización:** 2025-11-16

---

## 📋 Variables de Entorno Requeridas

### 🔴 CRÍTICAS (Deben configurarse)

Estas variables son **obligatorias** para producción. Sin ellas, la aplicación usará valores por defecto inseguros:

#### 1. **ADMIN_EMAIL**
- **Descripción:** Email del administrador del sistema
- **Valor por defecto:** `itmaster@rapicreditca.com` (⚠️ NO usar en producción)
- **Ejemplo:** `admin@tudominio.com`
- **Configuración en Render:**
  ```
  ADMIN_EMAIL=admin@tudominio.com
  ```
- **⚠️ ADVERTENCIA:** Si no se configura, aparecerá un mensaje crítico en los logs

#### 2. **ADMIN_PASSWORD**
- **Descripción:** Contraseña del administrador
- **Valor por defecto:** `R@pi_2025**` (⚠️ NO usar en producción)
- **Requisitos:**
  - Mínimo 8 caracteres (recomendado 12+)
  - Debe contener: mayúsculas, minúsculas y números o caracteres especiales
- **Ejemplo:** `Admin2025@RapiCredit!Secure`
- **Configuración en Render:**
  ```
  ADMIN_PASSWORD=TuContraseñaSegura123!@#
  ```
- **⚠️ ADVERTENCIA:** Si no se configura, aparecerá un mensaje crítico en los logs

#### 3. **SECRET_KEY**
- **Descripción:** Clave secreta para JWT y encriptación
- **Requisitos:** Mínimo 32 caracteres
- **Generación:**
  ```python
  import secrets
  secrets.token_urlsafe(32)
  ```
- **Configuración en Render:**
  ```
  SECRET_KEY=tu-clave-secreta-de-32-caracteres-minimo
  ```

#### 4. **DATABASE_URL**
- **Descripción:** URL de conexión a PostgreSQL
- **Formato:** `postgresql://usuario:contraseña@host:puerto/nombre_db`
- **Ejemplo:** `postgresql://user:pass@host:5432/dbname`
- **Configuración en Render:** Se configura automáticamente si usas PostgreSQL de Render

---

## 🟡 RECOMENDADAS (Mejoran rendimiento y funcionalidad)

### Redis (Cache y Rate Limiting)

#### 5. **REDIS_URL** (Recomendado)
- **Descripción:** URL completa de conexión a Redis
- **Formato:** `redis://[:password@]host[:port][/db]`
- **Ejemplo:** `redis://:password@red-d46dg4ri:6379/0`
- **Configuración en Render:** Se configura automáticamente si usas Redis de Render
- **⚠️ Sin Redis:**
  - Se usará MemoryCache (no recomendado para múltiples workers)
  - Rate limiting será en memoria (no compartido entre workers)

#### Alternativa: Configuración por componentes
Si no tienes `REDIS_URL`, puedes usar:
- `REDIS_HOST`: Host de Redis (default: `localhost`)
- `REDIS_PORT`: Puerto (default: `6379`)
- `REDIS_DB`: Base de datos (default: `0`)
- `REDIS_PASSWORD`: Contraseña (opcional)

---

## 📦 Dependencias Opcionales

### Machine Learning

Las siguientes dependencias son **opcionales** pero recomendadas si usas funcionalidades de ML:

#### **scikit-learn**
- **Instalación:** Ya incluido en `requirements.txt`
- **Versión:** `>=1.3.0,<2.0.0`
- **Uso:** Modelos de predicción de riesgo crediticio
- **⚠️ Sin scikit-learn:** Funcionalidades de ML estarán limitadas

#### **xgboost**
- **Instalación:** Ya incluido en `requirements.txt`
- **Versión:** `>=2.0.0,<3.0.0`
- **Uso:** Modelos avanzados de ML
- **⚠️ Sin xgboost:** XGBoost no podrá ser usado

---

## 🔍 Verificación de Configuración

### En Render Dashboard

1. Ve a tu servicio en Render Dashboard
2. Navega a **Environment** → **Environment Variables**
3. Verifica que estén configuradas:
   - ✅ `ADMIN_EMAIL`
   - ✅ `ADMIN_PASSWORD`
   - ✅ `SECRET_KEY`
   - ✅ `DATABASE_URL`
   - ✅ `REDIS_URL` (recomendado)

### En los Logs

Después de desplegar, revisa los logs. Deberías ver:

#### ✅ Configuración Correcta:
```
✅ Logging estructurado JSON configurado para producción
✅ Usando Redis para rate limiting: redis://...
✅ Paquete redis instalado: versión X.X.X
✅ Database connection successful
```

#### ⚠️ Problemas Detectados:
```
🚨🚨🚨 CRÍTICO: ADMIN_EMAIL no está configurado...
🚨🚨🚨 CRÍTICO: ADMIN_PASSWORD no está configurado...
⚠️ Paquete redis de Python no está instalado...
⚠️ Redis no instalado - Usando MemoryCache...
⚠️ scikit-learn no está disponible...
⚠️ xgboost no está disponible...
```

---

## 🚀 Checklist de Despliegue

Antes de desplegar a producción, verifica:

- [ ] `ADMIN_EMAIL` configurado como variable de entorno
- [ ] `ADMIN_PASSWORD` configurado con contraseña segura (12+ caracteres)
- [ ] `SECRET_KEY` configurado con mínimo 32 caracteres
- [ ] `DATABASE_URL` configurado y accesible
- [ ] `REDIS_URL` configurado (recomendado para producción)
- [ ] `ENVIRONMENT=production` configurado
- [ ] `DEBUG=False` (verificado automáticamente en producción)
- [ ] Dependencias instaladas: `redis`, `scikit-learn`, `xgboost`

---

## 📝 Notas Importantes

1. **Valores por Defecto:** La aplicación usará valores por defecto si las variables críticas no están configuradas, pero mostrará advertencias críticas en los logs.

2. **Múltiples Workers:** Si usas múltiples workers (Gunicorn), Redis es **obligatorio** para:
   - Cache compartido entre workers
   - Rate limiting distribuido

3. **Seguridad:** Nunca uses valores por defecto en producción. Siempre configura variables de entorno.

4. **Machine Learning:** Las dependencias de ML son opcionales. La aplicación funcionará sin ellas, pero con funcionalidades limitadas.

---

## 🔗 Referencias

- [Documentación de Render - Environment Variables](https://render.com/docs/environment-variables)
- [Documentación de Redis](https://redis.io/docs/)
- [Documentación de scikit-learn](https://scikit-learn.org/)
- [Documentación de XGBoost](https://xgboost.readthedocs.io/)

