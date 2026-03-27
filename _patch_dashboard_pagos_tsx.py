# Patch DashboardPagos.tsx: bundle query + lazy charts
from pathlib import Path

p = Path(
    r"c:\Users\PORTATIL\Documents\BIBLIOTECA\GitHub\pagos\frontend\src\pages\DashboardPagos.tsx"
)
t = p.read_text(encoding="utf-8")

old_imports = """import { useState } from 'react'

import { motion } from 'framer-motion'

import { useQuery } from '@tanstack/react-query'"""

new_imports = """import { lazy, Suspense, useState } from 'react'

import { motion } from 'framer-motion'

import { keepPreviousData, useQuery, useQueryClient } from '@tanstack/react-query'"""

if old_imports not in t:
    raise SystemExit("import block not found")

t = t.replace(old_imports, new_imports, 1)

old_recharts = """import {
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  AreaChart,
  Area,
} from 'recharts'"""

new_recharts = """const DashboardPagosCharts = lazy(() =>
  import('../components/dashboard/DashboardPagosCharts').then(m => ({
    default: m.DashboardPagosCharts,
  }))
)"""

if old_recharts not in t:
    raise SystemExit("recharts import block not found")
t = t.replace(old_recharts, new_recharts, 1)

# Remove unused lucide PieChart, BarChart3 if still needed in header - ModulePageHeader uses CreditCard only in actions - the charts use PieChart in lazy component
# Original imports from lucide include PieChart, BarChart3 - remove if unused in main file
old_lucide = """import {
  CreditCard,
  Shield,
  Clock,
  TrendingUp,
  CheckCircle,
  AlertCircle,
  PieChart,
  BarChart3,
  ChevronRight,
  Filter,
  Search,
} from 'lucide-react'"""

new_lucide = """import {
  CreditCard,
  Shield,
  Clock,
  TrendingUp,
  CheckCircle,
  AlertCircle,
  ChevronRight,
  Filter,
  Search,
} from 'lucide-react'"""

if old_lucide not in t:
    raise SystemExit("lucide block not found")
t = t.replace(old_lucide, new_lucide, 1)

old_queries = """  const {
    data: opcionesFiltros,
    isLoading: loadingOpcionesFiltros,
    isError: errorOpcionesFiltros,
  } = useQuery({
    queryKey: ['opciones-filtros'],

    queryFn: async () => {
      const response = await apiClient.get('/api/v1/dashboard/opciones-filtros')

      return response as {
        analistas: string[]
        concesionarios: string[]
        modelos: string[]
      }
    },
  })

  // Cargar estadA-sticas de pagos

  const {
    data: pagosStats,
    isLoading: pagosStatsLoading,
    refetch,
  } = useQuery({
    queryKey: ['pagos-stats', filtros],

    queryFn: async ({ signal }) => {
      const params = construirFiltrosObject()

      return await pagoService.getStats(params, { signal })
    },

    staleTime: 2 * 60 * 1000,

    refetchOnWindowFocus: false,
  })

  // Cargar KPIs de pagos - queryKey compartida con useSidebarCounts para evitar llamadas duplicadas

  const { data: kpisPagos, isLoading: loadingKPIs } = useQuery({
    queryKey: tieneFiltrosActivos ? ['kpis-pagos', filtros] : ['kpis-pagos'],

    queryFn: async ({ signal }) => {
      const response = (await apiClient.get('/api/v1/pagos/kpis', {
        signal,
      })) as {
        montoCobradoMes: number

        saldoPorCobrar: number

        clientesEnMora: number

        clientesAlDia: number

        cuotas_pendientes?: number
      }

      return response
    },

    staleTime: 5 * 60 * 1000,

    refetchOnWindowFocus: false,

    refetchInterval: 5 * 60 * 1000,

    refetchIntervalInBackground: false,

    retry: 1,
  })

  // Cargar pagos por estado

  const { data: pagosPorEstado, isLoading: loadingPagosEstado } = useQuery({
    queryKey: ['pagos-por-estado', filtros],

    queryFn: async ({ signal }) => {
      const params = construirFiltrosObject()

      const queryParams = new URLSearchParams()

      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })

      const queryString = queryParams.toString()

      const response = (await apiClient.get(
        `/api/v1/pagos/stats${queryString ? '?' + queryString : ''}`,

        { signal }
      )) as {
        total_pagos: number

        total_pagado: number

        pagos_por_estado: Array<{ estado: string; count: number }>
      }

      return response
    },

    staleTime: 2 * 60 * 1000,

    refetchOnWindowFocus: false,
  })

  // Datos para grA�fico de pagos por estado

  const datosPagosEstado =
    pagosPorEstado?.pagos_por_estado.map(item => ({
      estado: item.estado,

      cantidad: item.count,

      porcentaje:
        pagosPorEstado.total_pagos > 0
          ? (item.count / pagosPorEstado.total_pagos) * 100
          : 0,
    })) || []

  // Cargar evoluciA3n de pagos (A�ltimos 6 meses) - DATOS REALES

  const { data: datosEvolucion, isLoading: loadingEvolucion } = useQuery({
    queryKey: ['evolucion-pagos', filtros],

    queryFn: async () => {
      const params = construirFiltrosObject()

      const queryParams = new URLSearchParams()

      queryParams.append('meses', '6')

      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })

      const response = (await apiClient.get(
        `/api/v1/dashboard/evolucion-pagos?${queryParams.toString()}`
      )) as {
        meses: Array<{ mes: string; pagos: number; monto: number }>
      }

      return response.meses
    },

    staleTime: 5 * 60 * 1000,

    refetchOnWindowFocus: false,
  })"""

