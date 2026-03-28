# Paso 0 — Decisiones de alcance (auditoría de cartera)

Este documento **formaliza el Paso 0**: alineación de negocio y políticas **antes** de ampliar reglas o datos nuevos. No sustituye la firma de negocio/contabilidad cuando aplique.

**Fecha de registro:** 2026-03-27  
**Estado:** asunciones operativas para desarrollo (el responsable puede cambiar cualquier ítem respondiendo SÍ/NO en una nueva versión).

## 1. Prioridad

| # | Afirmación | Decisión (SÍ / NO) |
|---|------------|-------------------|
| 1 | La primera mejora técnica prioriza **escala** (paginación, filtros en servidor, export, rendimiento). | **SÍ** (asumido) |
| 2 | La primera mejora prioriza **moneda/tasa** en el control pagos vs aplicado. | **NO** (pospuesto; requiere acuerdo con reportes) |
| 3 | La primera mejora prioriza **bitácora de revisión** persistida en BD. | **NO** (pospuesto) |

## 2. Política de escritura en BD (comportamiento actual)

| # | Afirmación | Decisión |
|---|------------|----------|
| 4 | Mantener el job **03:00** que sincroniza `cuotas.estado` y persiste meta en `configuracion`. | **SÍ** |
| 5 | Mantener **Ejecutar auditoría** (POST ejecutar: sincroniza estados + meta). | **SÍ** |
| 6 | Mantener **Corregir** (admin) con opción de reaplicación en cascada pagos↔cuotas. | **SÍ** |

## 3. Alcance de la ronda vinculada a este Paso 0

| # | Afirmación | Decisión |
|---|------------|----------|
| 7 | Esta ronda incluye documentación / textos / contrato API aclarado **sin** nuevas tablas ni reglas monetarias nuevas. | **SÍ** |
| 8 | Esta ronda incluye tabla/API de **bitácora de revisión** en BD. | **SÍ** (implementado: paso 4) |
| 9 | Esta ronda incluye **cambios de reglas monetarias** del desajuste pagos vs aplicado. | **NO** (pendiente) |
| 10 | Esta ronda incluye **nuevas reglas de detección** en cartera (además de las 11 actuales). | **NO** (pendiente) |

## 4. Implementación derivada (checklist técnico)

- [x] Registro de este documento (`docs/auditoria-paso0-decisiones.md`).
- [x] Paso 1: textos de catálogo; descripciones OpenAPI (`Field`, queries); doc humana `docs/auditoria-api-cartera.md`; docstring del router de auditoría.
- [x] Paso 2: `GET .../chequeos` paginado y filtros; export CSV; menos `console.log` en pestaña Registro del sistema (`Auditoria.tsx`).
- [x] Paso 3: `GET .../cartera/resumen` sin items; `reglas_version` y `conteos_por_control` en `resumen` y en meta persistida (job 03:00, POST ejecutar/corregir); UI **Solo KPIs** y version en barra de estadísticas.
- [x] Paso 4: tabla `auditoria_cartera_revision`, POST/GET revisiones, UI OK + historial + sync ocultos.

## 5. Re-análisis

Cuando cambien prioridades o se aprueben los ítems **NO**, actualizar este archivo y reordenar el backlog (bitácora, moneda, nuevas reglas).

## 6. Decisión 3.5 — Conciliación del control «pagos vs aplicado»

Para el control **`total_pagado_vs_aplicado_cuotas`** (comparación de totales en el sistema), la **reconciliación línea a línea** con la realidad externa se hace mediante **conciliación bancaria**: movimientos y extractos bancarios frente a los pagos registrados y su aplicación a cuotas en la aplicación.
