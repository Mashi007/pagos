# 📊 CONFIRMACIÓN: FUENTE DE DATOS - GRÁFICO "EVOLUCIÓN DE MOROSIDAD"

**Fecha:** 2025-01-04  
**Gráfico:** Evolución de Morosidad (Line Chart)

---

## 🔍 RESUMEN EJECUTIVO

El gráfico "Evolución de Morosidad" obtiene sus datos del endpoint `/api/v1/dashboard/evolucion-morosidad` que consulta la tabla `cuotas` de la base de datos, agrupando por mes y calculando la suma de montos de cuotas vencidas no pagadas.

---

## 📱 FRONTEND - COMPONENTE REACT

### **Ubicación:** `frontend/src/pages/DashboardMenu.tsx`

#### **1. Query de Datos (React Query)**

```270:287:frontend/src/pages/DashboardMenu.tsx
  // Cargar evolución de morosidad
  const { data: datosEvolucionMorosidad, isLoading: loadingEvolucionMorosidad } = useQuery({
    queryKey: ['evolucion-morosidad-menu', JSON.stringify(filtros)],
    queryFn: async () => {
      const params = construirFiltrosObject()
      const queryParams = new URLSearchParams()
      queryParams.append('meses', '6')
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      const response = await apiClient.get(
        `/api/v1/dashboard/evolucion-morosidad?${queryParams.toString()}`
      ) as { meses: Array<{ mes: string; morosidad: number }> }
      return response.meses
    },
    staleTime: 5 * 60 * 1000,
    enabled: true,
  })
```

**Detalles:**
- **Endpoint:** `GET /api/v1/dashboard/evolucion-morosidad`
- **Parámetros enviados:**
  - `meses=6` (últimos 6 meses por defecto)
  - Filtros opcionales: `analista`, `concesionario`, `modelo`, `fecha_inicio`, `fecha_fin`
- **Respuesta esperada:** `{ meses: Array<{ mes: string; morosidad: number }> }`
- **Cache:** 5 minutos (`staleTime`)

#### **2. Renderizado del Gráfico**

```705:736:frontend/src/pages/DashboardMenu.tsx
              {/* Gráfico 5: Evolución de Morosidad */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.7 }}
              >
                <Card className="shadow-lg border-2 border-gray-200">
                  <CardHeader className="bg-gradient-to-r from-red-50 to-orange-50 border-b-2 border-red-200">
                    <CardTitle className="flex items-center space-x-2 text-xl font-bold text-gray-800">
                      <LineChart className="h-6 w-6 text-red-600" />
                      <span>Evolución de Morosidad</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="p-6">
                    {loadingEvolucionMorosidad ? (
                      <div className="h-[350px] flex items-center justify-center">
                        <div className="animate-pulse text-gray-400">Cargando...</div>
                      </div>
                    ) : datosEvolucionMorosidad && datosEvolucionMorosidad.length > 0 ? (
                      <ResponsiveContainer width="100%" height={350}>
                        <RechartsLineChart data={datosEvolucionMorosidad}>
                          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                          <XAxis dataKey="mes" stroke="#6b7280" />
                          <YAxis stroke="#6b7280" />
                          <Tooltip formatter={(value: number) => formatCurrency(value)} />
                          <Legend />
                          <Line type="monotone" dataKey="morosidad" stroke="#ef4444" strokeWidth={3} name="Morosidad" />
                        </RechartsLineChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="h-[350px] flex items-center justify-center text-gray-400">
                        No hay datos disponibles
                      </div>
                    )}
                  </CardContent>
                </Card>
              </motion.div>
```

**Componentes del gráfico:**
- **Tipo:** `LineChart` (Recharts)
- **DataKey:** `morosidad` (valor numérico)
- **XAxis:** `mes` (string: "Jul 2025", "Ago 2025", etc.)
- **Color:** Rojo (`#ef4444`)
- **Altura:** 350px

---

## 🔧 BACKEND - ENDPOINT API

### **Ubicación:** `backend/app/api/v1/endpoints/dashboard.py`

#### **Endpoint Completo:**

