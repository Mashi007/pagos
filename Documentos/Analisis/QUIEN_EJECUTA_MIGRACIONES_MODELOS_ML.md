# ¿Quién Ejecuta las Migraciones de Modelos ML?

## 📋 Resumen

Las migraciones que crean las tablas `modelos_riesgo` y `modelos_impago_cuotas` se ejecutan de **3 formas diferentes**:

## 🔄 Formas de Ejecución

### 1. **Automáticamente al Iniciar la Aplicación** ⚡ (PRINCIPAL)

**Ubicación:** `backend/app/main.py`

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestión del ciclo de vida"""
    init_db_startup()  # ← Aquí se ejecutan las migraciones
    # ...
```

**Flujo:**
1. FastAPI inicia la aplicación
2. Se ejecuta `lifespan()` (evento de startup)
3. Llama a `init_db_startup()` en `app/db/init_db.py`
4. `init_db_startup()` llama a `run_migrations()`
5. `run_migrations()` ejecuta `alembic upgrade head`

**Código relevante:**
```python
# backend/app/db/init_db.py
def init_db_startup() -> None:
    """Initialize database on startup."""
    # ...
    # Ejecutar migraciones de Alembic automáticamente
    run_migrations()  # ← Ejecuta alembic upgrade head
```

**Cuándo se ejecuta:**
- ✅ Cada vez que se inicia el servidor FastAPI
- ✅ En desarrollo: cuando ejecutas `uvicorn app.main:app`
- ✅ En producción: cuando Render/Railway inicia el servidor

---

### 2. **En el Procfile (Producción)** 🚀

**Ubicación:** `backend/Procfile`

```
web: alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

**Flujo:**
1. Render/Railway lee el `Procfile`
2. Ejecuta `alembic upgrade head` **ANTES** de iniciar el servidor
3. Luego inicia `uvicorn`

**Cuándo se ejecuta:**
- ✅ En cada deploy a producción (Render/Railway)
- ✅ Antes de iniciar el servidor web
- ✅ Garantiza que las migraciones estén aplicadas antes de servir requests

**Ventaja:**
- Si las migraciones fallan, el servidor no inicia
- Evita que la aplicación funcione con esquema desactualizado

---

### 3. **Manualmente por el Desarrollador** 👨‍💻

**Comando:**
```bash
cd backend
alembic upgrade head
```

**Cuándo se ejecuta:**
- ✅ Cuando el desarrollador quiere aplicar migraciones sin reiniciar el servidor
- ✅ Para verificar que las migraciones funcionan correctamente
- ✅ Para aplicar migraciones en desarrollo antes de hacer deploy

**Scripts disponibles:**
- `backend/scripts/ejecutar_migraciones_ai_training.py`
- `scripts/powershell/ejecutar_migraciones_alembic.ps1`

---

## 📊 Orden de Ejecución en Producción

```
1. Render/Railway inicia el contenedor
   ↓
2. Lee Procfile: "alembic upgrade head && uvicorn..."
   ↓
3. Ejecuta: alembic upgrade head
   ├─ Aplica migraciones pendientes
   ├─ Crea tablas si no existen
   └─ Actualiza esquema de BD
   ↓
4. Ejecuta: uvicorn app.main:app
   ↓
5. FastAPI lifespan() → init_db_startup()
   ↓
6. run_migrations() (verifica si hay migraciones pendientes)
   └─ Si ya están aplicadas, no hace nada
```

**Nota:** En producción, las migraciones se ejecutan **dos veces**:
- Primero en el `Procfile` (garantiza que estén aplicadas)
- Luego en `lifespan()` (verificación redundante, pero segura)

---

## 🔍 Migraciones Específicas de Modelos ML

### `20251114_04_create_modelos_riesgo.py`
- **Crea:** Tabla `modelos_riesgo`
- **Ejecutada por:** Cualquiera de los 3 métodos arriba
- **Revisión:** `20251114_04_modelos_riesgo`
- **Depende de:** `20251114_03_documento_ai_embeddings`

### `20251114_05_create_modelos_impago_cuotas.py`
- **Crea:** Tabla `modelos_impago_cuotas`
- **Ejecutada por:** Cualquiera de los 3 métodos arriba
- **Revisión:** `20251114_05_modelos_impago_cuotas`
- **Depende de:** `20251114_04_modelos_riesgo`

---

## ⚠️ Problemas Comunes

### Problema 1: Tabla no existe después de iniciar servidor

**Causa:** Las migraciones fallaron silenciosamente

**Solución:**
```bash
# Verificar estado
cd backend
alembic current

# Ejecutar manualmente
alembic upgrade head
```

### Problema 2: Múltiples heads

**Causa:** Hay múltiples ramas de migraciones

**Solución:** `run_migrations()` maneja esto automáticamente:
```python
if len(heads) > 1:
    # Actualiza todos los heads individualmente
    for head in heads:
        command.upgrade(alembic_cfg, head.revision)
```

### Problema 3: Migraciones no se ejecutan en producción

**Causa:** El `Procfile` no está configurado correctamente

**Solución:** Verificar que el `Procfile` tenga:
```
web: alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

---

## 📝 Resumen Ejecutivo

| Método | Cuándo | Dónde | Automático |
|--------|--------|-------|------------|
| **lifespan()** | Al iniciar FastAPI | `app/main.py` | ✅ Sí |
| **Procfile** | Antes de iniciar servidor | `backend/Procfile` | ✅ Sí |
| **Manual** | Cuando el dev lo ejecuta | Terminal | ❌ No |

**Conclusión:** Las migraciones se ejecutan **automáticamente** al iniciar la aplicación, tanto en desarrollo como en producción. No necesitas ejecutarlas manualmente a menos que haya un problema.

