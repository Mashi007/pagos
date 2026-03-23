# Aplicación en Informes - Estados de Cuota Correctos

## 1. Estado de Cuenta Público (`/pagos/rapicredit-estadocuenta`)

### Ubicación de Código
- **Frontend:** `frontend/src/pages/EstadoCuentaPublicoPage.tsx`
- **Backend:** `backend/app/api/v1/endpoints/estado_cuenta_publico.py`

### Cómo Funciona
1. Usuario ingresa cédula
2. Backend valida cédula con rate limiting
3. Backend calcula estados usando: `estado_cuota_para_mostrar()`
4. Frontend muestra tablas con estados CORRECTOS:
   - **PENDIENTE**: Vigentes, no vencidas
   - **VENCIDA**: Retraso <= 90 días
   - **MORA**: Retraso > 90 días
   - **PAGADO**: Completamente pagadas

### Flujo de Datos
```
Frontend Input (cédula)
    ↓
Backend validates & rate limits
    ↓
Backend queries DB: clientes, prestamos, cuotas, pagos
    ↓
Backend calls: estado_cuota_para_mostrar()
    ↓
Backend returns: estados, cuotas_pendientes, tabla_amortización
    ↓
Frontend displays: tablas de cuotas con estado correcto
```

---

## 2. Estado de Cuenta PDF Privado (NUEVO)

### Endpoint
- **Ruta:** `GET /prestamos/{prestamo_id}/estado-cuenta/pdf`
- **Autenticación:** Requerida (JWT token)
- **Responsabilidad:** Usuario autenticado puede descargar PDF de su préstamo

### Ubicación de Código
- **Backend:** `backend/app/api/v1/endpoints/prestamos.py`
- **Servicio:** `backend/app/services/estado_cuenta_pdf.py`
- **Función Auxiliar:** `backend/app/services/estado_cuenta_pdf.py::obtener_datos_estado_cuenta_prestamo()`

### Cómo Funciona
1. Frontend: Usuario hace clic en "Exportar PDF" (tabla de amortización)
2. Frontend: Llama a `prestamoService.descargarEstadoCuentaPDF(prestamo_id)`
3. Backend: Obtiene datos usando `obtener_datos_estado_cuenta_prestamo()`
4. Backend: Genera PDF con `generar_pdf_estado_cuenta()`
5. Backend: Retorna PDF con estados CORRECTOS
6. Frontend: Descarga archivo `Estado_Cuenta_Prestamo_{id}.pdf`

### Flujo de Datos
```
Frontend (click "Exportar PDF")
    ↓
Frontend: fetch GET /api/v1/prestamos/{id}/estado-cuenta/pdf
    ↓
Backend: validate authorization
    ↓
Backend: call obtener_datos_estado_cuenta_prestamo(db, prestamo_id)
    ↓
Backend: call estado_cuota_para_mostrar() para cada cuota
    ↓
Backend: call generar_pdf_estado_cuenta() con datos
    ↓
Backend: return PDF bytes
    ↓
Frontend: download & save PDF
```

---

## 3. Tabla de Amortización (Detalles de Préstamo)

### Ubicación de Código
- **Frontend:** `frontend/src/components/prestamos/TablaAmortizacionPrestamo.tsx`
- **Backend:** `backend/app/api/v1/endpoints/prestamos.py::get_cuotas_prestamo()`
- **Servicio:** `backend/app/services/cuota_estado.py::estado_cuota_para_mostrar()`

### Cómo Funciona
1. Usuario abre detalles de préstamo
2. Frontend carga tabla de amortización
3. Backend retorna cuotas con estado calculado dinámicamente
4. Frontend muestra:
   - Número de cuota
   - Fecha de vencimiento
   - Monto capital, interés, total
   - **ESTADO DINÁMICO:** PENDIENTE, VENCIDA, MORA, PAGADO
   - Botones de acción: "Ver recibo", "Exportar PDF", etc.

### Cambio Reciente
- **Botón "Exportar PDF"** ahora:
  - ✅ Llama a `descargarEstadoCuentaPDF()` (nuevo)
  - ✅ Genera PDF profesional del estado de cuenta
  - ❌ Ya NO llama a `descargarAmortizacionExcel()` (anterior error)

---

## 4. Informes Generales

### Dashboard
- Muestra "Cuotas Vencidas" (dias_mora > 0 y dias_mora <= 90)
- Muestra "Cuotas en Mora" (dias_mora > 90)
- Calcula dinámicamente, no caché

### Reportes
- Todos reutilizan `estado_cuota_para_mostrar()`
- Estados mostrados reflejan fecha actual
- Sincronización automática con BD

---

## Validación de Estados Por Fecha

### Ejemplo: Cuota Vencimiento 20/03/2026

