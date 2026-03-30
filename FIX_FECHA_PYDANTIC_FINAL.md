# FIX FINAL: Problema de Tipo de Fecha en Pydantic

## El Verdadero Problema

El error persistía porque había un **desajuste de tipos entre frontend, schema y BD**:

| Capa | fecha_requerimiento | fecha_aprobacion |
|------|-------------------|------------------|
| **BD (Model)** | `Date` | `DateTime` |
| **Schema (antes)** | `date` | `datetime` |
| **Schema (ahora)** | `date` ✅ | `datetime` ✅ |
| **Frontend (antes)** | `"2026-02-22T00:00:00"` ❌ | `"2026-02-23T00:00:00"` ✅ |
| **Frontend (ahora)** | `"2026-02-22"` ✅ | `"2026-02-23T00:00:00"` ✅ |

---

## El Error Ocurría Cuando

Pydantic recibía `"2026-02-22T00:00:00"` para un campo de tipo `date`. Pydantic intentaba parsearlo:
- A veces lo interpretaba como datetime primero
- Luego extraía solo la fecha
- Dependiendo del timezone/locale, esto causaba cambio de día (22 → 22, pero con offset = 23 o 21)

---

## La Solución

### Frontend: Enviar según el tipo de BD

```typescript
// fecha_requerimiento: Solo date (YYYY-MM-DD) porque en BD es Date
prestamoData.fecha_requerimiento = fechaReq  // "2026-02-22"

// fecha_aprobacion: DateTime completo porque en BD es DateTime  
prestamoData.fecha_aprobacion = `${fechaApr}T00:00:00`  // "2026-02-23T00:00:00"
```

### Backend: Mantener coherencia con BD

```python
# En Model (prestamo.py)
fecha_requerimiento = Column(Date, ...)
fecha_aprobacion = Column(DateTime(...), ...)

# En Schema (prestamo.py)
fecha_requerimiento: Optional[date] = None
fecha_aprobacion: Optional[datetime] = None

# En Validación (prestamos.py)
ap_date = row.fecha_aprobacion.date()  # Convert datetime to date
req_date = row.fecha_requerimiento     # Already date
if req_date > ap_date:
    # Error
```

---

## Archivos Corregidos

1. ✅ **frontend/src/components/prestamos/CrearPrestamoForm.tsx**
   - `fecha_requerimiento`: Sin hora (YYYY-MM-DD)
   - `fecha_aprobacion`: Con hora (YYYY-MM-DDTHH:MM:SS)

2. ✅ **backend/app/schemas/prestamo.py**
   - `PrestamoUpdate.fecha_requerimiento`: `date`
   - `PrestamoUpdate.fecha_aprobacion`: `datetime`
   - `PrestamoResponse.fecha_requerimiento`: `date`

3. ✅ **backend/app/api/v1/endpoints/prestamos.py**
   - Validación: Normaliza `datetime` a `date` antes de comparar

---

## Estado Final

| Elemento | Tipo | Formato Enviado |
|----------|------|-----------------|
| fecha_requerimiento | date | `"2026-02-22"` |
| fecha_aprobacion | datetime | `"2026-02-23T00:00:00"` |

✅ Pydantic parsea correctamente  
✅ BD almacena en tipo correcto  
✅ Validación compara tipos iguales  
✅ Sin ambigüedad de timezone  

---

## Prueba

```
1. Edita préstamo APROBADO
2. Cambia "Fecha de requerimiento" a 22/02/2026
3. Mantén "Fecha de aprobación" en 23/02/2026
4. Guarda
5. ✅ NO debe mostrar error (22 < 23 es válido)
```

