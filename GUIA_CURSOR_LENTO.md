# Por qué Cursor puede ir lento y qué hacer

## Causas habituales en este proyecto

### 1. **Muchos archivos que Cursor indexa**
- Hay **60+ archivos .md** (auditorías, guías, reportes) en la raíz y en `frontend/`/`backend/` que Cursor indexa por defecto.
- **Solución**: Añadir al final de **`.cursorignore`** las siguientes líneas para que Cursor no los analice:

```gitignore
# Documentos de auditoría/reporte (reducen índice y lentitud)
/ANALISIS_*.md
/AUDITORIA_*.md
/CAUSAS_*.md
/COMANDOS_*.md
/COMPARACION_*.md
/CONFIRMACION_*.md
/ERROR_*.md
/GUIA_*.md
/RESUMEN_*.md
/RESULTADO_*.md
/REVISION_*.md
/SOLUCION_*.md
/VERIFICACION_*.md
/VERSION_*.md
/REPORTE_*.txt
/diagnostico_cursor.ps1
/limpiar_cache_cursor.ps1
/verificar_calidad_conexion_cursor.ps1
/solucionar_error_serialize_binary.ps1
```

### 2. **Reglas que se ejecutan en cada cambio**
- Si tienes **kluster_code_review_auto** (o similar) configurado para ejecutarse **después de cualquier cambio**, cada guardado puede disparar una verificación externa y notar lentitud.
- **Solución**: Revisar en **Cursor Settings → Rules** (o `.cursor/rules/`) y, si quieres más fluidez, limitar la revisión automática a "solo en commit" o desactivarla y lanzarla manualmente cuando haga falta.

### 3. **Caché de Cursor**
- Caché dañado o muy grande (Cache, Code Cache, CachedData, GPUCache, ShaderCache) puede hacer que Cursor vaya lento.
- **Solución**: Cerrar Cursor y ejecutar el script que ya tienes en el repo:

```powershell
.\diagnostico_cursor.ps1
```

O limpiar manualmente las carpetas de caché en:
- `%APPDATA%\Cursor\Cache`
- `%APPDATA%\Cursor\Code Cache`
- `%APPDATA%\Cursor\CachedData`
- `%APPDATA%\Cursor\GPUCache`
- `%APPDATA%\Cursor\ShaderCache`

### 4. **Archivos muy grandes**
- Componentes de **más de ~1000 líneas** (por ejemplo `EvaluacionRiesgoForm.tsx`) hacen que el índice y el análisis sean más pesados.
- **Solución**: A largo plazo, dividir en componentes más pequeños; a corto plazo, el `.cursorignore` anterior ya reduce el trabajo al excluir docs/reportes.

### 5. **Conexión / red**
- Si las reglas hacen llamadas a servicios externos (p. ej. kluster), una red inestable o lenta se nota en cada ejecución.
- **Solución**: Comprobar conexión; si usas VPN, probar sin ella; reducir la frecuencia de las reglas que usan red.

### 6. **Antivirus o Windows Defender**
- El escaneo en tiempo real de carpetas como `node_modules/` o `frontend/dist/` puede ralentizar el IDE.
- **Solución**: Excluir la carpeta del proyecto (o al menos `node_modules/`, `frontend/dist/`, `.venv/`) del escaneo en tiempo real. `.cursorignore` ya evita que Cursor indexe `node_modules/`, pero el antivirus sigue leyendo el disco.

---

## Resumen rápido

| Acción | Impacto |
|--------|--------|
| Añadir las líneas anteriores a `.cursorignore` | Alto – menos archivos indexados |
| Limpiar caché con `diagnostico_cursor.ps1` | Medio – Cursor arranca más ligero |
| Suavizar o desactivar revisión automática en cada guardado | Medio – menos trabajo por cambio |
| Excluir carpeta del proyecto del antivirus en tiempo real | Variable – depende del equipo |

Empieza por **1** y **2**; si sigue lento, revisa **3** y **4**.
