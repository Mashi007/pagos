# DIAGNÓSTICO: Por Qué Sigue Fallando el PUT

## El Problema Persiste

El navegador muestra:
- `Fecha de requerimiento: 22/02/2026` (mostrado en UI)
- `Fecha de aprobación: 23/02/2026` (mostrado en UI)

Pero el backend rechaza con:
- `"fecha_requerimiento (2026-03-22)"`  ← **¡MARZO, no FEBRERO!**

---

## ¿Qué Significa?

Hay un cambio de mes que no debería ocurrir. Posibles causas:

1. **Frontend enviando fecha invertida** (DD/MM/YYYY en lugar de YYYY-MM-DD)
2. **Browser caché** - código viejo aún en memoria
3. **Timezone server** - aunque es menos probable
4. **Validador Pydantic** interpretando mal

---

## Cómo Diagnosticar (Instrucciones Exactas)

### Paso 1: Abre Developer Tools
```
Presiona: F12 (o Click derecho > Inspect)
```

### Paso 2: Ve a Network Tab
```
Tab > Network
```

### Paso 3: Intenta guardar el formulario
```
Edita el préstamo y presiona "Guardar" o intenta cambiar fecha
```

### Paso 4: Busca el PUT request
```
En la lista de requests, busca el último que sea:
- URL: /api/v1/prestamos/5545 (o tu ID)
- Método: PUT
- Estado: 400 (rojo)
```

### Paso 5: Inspecciona el payload
```
Click en el request
Tab "Request" o "Payload"
Mira exactamente QUÉ se está enviando

Busca:
{
  "fecha_requerimiento": "???" ← ¿QUÉ VALOR HA AQUI?
  "fecha_aprobacion": "???" ← ¿QUÉ VALOR HA AQUI?
}
```

### Paso 6: **Copia y pega exactamente qué se ve**

Esto me dirá si:
- El frontend envía `"2026-02-22"` → Error está en backend
- El frontend envía `"2026-03-22"` → Error está en frontend
- El frontend envía otro formato → Error en conversión

---

## Cambios Hechos en el Código

### Backend (app/schemas/prestamo.py)
Agregué un **validator resiliente** que acepta múltiples formatos y los normaliza:

```python
@field_validator("fecha_requerimiento", "fecha_aprobacion", mode="before")
def parse_fechas_resiliente(cls, v):
    # Acepta: "2026-02-22", "2026-02-22T00:00:00", date, datetime
    # Convierte todos al mismo formato
    if isinstance(v, str) and "T" in v:
        v = v.split("T")[0]  # Extrae parte fecha
    return v
```

Esto debería hacer el backend más resiliente.

### Frontend (CrearPrestamoForm.tsx)
- Envía `fecha_requerimiento` sin hora: `"2026-02-22"`
- Envía `fecha_aprobacion` con hora: `"2026-02-23T00:00:00"`
- Agregué logging para ver qué se está enviando

---

## Pasos Siguientes

### Opción A: Si quieres debugging rápido
1. Abre Console (F12 > Console tab)
2. Busca logs que digan: `[CrearPrestamoForm] Enviando fechas:`
3. Ve qué muestra

### Opción B: Inspecciona Network Request
1. Sigue pasos 1-6 arriba
2. **Cópiame exactamente qué valor aparece** en `fecha_requerimiento` y `fecha_aprobacion`

---

## Importante

**El código actualizado está en:**
- Frontend: CrearPrestamoForm.tsx (con logging)
- Backend: prestamo.py schema (con validator robusto)

Pero **necesito saber qué está siendo enviado** para confirmar el problema.

---

**Próximo paso: Ejecuta el formulario y reporta qué ves en Network Request**
