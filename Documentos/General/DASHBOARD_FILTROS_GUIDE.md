# Guía: Sistema de Filtros Automáticos para Dashboard

## 🎯 Objetivo
Asegurar que **TODOS los KPIs del dashboard** apliquen automáticamente los filtros (analista, concesionario, modelo, fechas).

## 📋 Arquitectura

### Backend (`backend/app/utils/filtros_dashboard.py`)

**Clase centralizada:** `FiltrosDashboard`

Métodos disponibles:
- `aplicar_filtros_prestamo(query, ...)` - Para queries de préstamos
- `aplicar_filtros_pago(query, ...)` - Para queries de pagos (requiere join con Prestamo)
- `aplicar_filtros_cuota(query, ...)` - Para queries de cuotas (requiere join con Prestamo)

### Frontend (`frontend/src/hooks/useDashboardFiltros.ts`)

**Hook centralizado:** `useDashboardFiltros(filtros)`

Funciones disponibles:
- `construirParams(periodo)` - Construye query string para endpoints
- `construirFiltrosObject()` - Construye objeto de filtros para servicios
- `tieneFiltrosActivos` - Boolean
- `cantidadFiltrosActivos` - Número

## ✅ Cómo Agregar un Nuevo KPI con Filtros Automáticos

### Backend (Python)

```python
from app.utils.filtros_dashboard import FiltrosDashboard

@router.get("/mi-nuevo-kpi")
def mi_nuevo_kpi(
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    fecha_inicio: Optional[date] = Query(None),
    fecha_fin: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 1. Crear tu query base
    query = db.query(func.sum(Prestamo.total_financiamiento)).filter(
        Prestamo.activo.is_(True)
    )

    # 2. ✅ APLICAR FILTROS AUTOMÁTICAMENTE
    query = FiltrosDashboard.aplicar_filtros_prestamo(
        query, analista, concesionario, modelo, fecha_inicio, fecha_fin
    )

    # 3. Ejecutar query
    resultado = query.scalar() or Decimal("0")

    return {"mi_kpi": float(resultado)}
```

**Para queries de PAGOS:**
```python
query = db.query(func.sum(Pago.monto_pagado))
if analista or concesionario or modelo:
    query = query.join(Prestamo, Pago.prestamo_id == Prestamo.id)
query = FiltrosDashboard.aplicar_filtros_pago(
    query, analista, concesionario, modelo, fecha_inicio, fecha_fin
)
```

**Para queries de CUOTAS:**
```python
query = db.query(func.count(Cuota.id)).join(
    Prestamo, Cuota.prestamo_id == Prestamo.id
)
query = FiltrosDashboard.aplicar_filtros_cuota(
    query, analista, concesionario, modelo, fecha_inicio, fecha_fin
)
```

### Frontend (TypeScript/React)

```typescript
import { useDashboardFiltros } from '@/hooks/useDashboardFiltros'

export function Dashboard() {
  const [filtros, setFiltros] = useState<DashboardFiltros>({})

  // ✅ Usar hook centralizado
  const { construirFiltrosObject, construirParams } = useDashboardFiltros(filtros)

  // ✅ Query para nuevo KPI - incluir filtros en queryKey y queryFn
  const { data: nuevoKpi } = useQuery({
    queryKey: ['mi-nuevo-kpi', filtros], // ⚠️ INCLUIR filtros en queryKey
    queryFn: async () => {
      const params = construirParams('mes')
      return await apiClient.get(`/api/v1/mi-endpoint?${params}`)
    },
  })

  // O si el servicio acepta objeto:
  const { data: otroKpi } = useQuery({
    queryKey: ['otro-kpi', filtros],
    queryFn: () => servicio.getData(construirFiltrosObject()),
  })

  return <div>...</div>
}
```

## 🚨 Reglas Importantes

1. **SIEMPRE incluir filtros en queryKey:** `queryKey: ['kpi', filtros]`
2. **SIEMPRE usar FiltrosDashboard en backend** para cualquier nueva query
3. **SIEMPRE usar useDashboardFiltros en frontend** para construir parámetros
4. **SIEMPRE agregar parámetros de filtro** a la firma de la función/endpoint
5. **Los filtros son opcionales** - si no se pasan, no se aplican filtros

## 📝 Ejemplo Completo

### Backend
```python
@router.get("/cartera-por-estado")
def cartera_por_estado(
    analista: Optional[str] = Query(None),
    concesionario: Optional[str] = Query(None),
    modelo: Optional[str] = Query(None),
    fecha_inicio: Optional[date] = Query(None),
    fecha_fin: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Query con filtros automáticos
    base_query = db.query(
        Prestamo.estado,
        func.sum(Prestamo.total_financiamiento)
    ).filter(Prestamo.activo.is_(True))

    base_query = FiltrosDashboard.aplicar_filtros_prestamo(
        base_query, analista, concesionario, modelo, fecha_inicio, fecha_fin
    )

    resultados = base_query.group_by(Prestamo.estado).all()

    return {
        "datos": [
            {"estado": estado, "total": float(total)}
            for estado, total in resultados
        ]
    }
```

### Frontend
```typescript
const { data: carteraPorEstado } = useQuery({
  queryKey: ['cartera-por-estado', filtros],
  queryFn: async () => {
    const params = construirParams(periodo)
    return await apiClient.get(`/api/v1/dashboard/cartera-por-estado?${params}`)
  },
})
```

## ✨ Ventajas

- ✅ **Automático:** Solo necesitas importar y usar
- ✅ **Consistente:** Todos los KPIs usan la misma lógica
- ✅ **Mantenible:** Si cambias los filtros, se aplican a todos los KPIs
- ✅ **Type-safe:** Tipos TypeScript y Python para seguridad

## 🔍 Verificación

Para verificar que un KPI aplica filtros:
1. Aplicar un filtro (ej: analista específico)
2. El KPI debe cambiar según el filtro
3. Si no cambia, el KPI no está usando `FiltrosDashboard`

