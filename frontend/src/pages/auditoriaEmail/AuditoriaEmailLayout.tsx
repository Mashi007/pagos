import { NavLink, Outlet } from 'react-router-dom'
import {
  Activity,
  FileText,
  Link as LinkIcon,
  Mail,
  RefreshCw,
  Shield,
} from 'lucide-react'

import { ModulePageHeader } from '../../components/ui/ModulePageHeader'
import { cn } from '../../utils'

const NAV = [
  { to: '/auditoria/email', end: true, label: 'Panel', icon: Mail },
  { to: '/auditoria/email/escanear', label: 'Escanear', icon: RefreshCw },
  { to: '/auditoria/email/bandeja', label: 'Bandeja', icon: FileText },
  { to: '/auditoria/email/recibos', label: 'Recibos', icon: FileText },
  { to: '/auditoria/email/pipelines', label: 'Pipelines', icon: Activity },
  { to: '/auditoria/email/hallazgos', label: 'Hallazgos', icon: Shield },
  { to: '/auditoria/email/conexion', label: 'Conexión', icon: LinkIcon },
  {
    to: '/auditoria/email/alineamiento',
    label: 'Alineamiento',
    icon: Activity,
  },
  { to: '/auditoria/email/bitacora', label: 'Bitácora', icon: FileText },
]

export default function AuditoriaEmailLayout() {
  return (
    <div className="space-y-4">
      <ModulePageHeader
        icon={Mail}
        title="Auditoría Email"
        description="Escaneo del buzón cobranza@rapicreditca.com: filtros fuertes, lotes hasta 32k, pipelines de cobranza y enrutamiento de recibos."
      />
      <nav className="-mx-1 flex gap-1 overflow-x-auto pb-1">
        {NAV.map(item => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) =>
              cn(
                'inline-flex shrink-0 items-center gap-1.5 rounded-lg border px-3 py-1.5 text-sm whitespace-nowrap',
                isActive
                  ? 'border-blue-600 bg-blue-600 text-white'
                  : 'border-gray-200 bg-white text-slate-700 hover:bg-blue-50'
              )
            }
          >
            <item.icon className="h-3.5 w-3.5" />
            {item.label}
          </NavLink>
        ))}
      </nav>
      <Outlet />
    </div>
  )
}
