# ✅ CONFIRMACIÓN: La Tabla de Amortización se Calcula con la Fecha Manual del Operador

## 📋 RESPUESTA DIRECTA

**SÍ, CONFIRMADO:** La tabla de amortización se calcula en función de la fecha que el operador ingresa **MANUALMENTE** en el formulario de aprobación.

---

## 🔍 FLUJO COMPLETO DE LA FECHA MANUAL

### **1. FRONTEND - Formulario de Aprobación**

**Archivo:** `frontend/src/components/prestamos/EvaluacionRiesgoForm.tsx`

**Campo de Fecha (Líneas 1243-1259):**
```typescript
<div className="space-y-2">
  <label className="text-sm font-medium text-gray-700">
    Fecha de Desembolso <span className="text-red-500">*</span>
  </label>
  <div className="relative">
    <Calendar className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-4 h-4" />
    <Input
      type="date"
      value={condicionesAprobacion.fecha_base_calculo}  // ✅ VALOR MANUAL DEL OPERADOR
      onChange={(e) => setCondicionesAprobacion({
        ...condicionesAprobacion,
        fecha_base_calculo: e.target.value  // ✅ OPERADOR INGRESA FECHA MANUALMENTE
      })}
      className="pl-10"
      min={new Date().toISOString().split('T')[0]}
    />
  </div>
</div>
```

**Características:**
- ✅ Campo **obligatorio** (`*` en rojo)
- ✅ Input tipo `date` para selección manual
- ✅ Validación: no permite fechas pasadas
- ✅ Valor inicial: fecha actual (pero el operador puede cambiarla)

---

### **2. ENVÍO AL BACKEND**

**Al hacer clic en "Aprobar Préstamo" (Líneas 1414-1423):**
```typescript
const condiciones = {
  estado: 'APROBADO',
  tasa_interes: condicionesAprobacion.tasa_interes,
  plazo_maximo: condicionesAprobacion.plazo_maximo,
  fecha_base_calculo: condicionesAprobacion.fecha_base_calculo,  // ✅ FECHA MANUAL ENVIADA
  observaciones: condicionesAprobacion.observaciones
}

await aplicarCondiciones.mutateAsync({
  prestamoId: prestamo.id,
  condiciones
})
```

**URL:** `POST /api/v1/prestamos/{prestamo_id}/aplicar-condiciones-aprobacion`

---

### **3. BACKEND - Recepción y Almacenamiento**

**Archivo:** `backend/app/api/v1/endpoints/prestamos.py`

**Aplicación de Fecha (Líneas 935-938):**
```python
# Aplicar fecha base de cálculo (SI VIENE)
if "fecha_base_calculo" in condiciones:
    fecha_str = condiciones["fecha_base_calculo"]  # ✅ FECHA MANUAL RECIBIDA
    prestamo.fecha_base_calculo = date_parse(fecha_str).date()  # ✅ CONVERTIDA Y GUARDADA
```

**Persistencia en Base de Datos:**
```python
db.commit()  # ✅ GUARDA fecha_base_calculo en tabla prestamos
```

---

### **4. GENERACIÓN DE TABLA DE AMORTIZACIÓN**

**Archivo:** `backend/app/api/v1/endpoints/prestamos.py`

**Llamada con Fecha Manual (Líneas 172-181):**
```python
# Si se aprueba y tiene fecha_base_calculo, generar tabla de amortización
if prestamo.fecha_base_calculo:  # ✅ VALIDA QUE TENGA FECHA MANUAL
    try:
        # Convertir a date si es necesario
        if isinstance(prestamo.fecha_base_calculo, str):
            fecha = date_parse(prestamo.fecha_base_calculo).date()
        else:
            fecha = prestamo.fecha_base_calculo  # ✅ USA FECHA MANUAL DEL OPERADOR

        generar_amortizacion(prestamo, fecha, db)  # ✅ PASA FECHA MANUAL COMO PARÁMETRO
        logger.info(
            f"Tabla de amortización generada para préstamo {prestamo.id} con fecha de desembolso: {fecha}"
        )
```

---

### **5. CÁLCULO DE FECHAS DE VENCIMIENTO**

**Archivo:** `backend/app/services/prestamo_amortizacion_service.py`

**Función Principal (Líneas 19-61):**
```python
def generar_tabla_amortizacion(
    prestamo: Prestamo,
    fecha_base: date,  # ✅ ESTA ES LA FECHA MANUAL DEL OPERADOR
    db: Session,
) -> List[Cuota]:
    """
    Genera tabla de amortización para un préstamo aprobado.

    Args:
        prestamo: Préstamo para el cual generar la tabla
        fecha_base: Fecha desde la cual se calculan las cuotas  # ✅ FECHA MANUAL
        db: Sesión de base de datos
    """
    # ... código ...

    # Generar cada cuota
    for numero_cuota in range(1, prestamo.numero_cuotas + 1):
        # ✅ Fecha de vencimiento CALCULADA desde fecha_base MANUAL
        fecha_vencimiento = fecha_base + timedelta(days=intervalo_dias * numero_cuota)

        # Crear cuota con fecha calculada
        cuota = Cuota(
            prestamo_id=prestamo.id,
            numero_cuota=numero_cuota,
            fecha_vencimiento=fecha_vencimiento,  # ✅ CALCULADA DESDE FECHA MANUAL
            # ... otros campos ...
        )
```

**Cálculo de Intervalos (Líneas 130-150):**
```python
def _calcular_intervalo_dias(modalidad_pago: str) -> int:
    """
    Calcula intervalo de días entre cuotas según modalidad.
    """
    intervalos = {
        "MENSUAL": 30,
        "QUINCENAL": 15,
        "SEMANAL": 7,
        "DIARIO": 1,
    }
    return intervalos.get(modalidad_pago, 30)
```