# File may have encoding differences - try shorter unique anchor
anchor_start = "  const {\n    data: opcionesFiltros,"
anchor_end = "    refetchOnWindowFocus: false,\n  })\n\n  const [isRefreshing"

if anchor_start not in t or "queryKey: ['evolucion-pagos'" not in t:
    raise SystemExit("query anchor not found")

i0 = t.find(anchor_start)
i1 = t.find(anchor_end)
if i0 < 0 or i1 < 0 or i1 <= i0:
    raise SystemExit("range not found")

new_queries = """  const queryClient = useQueryClient()

  const {
    data: inicialPagos,
    isLoading: loadingInicialPagos,
    isError: errorOpcionesFiltros,
    refetch,
    isFetching: fetchingInicialPagos,
  } = useQuery({
    queryKey: ['dashboard-pagos-inicial', filtros],

    queryFn: async ({ signal }) => {
      const params = construirFiltrosObject()
      const queryParams = new URLSearchParams()
      queryParams.append('meses_evolucion', '6')
      Object.entries(params).forEach(([key, value]) => {
        if (value) queryParams.append(key, value.toString())
      })
      const res = (await apiClient.get(
        `/api/v1/dashboard/pagos-inicial?${queryParams.toString()}`,
        { signal }
      )) as {
        opciones_filtros: {
          analistas: string[]
          concesionarios: string[]
          modelos: string[]
        }
        pagos_stats: {
          total_pagos: number
          total_pagado: number
          pagos_por_estado: Array<{ estado: string; count: number }>
          cuotas_pagadas: number
          cuotas_pendientes: number
        }
        kpis_pagos: {
          montoCobradoMes: number
          saldoPorCobrar: number
          clientesEnMora: number
          clientesAlDia: number
          cuotas_pendientes?: number
        }
        evolucion_pagos_meses: Array<{
          mes: string
          pagos: number
          monto: number
        }>
      }

      queryClient.setQueryData(['opciones-filtros'], res.opciones_filtros)
      const filtrosActivos =
        Boolean(filtros.analista) ||
        Boolean(filtros.concesionario) ||
        Boolean(filtros.modelo) ||
        Boolean(filtros.fecha_inicio) ||
        Boolean(filtros.fecha_fin)
      if (!filtrosActivos) {
        queryClient.setQueryData(['kpis-pagos'], res.kpis_pagos)
      }
      return res
    },

    placeholderData: keepPreviousData,

    staleTime: 2 * 60 * 1000,

    refetchOnWindowFocus: false,

    refetchInterval: 5 * 60 * 1000,

    refetchIntervalInBackground: false,

    retry: 1,
  })

  const opcionesFiltros = inicialPagos?.opciones_filtros

  const loadingOpcionesFiltros = loadingInicialPagos

  const pagosStats = inicialPagos?.pagos_stats

  const pagosStatsLoading = loadingInicialPagos

  const kpisPagos = inicialPagos?.kpis_pagos

  const loadingKPIs = loadingInicialPagos

  const pagosPorEstado = inicialPagos?.pagos_stats

  const loadingPagosEstado = loadingInicialPagos

  const datosPagosEstado =
    pagosPorEstado?.pagos_por_estado.map(item => ({
      estado: item.estado,

      cantidad: item.count,

      porcentaje:
        (pagosPorEstado?.total_pagos || 0) > 0
          ? (item.count / (pagosPorEstado?.total_pagos || 1)) * 100
          : 0,
    })) || []

  const datosEvolucion = inicialPagos?.evolucion_pagos_meses

  const loadingEvolucion = loadingInicialPagos"""

# Find anchor_end after old block - the file uses `const [isRefreshing` 
idx_refresh = t.find("\n  const [isRefreshing", i0)
if idx_refresh < 0:
    raise SystemExit("isRefreshing not found")
# include leading newline from old block end
old_block = t[i0:idx_refresh]
t = t[:i0] + new_queries + "\n" + t[idx_refresh:]

# Remove pagoService import if unused
t2 = t.replace(
    "\nimport { pagoService } from '../services/pagoService'\n", "\n", 1
)
if "pagoService" in t2:
    # still referenced?
    pass
else:
    t = t2

p.write_text(t, encoding="utf-8")
print("patched queries")
