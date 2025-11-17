# 🔍 CÓDIGO FUENTE - GRÁFICO EVOLUCIÓN DE MOROSIDAD

## 📱 FRONTEND - Llamada al API

```typescript
// frontend/src/pages/DashboardMenu.tsx (líneas 270-287)

const { data: datosEvolucionMorosidad } = useQuery({
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

## 🔧 BACKEND - Endpoint

```python
# backend/app/api/v1/endpoints/dashboard.py (líneas 2394-2494)

@router.get("/evolucion-morosidad")
@cache_result(ttl=300, key_prefix="dashboard")
def obtener_evolucion_morosidad(
    meses: int = Query(6),
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    fecha_inicio: Optional[date] = Query(None),
    fecha_fin: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    hoy = date.today()

    # Calcular fecha inicio (hace N meses)
    año_inicio = hoy.year
    mes_inicio = hoy.month - meses + 1
    if mes_inicio <= 0:
        año_inicio -= 1
        mes_inicio += 12
    fecha_inicio_query = date(año_inicio, mes_inicio, 1)

    # Query SQL
    query_sql = text("""
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
        GROUP BY EXTRACT(YEAR FROM c.fecha_vencimiento), EXTRACT(MONTH FROM c.fecha_vencimiento)
        ORDER BY año, mes
    """).bindparams(
        fecha_inicio=fecha_inicio_query,
        fecha_fin_total=hoy
    )

    result = db.execute(query_sql)
    morosidad_por_mes = {(int(row[0]), int(row[1])): float(row[2] or Decimal("0")) for row in result}

    # Generar datos mensuales
    meses_data = []
    current_date = fecha_inicio_query
    nombres_meses = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

    while current_date <= hoy:
        año_mes = current_date.year
        num_mes = current_date.month
        morosidad_mes = morosidad_por_mes.get((año_mes, num_mes), 0.0)

        meses_data.append({
            "mes": f"{nombres_meses[num_mes - 1]} {año_mes}",
            "morosidad": morosidad_mes,
        })

        current_date = _obtener_fechas_mes_siguiente(num_mes, año_mes)

    return {"meses": meses_data}
```

## 🗄️ SQL - Query Directa

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

## 📊 Renderizado del Gráfico

```typescript
// frontend/src/pages/DashboardMenu.tsx (líneas 724-733)

<ResponsiveContainer width="100%" height={350}>
  <RechartsLineChart data={datosEvolucionMorosidad}>
    <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
    <XAxis dataKey="mes" stroke="#6b7280" />
    <YAxis stroke="#6b7280" />
    <Tooltip formatter={(value: number) => formatCurrency(value)} />
    <Legend />
    <Line
      type="monotone"
      dataKey="morosidad"
      stroke="#ef4444"
      strokeWidth={3}
      name="Morosidad"
    />
  </RechartsLineChart>
</ResponsiveContainer>
```

## 📋 Resumen

- **Tabla principal:** `cuotas`
- **Join:** `prestamos` (para filtros de estado)
- **Cálculo:** `SUM(c.monto_cuota)` de cuotas vencidas no pagadas
- **Agrupación:** Por año y mes de `fecha_vencimiento`
- **Endpoint:** `GET /api/v1/dashboard/evolucion-morosidad`
- **Cache:** 5 minutos (frontend y backend)

