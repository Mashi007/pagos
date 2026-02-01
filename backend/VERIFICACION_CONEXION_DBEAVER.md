# Verificación de conexión a la base de datos (DBeaver / PostgreSQL)

Cuando DBeaver muestra **EOFException** ("El intento de conexión falló"), la conexión se corta antes de completar el handshake. Sigue esta guía para alinear la configuración con el proyecto y descartar causas habituales.

---

## 1. Parámetros que debe usar DBeaver

El proyecto usa **PostgreSQL** y la URL se define en `backend/.env` como `DATABASE_URL`. En DBeaver la conexión debe coincidir **exactamente** con esos valores.

### Base de datos en Render (producción) — **pagos_db_zjer**

Esta es la base del proyecto: **pagos_db_zjer** en Render (PostgreSQL 17). Para conectar desde tu equipo (DBeaver o backend en local) usa la **External Database URL** de Render.

| Parámetro   | Valor |
|------------|--------|
| **Host**   | `dpg-d3l8tkur433s7380oph0-a.oregon-postgres.render.com` (External) |
| **Port**   | `5432` |
| **Database** | `pagos_db_zjer` |
| **Username** | `pagos_admin` |
| **Password** | La que aparece en Render → Info de la BD → "Password" (o en External Database URL). |

En `backend/.env` debes usar la **External Database URL** que muestra Render (formato `postgresql://pagos_admin:...@dpg-d3l8tkur...oregon-postgres.render.com:5432/pagos_db_zjer`). El backend ya acepta tanto `postgres://` como `postgresql://`.

### Conexión local (ejemplo)

| Parámetro   | Valor típico (local) | Comentario |
|------------|----------------------|------------|
| **Host**   | `localhost` o `127.0.0.1` | Mismo que en `DATABASE_URL` |
| **Port**   | `5432` | Puerto por defecto de PostgreSQL |
| **Database** | Nombre de la BD (ej. `pagos_db`) | El que aparece después del último `/` en `DATABASE_URL` |
| **Username** | Usuario de PostgreSQL | El que está en `DATABASE_URL` antes de `:` en la parte de credenciales |
| **Password** | Contraseña del usuario | La que configuraste en PostgreSQL |

**Ejemplo de DATABASE_URL local (en .env):**
```text
DATABASE_URL=postgresql://usuario:password@localhost:5432/pagos_db
```
En DBeaver: Host `localhost`, Port `5432`, Database `pagos_db`, Username `usuario`, Password `password`.

---

## 2. Comprobar que PostgreSQL está en ejecución (Windows)

- Abre **Servicios** (`services.msc`) y busca **postgresql-x64-XX** (o similar). Debe estar **En ejecución**.
- O en PowerShell (como administrador):
  ```powershell
  Get-Service -Name "postgresql*"
  ```
  El estado debe ser `Running`.

Si no está instalado o no arranca, instala/arranca PostgreSQL antes de usar DBeaver.

---

## 3. Probar la conexión desde el backend (misma DATABASE_URL)

El backend expone un health check de base de datos. Si este responde bien, el fallo es de configuración en DBeaver.

1. En `backend` asegúrate de tener un `.env` con `DATABASE_URL` correcto (el mismo que quieres usar en DBeaver).
2. Arranca el backend (por ejemplo):
   ```bash
   cd backend
   uvicorn app.main:app --reload
   ```
3. Abre en el navegador o con curl:
   ```text
   http://localhost:8000/health/db
   ```
   - Si responde **200** con `"database": "connected"` → La BD y `DATABASE_URL` están bien; revisa solo DBeaver (host, puerto, SSL, etc.).
   - Si responde **503** o error → El problema es PostgreSQL o la URL (host, puerto, usuario, contraseña, nombre de BD). Corrige eso primero y luego DBeaver.

---

## 4. Ajustes en DBeaver que suelen resolver EOFException

### 4.1 SSL

- **BD en Render (cloud):** Render suele requerir SSL. En DBeaver: Edit Connection → pestaña **SSL** → usar **require** o **verify-full** según lo que indique Render.
- **BD local:** En muchas instalaciones locales **no** se usa SSL. En DBeaver: Edit Connection → pestaña **SSL** → **SSL = disable** (o "allow").

Guarda y prueba de nuevo.

### 4.2 Host y puerto

- **Host:** Exactamente el mismo que en `DATABASE_URL`. Para Render (conexión externa): `dpg-d3l8tkur433s7380oph0-a.oregon-postgres.render.com`. Para local: `localhost` o `127.0.0.1`.
- **Port:** `5432` (Render y PostgreSQL por defecto).

### 4.3 Firewall / antivirus

- A veces el firewall o el antivirus cierran la conexión y se ve como EOFException. Prueba temporalmente desactivar firewall/antivirus solo para probar, o añadir una excepción para `postgres.exe` y para el puerto 5432.

### 4.4 Driver PostgreSQL en DBeaver

- **Help → Check for Updates** (o **DBeaver → Check for Updates**) y actualiza DBeaver / drivers.
- En la conexión, pestaña **Driver settings**: asegúrate de usar el driver **PostgreSQL** y, si hay opción, la versión más reciente del driver.

---

## 5. Resumen rápido

1. **Misma configuración que el proyecto:** Host, puerto, base de datos, usuario y contraseña en DBeaver = los de `DATABASE_URL` en `backend/.env`.
2. **PostgreSQL en ejecución** en tu equipo (o en el servidor que uses en `DATABASE_URL`).
3. **Probar** `GET http://localhost:8000/health/db` con el backend arrancado; si responde "connected", el fallo es solo en DBeaver.
4. En DBeaver: **SSL desactivado** para BD local, **host/puerto correctos**, y si sigue fallando, revisar **firewall/antivirus** y **actualizar DBeaver/driver**.

Si tras esto sigue apareciendo EOFException, abre **Detalles** en el cuadro de error de DBeaver y revisa el mensaje completo (a veces incluye "Connection refused" o "timeout") para afinar el siguiente paso.
