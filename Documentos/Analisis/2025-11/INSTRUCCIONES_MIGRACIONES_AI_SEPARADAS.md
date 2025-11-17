# 📋 Instrucciones: Migraciones AI Training Separadas

**Fecha:** 2025-11-14
**Estado:** ✅ Migraciones creadas (Opción 1 implementada)

---

## ✅ Migraciones Creadas

Se han creado **4 migraciones separadas** según la Opción 1:

1. ✅ `20251114_01_create_conversaciones_ai.py`
2. ✅ `20251114_02_create_fine_tuning_jobs.py`
3. ✅ `20251114_03_create_documento_ai_embeddings.py`
4. ✅ `20251114_04_create_modelos_riesgo.py`

---

## 🔄 Orden de Dependencias

Las migraciones están configuradas en el siguiente orden:

```
20251114_create_documentos_ai (ya existe)
    ↓
20251114_01_create_conversaciones_ai
    ↓
20251114_02_create_fine_tuning_jobs
    ↓
20251114_03_create_documento_ai_embeddings (depende de documentos_ai)
    ↓
20251114_04_create_modelos_riesgo
```

---

## ⚠️ Migración Original

**Archivo:** `20250114_create_ai_training_tables.py`

### Opciones para la migración original:

#### **OPCIÓN A: Si la migración NO se ha aplicado** (Recomendado)

1. **Renombrar la migración original** para evitar conflictos:
   ```bash
   cd backend/alembic/versions
   mv 20250114_create_ai_training_tables.py 20250114_create_ai_training_tables.py.old
   ```

2. **Verificar orden de migraciones:**
   ```bash
   cd backend
   alembic history
   ```

3. **Aplicar las nuevas migraciones:**
   ```bash
   alembic upgrade head
   ```

#### **OPCIÓN B: Si la migración YA se aplicó**

1. **Mantener ambas migraciones** (la original y las nuevas)
   - Las nuevas migraciones tienen verificación `_table_exists()`
   - No crearán tablas duplicadas si ya existen

2. **O eliminar la migración original** si prefieres mantener solo las nuevas:
   ```bash
   cd backend/alembic/versions
   mv 20250114_create_ai_training_tables.py 20250114_create_ai_training_tables.py.backup
   ```

---

## 🔍 Verificación

### Paso 1: Verificar estado actual
```bash
cd backend
alembic current
alembic history
```

### Paso 2: Verificar si las tablas existen
```bash
# Usar el script de verificación
python scripts/verificar_migracion_ai_training.py
```

### Paso 3: Aplicar migraciones (si no se aplicaron)
```bash
alembic upgrade head
```

---

## 📊 Ventajas de las Migraciones Separadas

✅ **Mantenibilidad:** Cada migración es pequeña y enfocada (~50-70 líneas)
✅ **Rollback Selectivo:** Puedes hacer rollback de una tabla específica
✅ **Revisión Fácil:** Más fácil de revisar y aprobar en PRs
✅ **Idempotentes:** Todas tienen verificación `_table_exists()`
✅ **Orden Claro:** Dependencias explícitas en `down_revision`

---

## 🚨 Consideraciones Importantes

1. **No eliminar la migración original** hasta verificar que las nuevas funcionan
2. **Probar en desarrollo** antes de aplicar en producción
3. **Hacer backup** de la base de datos antes de aplicar migraciones
4. **Verificar orden** con `alembic history` antes de aplicar

---

## 📝 Checklist

- [x] Crear migración 1: conversaciones_ai
- [x] Crear migración 2: fine_tuning_jobs
- [x] Crear migración 3: documento_ai_embeddings
- [x] Crear migración 4: modelos_riesgo
- [ ] Verificar orden con `alembic history`
- [ ] Decidir qué hacer con migración original
- [ ] Probar en desarrollo
- [ ] Aplicar en producción

---

## 🔗 Archivos Relacionados

- `Documentos/Analisis/2025-11/ANALISIS_MIGRACION_AI_TRAINING.md` - Análisis completo
- `backend/scripts/verificar_migracion_ai_training.py` - Script de verificación