---

## 📊 EJEMPLO PRÁCTICO

### **Escenario:**
- **Operador ingresa fecha manual:** `2025-12-01` (1 de diciembre de 2025)
- **Modalidad:** MENSUAL (30 días entre cuotas)
- **Número de cuotas:** 12

### **Cálculo de Fechas de Vencimiento:**

| Cuota | Cálculo | Fecha de Vencimiento |
|-------|---------|---------------------|
| 1 | `2025-12-01 + (30 * 1)` | `2025-12-31` |
| 2 | `2025-12-01 + (30 * 2)` | `2026-01-01` |
| 3 | `2025-12-01 + (30 * 3)` | `2026-01-31` |
| 4 | `2025-12-01 + (30 * 4)` | `2026-03-02` |
| ... | ... | ... |
| 12 | `2025-12-01 + (30 * 12)` | `2025-11-01` (año siguiente) |

**✅ Todas las fechas se calculan DESDE la fecha manual ingresada por el operador**

---

## 🔄 DIAGRAMA DE FLUJO

```
┌─────────────────────────────────────────────────────────────┐
│                    OPERADOR                                  │
│  Selecciona fecha manual en formulario:                      │
│  📅 "2025-12-01"                                             │
└─────────────────────────────────────────────────────────────┘
                        │
                        │ onChange
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              FRONTEND - EvaluacionRiesgoForm                 │
│  condicionesAprobacion.fecha_base_calculo = "2025-12-01"    │
└─────────────────────────────────────────────────────────────┘
                        │
                        │ POST /aplicar-condiciones-aprobacion
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND - API                             │
│  prestamo.fecha_base_calculo = date("2025-12-01")          │
│  db.commit()  # ✅ GUARDA EN BD                              │
└─────────────────────────────────────────────────────────────┘
                        │
                        │ generar_amortizacion(prestamo, fecha, db)
                        ▼
┌─────────────────────────────────────────────────────────────┐
│          SERVICIO - generar_tabla_amortizacion              │
│  fecha_base = "2025-12-01"  # ✅ FECHA MANUAL                │
│                                                              │
│  FOR cada cuota:                                            │
│    fecha_vencimiento = fecha_base + (intervalo * numero)    │
│    ✅ TODAS LAS CUOTAS USAN FECHA MANUAL                    │
└─────────────────────────────────────────────────────────────┘
                        │
                        │ INSERT INTO cuotas
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                  BASE DE DATOS                               │
│  Tabla: cuotas                                               │
│  ┌──────┬─────────────────────┬──────────────────────┐      │
│  │ Cuota│ fecha_vencimiento  │ Origen                │      │
│  ├──────┼─────────────────────┼──────────────────────┤      │
│  │   1  │ 2025-12-31          │ fecha_base + 30d     │      │
│  │   2  │ 2026-01-01          │ fecha_base + 60d     │      │
│  │   3  │ 2026-01-31          │ fecha_base + 90d     │      │
│  │ ...  │ ...                 │ ... (desde fecha     │      │
│  │      │                     │  manual del operador)│      │
│  └──────┴─────────────────────┴──────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

---

## ✅ VERIFICACIONES CLAVE

### **1. Campo Manual en Formulario:**
- ✅ Input tipo `date` permite selección manual
- ✅ Valor inicial es fecha actual (pero se puede cambiar)
- ✅ Campo obligatorio (marcado con `*` rojo)
- ✅ Validación: no permite fechas pasadas

### **2. Envío al Backend:**
- ✅ Fecha se envía en objeto `condiciones`
- ✅ Campo: `fecha_base_calculo`
- ✅ Formato: `YYYY-MM-DD` (ISO)

### **3. Almacenamiento:**
- ✅ Se guarda en `prestamos.fecha_base_calculo`
- ✅ Se convierte a tipo `date` de Python
- ✅ Se persiste en PostgreSQL con `db.commit()`

### **4. Uso en Cálculo:**
- ✅ Se pasa como parámetro `fecha_base` a `generar_amortizacion()`
- ✅ Función calcula: `fecha_vencimiento = fecha_base + (intervalo * numero_cuota)`
- ✅ TODAS las cuotas usan esta fecha como base

### **5. Documentación del Código:**
- ✅ Comentario en línea 3: "Calcula automáticamente cuotas con base en fecha_base_calculo"
- ✅ Docstring línea 29: "fecha_base: Fecha desde la cual se calculan las cuotas"

---

## 🎯 CONCLUSIÓN FINAL

**✅ CONFIRMADO 100%:**

1. ✅ El operador **INGRESA MANUALMENTE** la fecha en el formulario de aprobación
2. ✅ Esta fecha se **ENVÍA** al backend como `fecha_base_calculo`
3. ✅ Se **GUARDA** en la base de datos en la tabla `prestamos`
4. ✅ Se **USA** como base para calcular TODAS las fechas de vencimiento de las cuotas
5. ✅ La fórmula es: `fecha_vencimiento = fecha_manual + (intervalo * numero_cuota)`

**La tabla de amortización se calcula COMPLETAMENTE en función de la fecha que el operador ingresa manualmente en el formulario de aprobación.**

---

## 📝 NOTAS IMPORTANTES

- **La fecha manual es obligatoria:** Si el operador no la ingresa, no se puede aprobar el préstamo (validación en frontend línea 1388)
- **La fecha manual determina todas las cuotas:** No hay cálculo automático de fecha, todo depende de la selección manual
- **Validación de fecha mínima:** No permite seleccionar fechas pasadas (línea 1257: `min={new Date().toISOString().split('T')[0]}`)
- **Logging:** El backend registra la fecha usada para generar la amortización (línea 183)

