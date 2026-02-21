# Auditoría: Reportes - Icono de carga no avanza

**Fecha:** 2026-02-21  
**URL afectada:** https://rapicredit.onrender.com/pagos/reportes  
**Problema:** Al hacer clic en el icono de actualizar (RefreshCw), el icono no muestra animación de carga y la experiencia parece no responder.

---

## Hallazgos de la auditoría

### 1. **Falta el Toaster de Sonner** (crítico)

- **Problema:** La página Reportes y ~50 componentes usan `toast` de **sonner**, pero en `main.tsx` solo estaba montado el Toaster de **react-hot-toast**.
- **Impacto:** Los toasts de sonner (`toast.info`, `toast.loading`, `toast.success`, `toast.error`) no se renderizaban. El usuario no veía feedback al hacer clic en "Actualizar KPIs".
- **Causa probable del refactor:** Migración parcial de react-hot-toast a sonner sin añadir el Toaster de sonner.

### 2. **Flujo del botón "Actualizar KPIs"**

- **Problema:** El `onClick` llamaba a `refetchResumen()` sin `await` y mostraba `toast.info('Actualizando datos...')` de forma inmediata. Si el toast no se mostraba (por falta de Toaster), no había feedback visual.
- **Problema adicional:** El estado `isFetching` de React Query puede tardar un tick en actualizarse. En algunos casos el spinner no llegaba a mostrarse antes de que el refetch terminara (p. ej. cold start rápido o caché).
- **Solución:** Estado local `isRefreshingManual` que se activa al hacer clic y se desactiva al terminar el refetch, garantizando que el icono muestre la animación de carga.

### 3. **Botón "Reintentar" en zona de error**

- Mismo patrón: no había estado local para el spinner, solo dependencia de `fetchingResumen`.
- **Solución:** Uso de `isRefreshingManual` para mostrar Loader2 de forma consistente.

---

## Correcciones aplicadas

### 1. `main.tsx` – Toaster de Sonner

```tsx
import { Toaster as SonnerToaster } from 'sonner'
// ...
<SonnerToaster position="bottom-right" richColors closeButton />
```

### 2. `Reportes.tsx` – Botón "Actualizar KPIs"

- Estado local `isRefreshingManual`.
- `onClick` async que:
  - Activa `isRefreshingManual` al inicio.
  - Hace `await refetchResumen()`.
  - Muestra `toast.success` o `toast.error` según el resultado.
  - Desactiva `isRefreshingManual` en `finally`.
- El icono usa `animate-spin` cuando `loadingResumen || fetchingResumen || isRefreshingManual`.

### 3. `Reportes.tsx` – Botón "Reintentar"

- Mismo patrón con `isRefreshingManual` para el spinner.

---

## Verificación

- Build del frontend: OK.
- Toasts de sonner visibles en toda la app.
- Icono de actualizar muestra animación de carga al hacer clic.
- Feedback claro de éxito o error tras el refetch.

---

## Recomendaciones futuras

1. **Unificar sistema de toasts:** Elegir sonner o react-hot-toast y migrar todo a uno solo para evitar duplicidad.
2. **Tests E2E:** Añadir pruebas para el flujo de actualización de KPIs en Reportes.
3. **Manejo de cold start:** El endpoint `/api/v1/reportes/dashboard/resumen` tiene timeout de 120 s; considerar un mensaje específico si tarda más de X segundos.
