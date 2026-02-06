# Verificación: Aprobación manual de riesgo (requisitos 1–6)

Comprobación de que los 6 requisitos del usuario están implementados y compatibilizados con las sugerencias.

---

## 1. Estado final: **APROBADO** (SI)

| Dónde | Implementado |
|-------|--------------|
| Backend | `prestamos.py` → `aprobar_manual`: `p.estado = "APROBADO"` |
| Doc | `PROCESO_APROBACION_RIESGO_MANUAL_SIMPLIFICADO.md`: estado resultante APROBADO |

**Conclusión:** OK. El préstamo queda en APROBADO (no DESEMBOLSADO).

---

## 2. Una sola fecha (aprobación = base amortización)

| Dónde | Implementado |
|-------|--------------|
| Backend | Un solo campo en body: `fecha_aprobacion`. Se asigna a `fecha_aprobacion` y a `fecha_base_calculo`. |
| Frontend | Un solo input tipo `date`: "Fecha de aprobación" (con nota: "Base para la tabla de amortización"). |

**Conclusión:** OK.

---

## 3. Texto de declaración **fijo**

| Dónde | Implementado |
|-------|--------------|
| Frontend | Constante `DECLARACION_FIJA` en `AprobarPrestamoManualModal.tsx`: "Al aprobar, usted asegura que el cliente cumple las políticas de RapiCredit y que su riesgo está dentro de parámetros normales." |

**Conclusión:** OK. No se lee de BD ni configuración.

---

## 4. Solo administración puede aprobar

| Dónde | Implementado |
|-------|--------------|
| Frontend | El botón "Aprobar préstamo" solo se muestra si `canViewEvaluacionRiesgo()` es true → `usePermissions`: `isAdmin()` → `user?.rol === 'administrador'`. |
| Backend | En `aprobar_manual` se valida `current_user.rol == "administrador"`; si no, se devuelve **403** con mensaje "Solo administración puede aprobar préstamos". |

**Nota:** En el sistema el rol se llama `"administrador"`. Si en tu BD o auth usas otro valor (ej. `"administracion"`), hay que alinear: mismo valor en backend/frontend o aceptar ambos en el backend.

**Conclusión:** OK (frontend + backend).

---

## 5. Datos del formulario nuevo crédito → formulario de aprobación; editables solo en este paso; confirmación “documentos analizados”

| Requisito | Implementado |
|-----------|--------------|
| Datos del nuevo crédito al formulario de aprobación | El préstamo se crea con `CrearPrestamoForm` (nuevo crédito). En la lista, al hacer clic en "Aprobar préstamo" se abre el modal con ese `prestamo` (mismo registro: `total_financiamiento`, `numero_cuotas`, `modalidad_pago`, etc.). |
| Editables en aprobación | En el modal se pueden editar: monto financiamiento, número de cuotas, modalidad de pago, cuota por periodo, tasa de interés, observaciones. El backend actualiza el préstamo con estos valores antes de generar cuotas. |
| Solo en este paso se pueden editar | Para DRAFT/EN_REVISION la lista no muestra "Editar" para esos campos; el único flujo que permite cambiar monto/cuotas/modalidad antes de aprobar es este modal. Tras aprobar, el préstamo pasa a APROBADO. |
| “Documentos analizados” (confirmación) | Checkbox: "Confirmo que se analizaron los documentos del cliente." Backend exige `documentos_analizados === true`. No se analizan documentos en el sistema; es una declaración del aprobador. |

**Conclusión:** OK. Opcional: si se quisiera poder editar también producto, concesionario, analista o modelo en este paso, habría que añadir esos campos al modal y al body del endpoint.

---

## 6. Auditoría en tabla de auditoría

| Dónde | Implementado |
|-------|--------------|
| Backend | Tras actualizar préstamo y generar cuotas, se inserta un registro en la tabla `auditoria`: `modulo="prestamos"`, `tabla="prestamos"`, `accion="APROBACION_MANUAL"`, `registro_id=prestamo_id`, `usuario_email=current_user.email`, `usuario_id=current_user.id`, `descripcion` con resumen. |
| SQL verificación | `backend/sql/verificar_aprobacion_manual_prestamos.sql` incluye una consulta para listar los últimos `APROBACION_MANUAL`. |

**Conclusión:** OK.

---

## Resumen

| # | Requisito | Estado |
|---|-----------|--------|
| 1 | Estado APROBADO (SI) | Implementado |
| 2 | Una sola fecha | Implementado |
| 3 | Texto declaración fijo | Implementado |
| 4 | Solo administración | Implementado (frontend + backend 403) |
| 5 | Datos nuevo crédito → aprobación; editables solo aquí; “documentos analizados” | Implementado |
| 6 | Auditoría en tabla auditoría | Implementado |

**¿Falta algo?** Con lo revisado, no falta ningún punto de los 6. El proceso anterior (evaluar riesgo 7 criterios, aplicar condiciones, asignar fecha) está reemplazado por este flujo único en la lista de préstamos.

**Preguntas opcionales para ti:**

1. ¿El rol en tu BD/auth es exactamente `"administrador"` o usáis otro valor (ej. `"administracion"`)? Si es otro, se puede aceptar también en el backend.
2. ¿Queréis poder editar en el modal de aprobación más campos del préstamo (producto, concesionario, analista, modelo_vehiculo)?
3. ¿Queréis que en detalle del préstamo (o en lista) se muestre explícitamente “Aprobado por: …” y “Fecha aprobación: …” usando `usuario_aprobador` y `fecha_aprobacion`? (Los datos ya se guardan; solo faltaría mostrarlos en la UI si aún no está.)