```2394:2494:backend/app/api/v1/endpoints/dashboard.py
@router.get("/evolucion-morosidad")
@cache_result(ttl=300, key_prefix="dashboard")
def obtener_evolucion_morosidad(
    meses: int = Query(6, description="Número de meses a mostrar (últimos N meses)"),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    fecha_inicio: Optional[date] = Query(None),
    fecha_fin: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Evolución de morosidad (últimos N meses) para DashboardCuotas
    Consulta tabla cuotas para obtener morosidad real por mes
    OPTIMIZADO: Una sola query con GROUP BY en lugar de múltiples queries en loop
    """
    try:
        # text ya está importado al inicio del archivo

        hoy = date.today()
        nombres_meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

        # Calcular fecha inicio (hace N meses)
        año_inicio = hoy.year
        mes_inicio = hoy.month - meses + 1
        if mes_inicio <= 0:
            año_inicio -= 1
            mes_inicio += 12
        fecha_inicio_query = date(año_inicio, mes_inicio, 1)

        # OPTIMIZACIÓN: Una sola query con GROUP BY en lugar de múltiples queries
        # Construir filtros base
        filtros_base = [
            "p.estado = 'APROBADO'",
            "c.fecha_vencimiento >= :fecha_inicio",
            "c.fecha_vencimiento < :fecha_fin_total",
            "c.estado != 'PAGADO'",
        ]

        filtros_params = {
            "fecha_inicio": fecha_inicio_query,
            "fecha_fin_total": hoy,
        }

        # Aplicar filtros opcionales
        if analista:
            filtros_base.append("(p.analista = :analista OR p.producto_financiero = :analista)")
            filtros_params["analista"] = analista
        if concesionario:
            filtros_base.append("p.concesionario = :concesionario")
            filtros_params["concesionario"] = concesionario
        if modelo:
            filtros_base.append("(p.producto = :modelo OR p.modelo_vehiculo = :modelo)")
            filtros_params["modelo"] = modelo

        where_clause = " AND ".join(filtros_base)

        # Query optimizada: GROUP BY por mes y año (usar bindparams para seguridad)
        query_sql = text(
            """
            SELECT 
                EXTRACT(YEAR FROM c.fecha_vencimiento)::int as año,
                EXTRACT(MONTH FROM c.fecha_vencimiento)::int as mes,
                COALESCE(SUM(c.monto_cuota), 0) as morosidad
            FROM cuotas c
            INNER JOIN prestamos p ON c.prestamo_id = p.id
            WHERE """
            + where_clause
            + """
            GROUP BY EXTRACT(YEAR FROM c.fecha_vencimiento), EXTRACT(MONTH FROM c.fecha_vencimiento)
            ORDER BY año, mes
        """
        ).bindparams(**filtros_params)

        result = db.execute(query_sql)
        morosidad_por_mes = {(int(row[0]), int(row[1])): float(row[2] or Decimal("0")) for row in result}

        # Generar datos mensuales (incluyendo meses sin datos)
        meses_data = []
        current_date = fecha_inicio_query

        while current_date <= hoy:
            año_mes = current_date.year
            num_mes = current_date.month
            morosidad_mes = morosidad_por_mes.get((año_mes, num_mes), 0.0)

            meses_data.append(
                {
                    "mes": f"{nombres_meses[num_mes - 1]} {año_mes}",
                    "morosidad": morosidad_mes,
                }
            )

            # Avanzar al siguiente mes
            current_date = _obtener_fechas_mes_siguiente(num_mes, año_mes)

        return {"meses": meses_data}

    except Exception as e:
```

---

## 🗄️ BASE DE DATOS - QUERY SQL

### **Query Principal:**

```sql
SELECT 
    EXTRACT(YEAR FROM c.fecha_vencimiento)::int as año,
    EXTRACT(MONTH FROM c.fecha_vencimiento)::int as mes,
    COALESCE(SUM(c.monto_cuota), 0) as morosidad
FROM cuotas c
INNER JOIN prestamos p ON c.prestamo_id = p.id
WHERE 
    p.estado = 'APROBADO'
    AND c.fecha_vencimiento >= :fecha_inicio
    AND c.fecha_vencimiento < :fecha_fin_total
    AND c.estado != 'PAGADO'
    -- Filtros opcionales:
    -- AND (p.analista = :analista OR p.producto_financiero = :analista)
    -- AND p.concesionario = :concesionario
    -- AND (p.producto = :modelo OR p.modelo_vehiculo = :modelo)
GROUP BY EXTRACT(YEAR FROM c.fecha_vencimiento), EXTRACT(MONTH FROM c.fecha_vencimiento)
ORDER BY año, mes
```

### **Tablas Involucradas:**

1. **`cuotas`** (alias: `c`)
   - Campo principal: `monto_cuota`
   - Filtros: `fecha_vencimiento`, `estado`
   - Relación: `c.prestamo_id = p.id`

2. **`prestamos`** (alias: `p`)
   - Filtros: `estado = 'APROBADO'`
   - Filtros opcionales: `analista`, `concesionario`, `producto`, `modelo_vehiculo`

### **Definición de Morosidad:**

La morosidad se calcula como:
- **Suma de `monto_cuota`** de todas las cuotas que cumplan:
  - `prestamo.estado = 'APROBADO'`
  - `cuota.fecha_vencimiento < fecha_actual` (vencidas)
  - `cuota.estado != 'PAGADO'` (no pagadas)
  - Agrupado por mes y año de `fecha_vencimiento`