| Fecha Actual | Días Transcurridos | Pagado | Estado Mostrado | Correcto? |
|-------------|-------------------|--------|----------------|----------|
| 19/03/2026 | -1 | $0 | PENDIENTE | ✅ |
| 20/03/2026 | 0 | $0 | PENDIENTE | ✅ |
| 21/03/2026 | 1 | $0 | VENCIDA | ✅ |
| 10/04/2026 | 21 | $0 | VENCIDA | ✅ |
| 15/05/2026 | 56 | $0 | VENCIDA | ✅ |
| 15/06/2026 | 87 | $0 | VENCIDA | ✅ |
| 19/06/2026 | 91 | $0 | VENCIDA | ✅ |
| 20/06/2026 | 92 | $0 | **MORA** | ✅ (ahora correcto) |
| 21/06/2026 | 93 | $0 | **MORA** | ✅ |

---

## Sincronización de Pagos

### Antes de Mostrar Estados
Backend ejecuta: `sincronizar_pagos_pendientes_a_prestamos()`
- Aplica pagos pendientes a cuotas (Cascada)
- Recalcula estados
- Asegura que datos mostrados son actuales

### Flujo
```
Request para mostrar estado de cuenta
    ↓
Backend: sincronizar_pagos_pendientes_a_prestamos()
    ↓
Backend: Query cuotas actuales (con pagos aplicados)
    ↓
Backend: Para cada cuota: estado_cuota_para_mostrar()
    ↓
Backend: Return datos actualizados al frontend
    ↓
Frontend: Muestra tabla con estados correctos
```

---

## Ejemplos de Informes Generados

### PDF: Estado de Cuenta

#### Secciones del PDF
1. **Encabezado RapiCredit**
   - Logo
   - Nombre del cliente
   - Cédula del cliente
   - Fecha de corte

2. **Tabla de Préstamos**
   - ID, Producto, Total Financiamiento, Estado

3. **Tabla de Cuotas Pendientes**
   - Préstamo, Número de Cuota, Vencimiento, Monto, **ESTADO**

4. **Tabla de Amortización (por préstamo)**
   - Cuota, Fecha Vence, Capital, Interés, Total, Saldo, Pago Conc., **ESTADO**, Recibo

5. **Pie de página**
   - Contacto RapiCredit
   - Fecha de generación

#### Estados que Aparecen en PDF
- PENDIENTE (color normal)
- VENCIDA (color naranja/advertencia)
- MORA (color rojo/error)
- PAGADO (color verde)
- CONCILIADO (etiqueta especial)

---

## Reglas de Negocio Aplicadas a Informes

### 1. Cálculo Dinámico
```python
# Nunca cacheado, siempre calcula:
estado = estado_cuota_para_mostrar(
    total_pagado=cuota.total_pagado,
    monto_cuota=cuota.monto,
    fecha_vencimiento=cuota.fecha_vencimiento,
    fecha_referencia=date.today()  # Hoy
)
```

### 2. Tolerancia de Redondeo
```python
# Pagado si: total_pagado >= monto_cuota - 0.01
# Permite diferencias menores a 1 centavo
```

### 3. Prioridad: Backend
```python
# Backend calcula estado, frontend solo lo muestra
# Nunca calcular estado en frontend
```

### 4. Sincronización Previa
```python
# Siempre sincronizar pagos antes de mostrar estados
sincronizar_pagos_pendientes_a_prestamos(db, prestamo_ids)
```

---

## Checklist de Validación

Cuando revises un informe, verifica:

- ✅ PENDIENTE: Sin pagar + vence mañana o hoy
- ✅ VENCIDA: Sin pagar + vence hace < 90 días
- ✅ MORA: Sin pagar + vence hace > 90 días
- ✅ PAGADO: Independiente de fecha
- ✅ Número de cuotas = número de filas en tabla
- ✅ Total pendiente = suma de cuotas sin pagar
- ✅ Fecha de corte = fecha actual

---

## FAQ - Preguntas sobre Informes

**P: ¿Por qué el estado cambió de un día para otro sin pagar?**
A: Porque pasó el umbral de 90 días de atraso. VENCIDA pasó a MORA automáticamente.

**P: ¿Puedo cambiar un estado manualmente?**
A: No. Los estados se calculan automáticamente basados en fecha y pagos. La única forma de cambiar es pagar o registrar un pago.

**P: ¿Los informes se actualizan en tiempo real?**
A: Sí. Se calculan dinámicamente cada vez que se solicitan. No hay caché de estados.

**P: ¿Qué pasa si pago después de 90 días?**
A: La cuota pasa de MORA a PAGADO. El historial registra que estuvo en mora.

**P: ¿Cómo afecta esto a reportes históricos?**
A: Los reportes históricos deben incluir fecha de generación y estado en esa fecha. Si se regeneran, mostrarán estado actual.

---

## Documentos Relacionados

- `REGLAS_NEGOCIO_ESTADOS_CUOTA.md` - Reglas completas
- `IMPLEMENTACION_ESTADOS_CUOTA_RESUMEN.md` - Resumen de cambios
- `backend/app/services/cuota_estado.py` - Función central
- `backend/app/api/v1/endpoints/estado_cuenta_publico.py` - Implementación

---

**Última actualización:** 20/03/2026
**Estado:** ✅ DOCUMENTADO Y FUNCIONAL

