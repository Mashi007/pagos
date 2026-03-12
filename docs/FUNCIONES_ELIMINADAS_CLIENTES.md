# Funciones eliminadas (clientes) – Referencia para el commit

Se eliminaron **6 funciones/hooks** que no se usaban en la UI o que eran stubs obsoletos.

## Para qué eran

| Función / Hook | Propósito original | Motivo de eliminación |
|----------------|--------------------|------------------------|
| **asignarAsesor** (clienteService) | Asignar un analista/asesor a un cliente. | **Obsoleto:** la asignación de analistas a clientes fue eliminada; la función solo hacía `throw new Error(...)`. |
| **useAsignarAsesor** (useClientes) | Hook para llamar a `asignarAsesor` desde un componente (mutación + toast + invalidación de cache). | **Código muerto:** ningún componente importa este hook. |
| **exportarClientes** (clienteService) | Exportar listado de clientes a Excel o PDF (filtros opcionales). | **No implementado:** solo hacía `throw new Error('Exportación de clientes no disponible')`; no existía endpoint de exportación. |
| **useExportClientes** (useClientes) | Hook para llamar a `exportarClientes` desde la UI. | **Código muerto:** ningún componente importa este hook. |
| **getClientesValoresPorDefecto** (clienteService) | Devolver clientes con valores por defecto (placeholders); era un alias de `getCasosARevisar`. | **Redundante:** mismo resultado que `getCasosARevisar`; ningún código lo usaba. |
| **exportarValoresPorDefecto** (clienteService) | Exportar a CSV los “casos a revisar” (clientes con placeholders), generando el CSV en el frontend. | **Código muerto:** ningún componente lo llamaba. Si se necesita exportar casos a revisar, puede reimplementarse usando `getCasosARevisar`. |

## Archivos modificados

- `frontend/src/services/clienteService.ts`: eliminadas las 4 funciones del servicio.
- `frontend/src/hooks/useClientes.ts`: eliminados los 2 hooks.

La funcionalidad activa de “casos a revisar” sigue en **getCasosARevisar** y **getClientesConProblemasValidacion** (este último sí se usa en CorregirClientes).
