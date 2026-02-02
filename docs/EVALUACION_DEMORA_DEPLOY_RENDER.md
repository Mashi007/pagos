# Evaluación: por qué demora cargar/desplegar desde GitHub a Render (front y back)

## Resumen

Tanto el **frontend** como el **backend** tienen builds pesados: muchas dependencias, instalación desde cero en cada deploy y pasos de build costosos. Aquí se detallan causas y opciones para reducir tiempo.

---

## 1. Frontend (Node / Vite)

### Qué hace Render en cada deploy

1. **Clone del repo** desde GitHub (rápido si el repo no es enorme).
2. **Build command:** `npm install && npm run build`
3. **Start:** `node server.js` (o `npm run render-start`)

### Causas de demora

| Causa | Impacto |
|-------|--------|
| **`npm install`** | ~541 paquetes (deps + devDependencies). Sin cache efectivo puede ser 1–3 min. |
| **Dependencias pesadas** | `exceljs` (~940 KB minificado), `jspdf`, `jspdf-autotable`, `html2canvas`, `recharts` → descarga y procesamiento en build. |
| **`npm run build`** = `tsc --noEmit --skipLibCheck` + `vite build` + `verify-build.js` | TypeScript recorre todo el proyecto; Vite empaqueta muchos chunks; total típico 1–3 min. |
| **DevDependencies en build** | TypeScript, Vite, ESLint, Vitest, etc. se instalan aunque no se usen en runtime; aumentan tiempo de `npm install`. |
| **Cache de Render** | Si el cache se invalida (cambio de branch, limpieza, etc.), `node_modules` se reinstala por completo. |

### Tiempo aproximado (referencia)

- `npm install`: 1–3 min (según región y cache).
- `tsc --noEmit`: 15–45 s.
- `vite build`: 1–2 min.
- **Total build frontend:** en torno a **3–6 minutos** en un entorno típico de Render.

---

## 2. Backend (Python / FastAPI)

### Qué hace Render en cada deploy

1. **Clone del repo.**
2. **Build command:** `pip install -r ../requirements.txt` (ejecutado con `rootDir: backend`).
3. **Start:** `gunicorn` con uvicorn workers.

### Causas de demora

| Causa | Impacto |
|-------|--------|
| **Paquetes científicos/ML** | `pandas`, `numpy`, `scikit-learn`, `xgboost` son pesados; descarga e instalación (o compilación) puede ser 2–5 min. |
| **Google Cloud** | `google-api-python-client`, `google-auth`, `google-cloud-vision` suman dependencias y tiempo. |
| **Otros pesados** | `reportlab`, `cryptography`, `openpyxl` también contribuyen. |
| **Sin wheels precompilados** | En algunas versiones de Python/plataforma, pip puede compilar desde fuente → más tiempo. |
| **Cache pip** | Render suele cachear; si se pierde el cache, la instalación es mucho más lenta. |

### Tiempo aproximado (referencia)

- `pip install -r requirements.txt`: **3–8 minutos** (dependiendo de cache y de si hay compilación).
- **Total build backend:** en torno a **3–8 minutos**.

---

## 3. Recomendaciones para reducir tiempo

### Frontend

1. **Usar `npm ci` en lugar de `npm install`**  
   - Más rápido y determinista.  
   - Requiere tener `package-lock.json` commitado y no alterado a mano.  
   - En `render.yaml` / Build command:  
     `npm ci && npm run build`

2. **Mantener cache de Render**  
   - No desactivar cache de build en el dashboard salvo que sea necesario.  
   - Evitar cambios que invaliden cache (p. ej. borrar `node_modules` en el repo).

3. **Opcional: aligerar el script de build**  
   - Si en CI ya haces type-check aparte, se puede probar en Render solo `vite build` (quitar `tsc --noEmit` del script `build`) para ahorrar 15–45 s.  
   - Implica asumir que los tipos se validan en otro paso.

4. **No instalar devDependencies innecesarias para el build**  
   - Para el build en Render solo hacen falta, en la práctica, las herramientas de build (p. ej. `vite`, `typescript`).  
   - Herramientas como `@axe-core/cli`, `vitest`, `jsdom` no se usan en el build; quitarlas de `devDependencies` (si no las usas en otro lado) reduce un poco el tiempo de `npm install`.  
   - Es un cambio menor y opcional.

### Backend

1. **Mantener cache de pip**  
   - No desactivar cache de build en el servicio de Render si no hace falta.

2. **Revisar si todo lo de `requirements.txt` es imprescindible en este servicio**  
   - Por ejemplo: si `xgboost` / `scikit-learn` solo se usan en un job o en otro servicio, moverlos a otro `requirements-*.txt` o imagen y no instalarlos en el web service reduce mucho el tiempo.

3. **Fijar versiones y preferir wheels**  
   - Ya usas versiones fijadas; en entornos donde pip pueda elegir wheels (Linux x86_64 en Render), la instalación suele ser más rápida que compilar.

4. **Build en dos etapas (avanzado)**  
   - Una imagen o etapa que instale dependencias y otra que solo copie código y arranque la app (estilo Docker multi-stage). Render permite Dockerfile; es la opción más potente pero implica más configuración.

---

## 4. Cambios concretos sugeridos en el repo

### `render.yaml` (raíz) – Frontend

```yaml
buildCommand: npm ci && npm run build
```

(Requisito: `package-lock.json` actualizado y commitado.)

### `frontend/render.yaml` (si se usa)

```yaml
buildCommand: npm ci && npm run build
```

### Backend

- Dejar el `buildCommand` actual; el mayor ahorro viene de cache y de no instalar paquetes que no uses en este servicio.
- Opcional: crear `requirements-base.txt` (sin pandas/sklearn/xgboost) y `requirements-ml.txt` y en Render instalar solo el que corresponda al servicio que se despliega.

---

## 5. Qué esperar

- **Frontend:** con `npm ci` y cache estable, se puede ahorrar algo de tiempo en `npm install`; el resto del tiempo seguirá dominado por `tsc` + `vite build`.
- **Backend:** la mayor ganancia es no instalar ML/científicas en el web service si no se usan ahí, y confiar en el cache de pip.
- **Ambos:** el clone desde GitHub suele ser rápido; la demora principal está en **install** y **build**, no en “cargar archivos” en sí.

Si compartes el `render.yaml` actual (o el build command exacto de cada servicio en el dashboard), se puede ajustar la recomendación a tu caso concreto (por ejemplo, si usas dos servicios separados para front y back).
