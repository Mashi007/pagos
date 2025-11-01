import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  DollarSign,
  Users,
  CreditCard,
  TrendingUp,
  TrendingDown,
  AlertTriangle,
  CheckCircle,
  Clock,
  Target,
  BarChart3,
  PieChart,
  LineChart,
  Calendar,
  RefreshCw,
  Eye,
  Activity,
  Zap,
  Award,
  Building2,
  Shield,
  Filter,
  X
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { useSimpleAuth } from '@/store/simpleAuthStore'
import { formatCurrency, formatPercentage } from '@/utils'
import { apiClient } from '@/services/api'
import { userService, User } from '@/services/userService'
import { PagosKPIs } from '@/components/pagos/PagosKPIs'
import { pagoService } from '@/services/pagoService'
import { useDashboardFiltros, type DashboardFiltros } from '@/hooks/useDashboardFiltros'
import {
  BarChart,
  Bar,
  PieChart as RechartsPieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  AreaChart,
  Area
} from 'recharts'

export function Dashboard() {
  const navigate = useNavigate()

  // Redirigir al menú de KPIs automáticamente
  useEffect(() => {
    navigate('/dashboard/menu', { replace: true })
  }, [navigate])

  return (
    <div className="flex items-center justify-center min-h-[400px]">
      <div className="text-center">
        <p className="text-gray-600">Redirigiendo al menú de KPIs...</p>
      </div>
    </div>
  )
}
