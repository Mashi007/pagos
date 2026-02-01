# Qué puede hacer lento a Cursor en el proyecto pagos

---

## 1. Archivos muy grandes (>1500 líneas)

Cursor indexa y analiza todo el código. **8 archivos** tienen más de 1500 líneas y pesan mucho en el índice:

- `frontend/src/components/configuracion/FineTuningTab.tsx` (2035)
- `frontend/src/components/configuracion/AIConfig.tsx` (1723)
- `frontend/src/components/clientes/ExcelUploader.tsx` (1768)
- `frontend/src/components/prestamos/EvaluacionRiesgoForm.tsx` (1758)
- `frontend/src/pages/Configuracion.tsx` (1615)
- `frontend/src/components/clientes/CrearClienteForm.tsx` (1612)
- `frontend/src/pages/DashboardMenu.tsx` (1520)
- `frontend/src/pages/Cobranzas.tsx` (1514)

**Qué hacer:** Añadir estas rutas al final de `.cursorignore` (están listadas en `ARCHIVOS_LENTOS_CURSOR.md`) o ir refactorizando y dividiendo en componentes más pequeños.

---

## 2. Reglas que se ejecutan en cada cambio

Si tienes **kluster_code_review_auto** (o similar) configurado para ejecutarse **después de cualquier cambio**, cada guardado puede disparar una verificación externa y notar lentitud.

**Qué hacer:** En Cursor → Settings → Rules (o `.cursor/rules/`), limitar la revisión automática a “solo en commit” o desactivarla y lanzarla manualmente cuando haga falta.

---

## 3. Caché de Cursor

Caché grande o dañado (Cache, Code Cache, CachedData, GPUCache, ShaderCache) puede hacer que Cursor arranque o responda más lento.

**Qué hacer:** Cerrar Cursor y borrar (o vaciar) estas carpetas en `%APPDATA%\Cursor\`:
- Cache  
- Code Cache  
- CachedData  
- GPUCache  
- ShaderCache  

Luego volver a abrir Cursor.

---

## 4. Cantidad de archivos que indexa

El proyecto tiene **~128 archivos .tsx**, **~57 .ts**, código Python en backend y varios .md. Todo eso se indexa. Ya tienes en `.cursorignore` `node_modules/`, `venv/`, `__pycache__/`, `dist/`, etc., que es lo correcto.

**Qué hacer:** Mantener `.cursorignore` actualizado. Si quieres aligerar más, añadir los 8 archivos grandes (punto 1).

---

## 5. Antivirus / Windows Defender

Si el antivirus escanea en tiempo real la carpeta del proyecto (sobre todo `node_modules/`, `frontend/dist/`, `.venv/`), el disco y el IDE pueden ir más lentos.

**Qué hacer:** Excluir la carpeta del proyecto pagos (o al menos `node_modules/`, `frontend/dist/`, `.venv/`) del escaneo en tiempo real en Windows Defender / tu antivirus.

---

## Resumen rápido

| Causa              | Impacto  | Acción rápida                                      |
|--------------------|----------|----------------------------------------------------|
| Archivos >1500 líneas | Alto     | Añadirlos a `.cursorignore` (ver ARCHIVOS_LENTOS_CURSOR.md) |
| Revisión automática en cada cambio | Medio    | Limitar a “solo en commit” o desactivar            |
| Caché de Cursor    | Medio    | Borrar carpetas de caché en %APPDATA%\Cursor\     |
| Muchos archivos    | Ya mitigado | node_modules, venv, dist ya en .cursorignore   |
| Antivirus          | Variable | Excluir carpeta del proyecto del escaneo en vivo   |

Empieza por **1** (archivos grandes en `.cursorignore`) y **3** (limpiar caché); si sigue lento, revisa **2** y **5**.