---

## 📋 FLUJO DE DATOS COMPLETO

```
1. Frontend (DashboardMenu.tsx)
   └─> React Query Hook
       └─> GET /api/v1/dashboard/evolucion-morosidad?meses=6&[filtros]
           │
2. Backend (dashboard.py)
   └─> Endpoint: obtener_evolucion_morosidad()
       └─> Construye query SQL
           │
3. Base de Datos (PostgreSQL)
   └─> Ejecuta query en tablas: cuotas + prestamos
       └─> Retorna: [{año, mes, morosidad}, ...]
           │
4. Backend procesa resultados
   └─> Formatea datos: [{mes: "Jul 2025", morosidad: 65000}, ...]
       └─> Retorna: {"meses": [...]}
           │
5. Frontend recibe datos
   └─> React Query cachea (5 min)
       └─> Pasa datos a RechartsLineChart
           │
6. Gráfico renderizado
   └─> Line Chart con datos de morosidad por mes
```

---

## 🔍 PARÁMETROS Y FILTROS

### **Parámetros de Query:**

| Parámetro | Tipo | Requerido | Descripción | Ejemplo |
|-----------|------|-----------|-------------|---------|
| `meses` | int | No (default: 6) | Número de meses a mostrar | `6` |
| `analista` | string | No | Filtrar por analista | `"Juan Pérez"` |
| `concesionario` | string | No | Filtrar por concesionario | `"Toyota"` |
| `modelo` | string | No | Filtrar por modelo | `"Corolla"` |
| `fecha_inicio` | date | No | Fecha inicio personalizada | `"2025-01-01"` |
| `fecha_fin` | date | No | Fecha fin personalizada | `"2025-12-31"` |

### **Ejemplo de Request:**

```http
GET /api/v1/dashboard/evolucion-morosidad?meses=6&analista=Juan%20Pérez&concesionario=Toyota
```

### **Ejemplo de Response:**

```json
{
  "meses": [
    {
      "mes": "Jul 2025",
      "morosidad": 65000.0
    },
    {
      "mes": "Ago 2025",
      "morosidad": 72000.0
    },
    {
      "mes": "Sep 2025",
      "morosidad": 90000.0
    },
    {
      "mes": "Oct 2025",
      "morosidad": 115000.0
    },
    {
      "mes": "Nov 2025",
      "morosidad": 5000.0
    }
  ]
}
```

---

## ✅ VERIFICACIÓN

### **Cómo verificar la fuente de datos:**

1. **Ver logs del backend:**
   ```bash
   # Los logs mostrarán la query SQL ejecutada
   ```

2. **Inspeccionar Network Tab en navegador:**
   - Abrir DevTools → Network
   - Filtrar por "evolucion-morosidad"
   - Ver Request/Response

3. **Ejecutar query SQL directamente:**
   ```sql
   SELECT 
       EXTRACT(YEAR FROM c.fecha_vencimiento)::int as año,
       EXTRACT(MONTH FROM c.fecha_vencimiento)::int as mes,
       COALESCE(SUM(c.monto_cuota), 0) as morosidad
   FROM cuotas c
   INNER JOIN prestamos p ON c.prestamo_id = p.id
   WHERE 
       p.estado = 'APROBADO'
       AND c.fecha_vencimiento >= CURRENT_DATE - INTERVAL '6 months'
       AND c.fecha_vencimiento < CURRENT_DATE
       AND c.estado != 'PAGADO'
   GROUP BY EXTRACT(YEAR FROM c.fecha_vencimiento), EXTRACT(MONTH FROM c.fecha_vencimiento)
   ORDER BY año, mes;
   ```

---

## 📝 CONCLUSIÓN

**El gráfico "Evolución de Morosidad" obtiene sus datos de:**

1. ✅ **Tabla:** `cuotas` (principal) + `prestamos` (join)
2. ✅ **Cálculo:** Suma de `monto_cuota` de cuotas vencidas no pagadas
3. ✅ **Agrupación:** Por mes y año de `fecha_vencimiento`
4. ✅ **Endpoint:** `/api/v1/dashboard/evolucion-morosidad`
5. ✅ **Cache:** 5 minutos (frontend) + 5 minutos (backend)

**Definición de Morosidad:**
- Cuotas con `fecha_vencimiento < fecha_actual`
- Cuotas con `estado != 'PAGADO'`
- Préstamos con `estado = 'APROBADO'`
- Suma de `monto_cuota` agrupada por mes

---

**Documento generado automáticamente**  
**Última actualización:** 2025-01-04

