# 📍 DÓNDE SE GENERAN LAS TABLAS DE AMORTIZACIÓN

## 🎯 RESUMEN EJECUTIVO

Las tablas de amortización (cuotas) se generan en **múltiples lugares** del sistema:

1. **Servicio principal**: `backend/app/services/prestamo_amortizacion_service.py`
2. **Endpoints API**: `backend/app/api/v1/endpoints/prestamos.py` y `amortizacion.py`
3. **Scripts masivos**: `scripts/python/Generar_Cuotas_Masivas.py`

---

## 📂 UBICACIONES DETALLADAS

### 1. **SERVICIO PRINCIPAL** ⭐
**Archivo:** `backend/app/services/prestamo_amortizacion_service.py`

**Función principal:**
```python
def generar_tabla_amortizacion(
    prestamo: Prestamo,
    fecha_base: date,
    db: Session,
) -> List[Cuota]:
```

**Características:**
- ✅ Función central que genera todas las cuotas
- ✅ Elimina cuotas existentes antes de generar nuevas
- ✅ Calcula método Francés (cuota fija)
- ✅ Maneja modalidades: MENSUAL, QUINCENAL, SEMANAL
- ✅ Calcula interés sobre saldo pendiente
- ✅ Valida consistencia de la tabla generada
- ✅ Guarda las cuotas en la tabla `cuotas` de la BD

**Lógica:**
- Usa `relativedelta` para fechas MENSUALES (mantiene día del mes)
- Usa `timedelta` para QUINCENAL y SEMANAL
- Calcula: `interés = saldo_capital * tasa_mensual`
- Calcula: `capital = cuota - interés`
- Actualiza saldo capital en cada cuota

---

### 2. **ENDPOINT API: Generar Amortización de Préstamo**
**Archivo:** `backend/app/api/v1/endpoints/prestamos.py`

**Endpoint:**
```python
@router.post("/{prestamo_id}/generar-amortizacion")
def generar_amortizacion_prestamo(
    prestamo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
```

**Ruta API:** `POST /api/v1/prestamos/{prestamo_id}/generar-amortizacion`

**Validaciones:**
- ✅ Verifica que el préstamo existe
- ✅ Verifica que el préstamo está en estado `APROBADO`
- ✅ Verifica que tiene `fecha_base_calculo`
- ✅ Solo Admin y Analistas pueden ejecutar

**Uso:**
- Se llama desde el frontend cuando se aprueba un préstamo
- También se puede llamar manualmente para regenerar cuotas

---

### 3. **ENDPOINT API: Generar Tabla (Simulación)**
**Archivo:** `backend/app/api/v1/endpoints/amortizacion.py`

**Endpoint:**
```python
@router.post("/generar-tabla", response_model=TablaAmortizacionResponse)
def generar_tabla_amortizacion(
    request: TablaAmortizacionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
```

**Ruta API:** `POST /api/v1/amortizacion/generar-tabla`

**Características:**
- ✅ Genera tabla de amortización **sin guardar en BD** (solo simulación)
- ✅ Soporta métodos: FRANCESA, ALEMANA, AMERICANA
- ✅ Retorna la tabla calculada para visualización
- ✅ No modifica la base de datos

**Uso:**
- Para previsualizar cómo quedaría la tabla antes de aprobar
- Para cálculos y proyecciones

---

### 4. **ENDPOINT API: Crear Cuotas en BD**
**Archivo:** `backend/app/api/v1/endpoints/amortizacion.py`

**Endpoint:**
```python
@router.post("/prestamo/{prestamo_id}/cuotas", response_model=List[CuotaResponse])
def crear_cuotas_prestamo(
    prestamo_id: int,
    request_data: TablaAmortizacionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
```

**Ruta API:** `POST /api/v1/amortizacion/prestamo/{prestamo_id}/cuotas`

**Características:**
- ✅ Genera la tabla y **la guarda en BD**
- ✅ Verifica que el préstamo no tenga cuotas ya creadas
- ✅ Usa `AmortizacionService.crear_cuotas_prestamo()`

---

### 5. **SCRIPT MASIVO: Generar Cuotas Faltantes**
**Archivo:** `scripts/python/Generar_Cuotas_Masivas.py`

**Función principal:**
```python
def generar_cuotas_prestamo(prestamo: Prestamo, db: Session) -> tuple[bool, int, str]:
```

**Características:**
- ✅ Genera cuotas para **todos los préstamos aprobados** que no tengan cuotas
- ✅ Procesamiento masivo
- ✅ Manejo robusto de errores
- ✅ Logging detallado
- ✅ Reporte de resultados

**Uso:**
```bash
python scripts/python/Generar_Cuotas_Masivas.py
```

