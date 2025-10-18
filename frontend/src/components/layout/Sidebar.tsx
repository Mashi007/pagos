import React, { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  LayoutDashboard,
  Users,
  CreditCard,
  Calculator,
  Building2,
  FileText,
  BarChart3,
  Settings,
  Bell,
  CheckSquare,
  Search,
  Upload,
  Brain,
  UserCheck,
  Calendar,
  Shield,
  X,
  ChevronDown,
  ChevronRight,
  Wrench,
  Building,
  Car,
  CheckCircle,
} from 'lucide-react'
import { cn } from '@/utils'
import { useSimpleAuth } from '@/store/simpleAuthStore'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

interface SidebarProps {
  isOpen: boolean
  onClose: () => void
}

interface MenuItem {
  title: string
  href?: string
  icon: React.ComponentType<{ className?: string }>
  badge?: string
  requiredRoles?: string[]
  children?: MenuItem[]
  isSubmenu?: boolean
}

export function Sidebar({ isOpen, onClose }: SidebarProps) {
  const location = useLocation()
  const { user } = useSimpleAuth()
  const userRole = user?.is_admin ? 'ADMIN' : 'USER'  // Cambio clave: rol → is_admin
  const [openSubmenus, setOpenSubmenus] = useState<string[]>(['Herramientas'])

  const toggleSubmenu = (title: string) => {
    setOpenSubmenus(prev =>
      prev.includes(title)
        ? prev.filter(item => item !== title)
        : [...prev, title]
    )
  }

  const menuItems: MenuItem[] = [
    {
      title: 'Dashboard',
      href: '/dashboard',
      icon: LayoutDashboard,
    },
    {
      title: 'Clientes',
      href: '/clientes',
      icon: Users,
    },
    {
      title: 'Préstamos',
      href: '/prestamos',
      icon: CreditCard,
    },
    {
      title: 'Pagos',
      href: '/pagos',
      icon: CreditCard,
    },
    {
      title: 'Amortización',
      href: '/amortizacion',
      icon: Calculator,
    },
    {
      title: 'Conciliación',
      href: '/conciliacion',
      icon: Building2,
    },
    {
      title: 'Reportes',
      href: '/reportes',
      icon: FileText,
    },
    {
      title: 'Aprobaciones',
      href: '/aprobaciones',
      icon: CheckSquare,
      badge: '3',
    },
    {
      title: 'Carga Masiva',
      href: '/carga-masiva',
      icon: Upload,
    },
    {
      title: 'Herramientas',
      icon: Wrench,
      isSubmenu: true,
      children: [
        { title: 'Notificaciones', href: '/notificaciones', icon: Bell },
        { title: 'Programador', href: '/scheduler', icon: Calendar },
        { title: 'Auditoría', href: '/auditoria', icon: Shield },
      ],
    },
    {
      title: 'Configuración',
      icon: Settings,
      isSubmenu: true,
      requiredRoles: ['ADMIN', 'GERENTE'],
      children: [
        { title: 'General', href: '/configuracion', icon: Settings },
        { title: 'Validadores', href: '/validadores', icon: CheckCircle },
        { title: 'Analistas', href: '/analistas', icon: Users },
        { title: 'Concesionarios', href: '/concesionarios', icon: Building },
        { title: 'Modelos de Vehículos', href: '/modelos-vehiculos', icon: Car },
        { title: 'Usuarios', href: '/usuarios', icon: Shield, requiredRoles: ['ADMIN'] },
      ],
    },
  ]

  // TEMPORAL: Mostrar todos los elementos del menú sin filtros de permisos
  const filteredMenuItems = menuItems.filter((item) => {
    // Mostrar todos los elementos por ahora
    return true
    // if (!item.requiredRoles) return true
    // return hasAnyRole(item.requiredRoles)
  })

  const isActiveRoute = (href: string) => {
    if (href === '/dashboard') {
      return location.pathname === '/' || location.pathname === '/dashboard'
    }
    return location.pathname.startsWith(href)
  }

  const sidebarVariants = {
    open: {
      x: 0,
      transition: {
        type: "spring",
        stiffness: 300,
        damping: 40,
      },
    },
    closed: {
      x: "-100%",
      transition: {
        type: "spring",
        stiffness: 300,
        damping: 40,
      },
    },
  }

  const itemVariants = {
    open: {
      opacity: 1,
      x: 0,
      transition: {
        type: "spring",
        stiffness: 300,
        damping: 24,
      },
    },
    closed: {
      opacity: 0,
      x: -20,
      transition: {
        duration: 0.2,
      },
    },
  }

  return (
    <>
      {/* Overlay para móvil */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
            onClick={onClose}
          />
        )}
      </AnimatePresence>

      {/* Sidebar */}
      <motion.aside
        variants={sidebarVariants}
        initial="closed"
        animate={isOpen ? "open" : "closed"}
        className="fixed left-0 top-0 z-50 h-full w-64 bg-white border-r border-gray-200 shadow-lg lg:relative lg:translate-x-0"
      >
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-gray-200">
            <div className="flex items-center space-x-3">
              <img 
                src="/logo-compact.svg" 
                alt="RAPICREDIT Logo" 
                className="w-10 h-10"
              />
              <div>
                <h2 className="font-bold text-gray-900 text-sm">RAPICREDIT</h2>
                <p className="text-xs text-gray-500">Sistema v1.0</p>
              </div>
            </div>
            <Button
              variant="ghost"
              size="icon"
              onClick={onClose}
              className="lg:hidden"
            >
              <X className="h-5 w-5" />
            </Button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 overflow-y-auto py-4">
            <div className="px-3 space-y-1">
              {filteredMenuItems.map((item, index) => (
                <motion.div
                  key={item.href || item.title}
                  variants={itemVariants}
                  initial="closed"
                  animate="open"
                  transition={{ delay: index * 0.05 }}
                >
                  {item.isSubmenu && item.children ? (
                    // Renderizar submenú con dropdown
                    <div>
                      <button
                        onClick={() => toggleSubmenu(item.title)}
                        className={cn(
                          "w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                          "text-gray-700 hover:bg-gray-100 hover:text-gray-900"
                        )}
                      >
                        <div className="flex items-center space-x-3">
                          <item.icon className="h-5 w-5" />
                          <span>{item.title}</span>
                        </div>
                        {openSubmenus.includes(item.title) ? (
                          <ChevronDown className="h-4 w-4" />
                        ) : (
                          <ChevronRight className="h-4 w-4" />
                        )}
                      </button>
                      
                      {/* Submenú desplegable */}
                      <AnimatePresence>
                        {openSubmenus.includes(item.title) && (
                          <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: 'auto', opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            transition={{ duration: 0.2 }}
                            className="overflow-hidden"
                          >
                            <div className="ml-6 mt-1 space-y-1">
                              {item.children.map((child) => (
                                <NavLink
                                  key={child.href}
                                  to={child.href!}
                                  onClick={() => {
                                    if (window.innerWidth < 1024) {
                                      onClose()
                                    }
                                  }}
                                  className={({ isActive }) =>
                                    cn(
                                      "flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                                      isActive || isActiveRoute(child.href!)
                                        ? "bg-primary text-primary-foreground shadow-sm"
                                        : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                                    )
                                  }
                                >
                                  <child.icon className="h-4 w-4" />
                                  <span>{child.title}</span>
                                </NavLink>
                              ))}
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  ) : (
                    // Renderizar item normal
                    <NavLink
                      to={item.href!}
                      onClick={() => {
                        // Cerrar sidebar en móvil al hacer click
                        if (window.innerWidth < 1024) {
                          onClose()
                        }
                      }}
                      className={({ isActive }) =>
                        cn(
                          "flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition-colors",
                          isActive || isActiveRoute(item.href!)
                            ? "bg-primary text-primary-foreground shadow-sm"
                            : "text-gray-700 hover:bg-gray-100 hover:text-gray-900"
                        )
                      }
                    >
                      <div className="flex items-center space-x-3">
                        <item.icon className="h-5 w-5" />
                        <span>{item.title}</span>
                      </div>
                      {item.badge && (
                        <Badge
                          variant={item.badge === 'NUEVO' ? 'success' : 'destructive'}
                          className="text-xs"
                        >
                          {item.badge}
                        </Badge>
                      )}
                    </NavLink>
                  )}
                </motion.div>
              ))}
            </div>
          </nav>

          {/* Footer */}
          <div className="p-4 border-t border-gray-200">
            <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg p-3">
              <div className="flex items-center space-x-2">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                <span className="text-sm font-medium text-gray-700">
                  Sistema Activo
                </span>
              </div>
              <p className="text-xs text-gray-600 mt-1">
                Rol: <span className="font-medium">{userRole}</span>
              </p>
            </div>
          </div>
        </div>
      </motion.aside>
    </>
  )
}
