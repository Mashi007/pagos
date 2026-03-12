# Revisión: funciones comentadas y código que no se necesita

**Fecha:** 2025-03-12

---

## 1. Archivos que no se usan (duplicados / alternativas)

| Archivo | Motivo |
|---------|--------|
| `frontend/src/components/notificaciones/PlantillaAnexoPdf.updated.tsx` | Alternativa; solo se importa `PlantillaAnexoPdf.tsx` (desde `Plantillas.tsx`). |
| `frontend/src/components/notificaciones/PlantillaAnexoPdf.v2.tsx` | Igual. |
| `frontend/src/components/notificaciones/PlantillaAnexoPdf.NEW.tsx` | Igual. |

**Recomendación:** Eliminar los tres si no los usas como referencia. Si quieres conservar uno como respaldo, deja solo uno y borra los otros dos.

---

## 2. Código comentado en UI (menor)

| Ubicación | Qué está comentado |
|-----------|---------------------|
| `frontend/src/components/notificaciones/EditorPlantillaHTML.tsx` línea ~129 | Icono: `{/* <FileText className="h-5 w-5" /> */}` dentro del título "Información de la Plantilla". |

**Recomendación:** Quitar el comentario y dejar el icono, o borrar la línea si no quieres el icono.

---

## 3. Funciones / hooks que no se usan (frontend)

| Ubicación | Función / hook | Comentario |
|-----------|----------------|------------|
| `frontend/src/services/clienteService.ts` | `asignarAsesor(clienteId, analistaId)` | Marcada como "FUNCIÓN OBSOLETA - eliminado"; hace `throw new Error('La asignación...')`. Solo la usa el hook `useAsignarAsesor`. |
| `frontend/src/services/clienteService.ts` | `exportarClientes(filters, format)` | Hace `throw new Error('Exportación de clientes no disponible')`. Solo la usa el hook `useExportClientes`. |
| `frontend/src/hooks/useClientes.ts` | `useAsignarAsesor()` | No importado en ningún componente → código muerto. |
| `frontend/src/hooks/useClientes.ts` | `useExportClientes()` | No importado en ningún componente → código muerto. |
| `frontend/src/services/clienteService.ts` | `getClientesValoresPorDefecto(page, perPage)` | Delegación a `getCasosARevisar`. No referenciado en el frontend. |
| `frontend/src/services/clienteService.ts` | `exportarValoresPorDefecto(formato)` | No referenciado en el frontend. |

**Recomendación:**  
- Si la asignación de asesor y la exportación de clientes ya no existen en la app: eliminar `asignarAsesor`, `exportarClientes`, `useAsignarAsesor` y `useExportClientes`.  
- Si en el futuro se implementan, se puede volver a añadir.  
- `getClientesValoresPorDefecto` y `exportarValoresPorDefecto`: eliminar si no hay pantalla que los use; si hay o habrá “casos a revisar” y export CSV, se puede dejar solo lo que sí use la UI.

---

## 4. Backend: archivos de patch / documentación (no importados)

Estos archivos **no se importan** en `app/`; son scripts de parche o documentación de cambios ya aplicados:

- `backend/patch_*.py` (varios: patch_adjunto, patch_email_*, patch_call_sites, etc.)
- `backend/apply_*.py` (apply_modo_pruebas_plantillas, apply_email_patch, etc.)
- `backend/app/api/v1/endpoints/notificaciones_modo_pruebas_patch.py` — Contiene instrucciones y código comentado; la lógica real de `modo_pruebas` está en `notificaciones.py` y `notificaciones_tabs.py`.

**Recomendación:** Moverlos a una carpeta `backend/patches/` o `docs/patches/` y documentar que son históricos, o borrarlos si ya no los necesitas. No afectan la ejecución de la app.

---

## 5. Resumen de acciones sugeridas

| Prioridad | Acción |
|-----------|--------|
| Alta | Eliminar `PlantillaAnexoPdf.updated.tsx`, `PlantillaAnexoPdf.v2.tsx`, `PlantillaAnexoPdf.NEW.tsx` si no los usas. |
| Media | En `EditorPlantillaHTML.tsx`: descomentar el icono `FileText` o eliminar la línea comentada. |
| Media | Eliminar `useAsignarAsesor`, `useExportClientes` y las funciones `asignarAsesor` y `exportarClientes` del servicio de clientes si esas features no existen en la UI. |
| Baja | Revisar si algo usa `getClientesValoresPorDefecto` / `exportarValoresPorDefecto`; si no, eliminarlos. |
| Baja | Organizar o eliminar scripts `patch_*.py` y `apply_*.py` y el archivo `notificaciones_modo_pruebas_patch.py`. |

Si quieres, en el siguiente paso puedo aplicar las eliminaciones y el ajuste del icono en el código.