**Cuándo usar:**
- Después de una migración de BD
- Cuando hay préstamos aprobados sin cuotas generadas
- Para regenerar todas las cuotas faltantes

---

### 6. **OTRO SCRIPT: Generar Amortización Prestamos Faltantes**
**Archivo:** `scripts/python/Generar_Amortizacion_Prestamos_Faltantes.py`

**Características:**
- ✅ Usa SQL directo para evitar problemas con ORM desincronizado
- ✅ Genera cuotas usando cálculos SQL
- ✅ Útil cuando hay problemas con el modelo ORM

---

## 🔄 FLUJO DE GENERACIÓN

### Flujo Normal (Aprobación de Préstamo):

```
1. Usuario aprueba préstamo → Frontend
2. Frontend llama: POST /api/v1/prestamos/{id}/generar-amortizacion
3. Endpoint valida préstamo y estado
4. Llama: generar_tabla_amortizacion(prestamo, fecha_base, db)
5. Servicio genera todas las cuotas
6. Guarda en tabla `cuotas`
7. Retorna confirmación
```

### Flujo Masivo (Script):

```
1. Ejecutar: python scripts/python/Generar_Cuotas_Masivas.py
2. Script busca préstamos aprobados sin cuotas
3. Para cada préstamo:
   - Llama: generar_tabla_amortizacion(prestamo, fecha_base, db)
   - Genera todas las cuotas
   - Guarda en BD
4. Genera reporte de resultados
```

---

## 📊 TABLA DE BASE DE DATOS

**Tabla:** `cuotas`

**Columnas principales:**
- `id`: ID único
- `prestamo_id`: FK a `prestamos`
- `numero_cuota`: Número de cuota (1, 2, 3...)
- `fecha_vencimiento`: Fecha de vencimiento
- `monto_cuota`: Monto total de la cuota
- `monto_capital`: Capital de la cuota
- `monto_interes`: Interés de la cuota
- `saldo_capital_inicial`: Saldo antes de la cuota
- `saldo_capital_final`: Saldo después de la cuota
- `capital_pagado`: Capital pagado hasta ahora
- `interes_pagado`: Interés pagado hasta ahora
- `mora_pagada`: Mora pagada
- `total_pagado`: Total pagado
- `capital_pendiente`: Capital pendiente
- `interes_pendiente`: Interés pendiente
- `estado`: PENDIENTE, PAGADO, ATRASADO, PARCIAL

---

## ⚙️ CONFIGURACIÓN Y PARÁMETROS

### Parámetros del Préstamo necesarios:
- `total_financiamiento`: Monto total del préstamo
- `numero_cuotas`: Cantidad de cuotas
- `cuota_periodo`: Monto fijo de cada cuota
- `tasa_interes`: Tasa de interés anual (%)
- `modalidad_pago`: MENSUAL, QUINCENAL, SEMANAL
- `fecha_base_calculo`: Fecha desde la cual se calculan las cuotas

### Cálculos realizados:
- **Tasa mensual:** `tasa_interes / 100 / 12`
- **Interés por cuota:** `saldo_capital * tasa_mensual`
- **Capital por cuota:** `cuota_periodo - monto_interes`
- **Saldo final:** `saldo_capital - monto_capital`

---

## 🎯 RESUMEN DE UBICACIONES

| Ubicación | Tipo | Guarda en BD | Uso Principal |
|-----------|------|--------------|---------------|
| `prestamo_amortizacion_service.py` | Servicio | ✅ Sí | Función central |
| `POST /prestamos/{id}/generar-amortizacion` | API Endpoint | ✅ Sí | Generar al aprobar |
| `POST /amortizacion/generar-tabla` | API Endpoint | ❌ No | Simulación/Preview |
| `POST /amortizacion/prestamo/{id}/cuotas` | API Endpoint | ✅ Sí | Crear cuotas manualmente |
| `Generar_Cuotas_Masivas.py` | Script | ✅ Sí | Procesamiento masivo |
| `Generar_Amortizacion_Prestamos_Faltantes.py` | Script | ✅ Sí | Con SQL directo |

---

## 📝 NOTAS IMPORTANTES

1. **Eliminación de cuotas existentes:**
   - El servicio **siempre elimina** las cuotas existentes antes de generar nuevas
   - Esto asegura que no haya duplicados

2. **Validación de consistencia:**
   - Después de generar, valida que la suma de cuotas coincida con el total financiado
   - Tolerancia de 1 centavo para diferencias de redondeo

3. **Manejo de fechas:**
   - MENSUAL: Usa `relativedelta` para mantener el día del mes
   - QUINCENAL/SEMANAL: Usa `timedelta` con días fijos

4. **Tasa de interés 0%:**
   - Si la tasa es 0%, el interés es 0 y todo va a capital

---

**Última actualización:** 2025-01-XX
