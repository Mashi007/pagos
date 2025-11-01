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
  Mail,
  AlertTriangle,
  User,
  LogOut,
  Menu,
} from 'lucide-react'
import { cn } from '@/utils'
import { useSimpleAuth } from '@/store/simpleAuthStore'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

interface SidebarProps {
  isOpen: boolean
  onClose: () => void
  onToggle?: () => void
}

interface MenuItem {
  title: string
  href?: string
  icon: React.ComponentType<{ className?: string }>
  badge?: string
  children?: MenuItem[]
  isSubmenu?: boolean
}

export function Sidebar({ isOpen, onClose, onToggle }: SidebarProps) {
  const location = useLocation()
  const { user, logout, refreshUser } = useSimpleAuth()
  const [openSubmenus, setOpenSubmenus] = useState<string[]>([])
  const [showUserMenu, setShowUserMenu] = useState(false)

  // Variables derivadas del usuario
  const userInitials = user ? `${user.nombre?.charAt(0) || ''}${user.apellido?.charAt(0) || ''}`.toUpperCase() : 'U'
  const userName = user ? `${user.nombre} ${user.apellido}` : 'Usuario'
  const userRoleDisplay = user?.is_admin ? 'Administrador' : 'Usuario'

  const handleLogout = async () => {
    await logout()
    setShowUserMenu(false)
  }

  const getRoleColor = (isAdmin: boolean) => {
    return isAdmin ? 'bg-red-100 text-red-800 border border-red-200' : 'bg-blue-100 text-blue-800 border border-blue-200'
  }

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
      title: 'Cobranzas',
      href: '/cobranzas',
      icon: AlertTriangle,
    },
    {
      title: 'Reportes',
      href: '/reportes',
      icon: FileText,
    },
    {
      title: 'Herramientas',
      icon: Wrench,
      isSubmenu: true,
      children: [
        { title: 'Notificaciones', href: '/notificaciones', icon: Bell },
        // Solo Admin: Plantillas de notificaciones
        ...(user?.is_admin ? [{ title: 'Plantillas', href: '/herramientas/plantillas', icon: Mail }] : []),
        { title: 'Programador', href: '/scheduler', icon: Calendar },
        { title: 'Auditoría', href: '/auditoria', icon: Shield },
      ],
    },
    {
      title: 'Configuración',
      icon: Settings,
      isSubmenu: true,
      children: [
        { title: 'General', href: '/configuracion', icon: Settings },
        { title: 'Validadores', href: '/validadores', icon: CheckCircle },
        { title: 'Configuración Email', href: '/configuracion?tab=email', icon: Mail },
        { title: 'Analistas', href: '/analistas', icon: Users },
        { title: 'Concesionarios', href: '/concesionarios', icon: Building },
        { title: 'Modelos de Vehículos', href: '/modelos-vehiculos', icon: Car },
        { title: 'Usuarios', href: '/usuarios', icon: Shield },
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
        className="fixed left-0 top-0 z-50 h-screen w-64 bg-gradient-to-b from-slate-50 to-blue-50/30 border-r border-blue-200/50 shadow-xl lg:relative lg:translate-x-0 lg:h-full"
      >
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-blue-200/60 bg-gradient-to-r from-blue-600 to-blue-700">
            <div className="flex items-center">
              <div className="w-14 h-14 bg-white rounded-xl flex items-center justify-center shadow-2xl p-2.5 border-2 border-white/20">
                <img 
                  src="/logo-compact.svg" 
                  alt="RAPICREDIT Logo" 
                  className="w-full h-full object-contain"
                />
              </div>
            </div>
            <div className="flex items-center space-x-2">
              {onToggle && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={onToggle}
                  className="lg:hidden text-white hover:bg-blue-800/50"
                >
                  <Menu className="h-5 w-5" />
                </Button>
              )}
              <Button
                variant="ghost"
                size="icon"
                onClick={onClose}
                className="lg:hidden text-white hover:bg-blue-800/50"
              >
                <X className="h-5 w-5" />
              </Button>
            </div>
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
                          "w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200",
                          "text-slate-700 hover:bg-blue-50 hover:text-blue-700 hover:shadow-sm"
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
                                      "flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200",
                                      isActive || isActiveRoute(child.href!)
                                        ? "bg-blue-600 text-white shadow-md shadow-blue-500/30"
                                        : "text-slate-600 hover:bg-blue-50 hover:text-blue-700 hover:shadow-sm"
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
                          "flex items-center justify-between px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200",
                          isActive || isActiveRoute(item.href!)
                            ? "bg-blue-600 text-white shadow-md shadow-blue-500/30"
                            : "text-slate-700 hover:bg-blue-50 hover:text-blue-700 hover:shadow-sm"
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

          {/* Footer con información de usuario */}
          <div className="p-4 border-t border-blue-200/60 bg-white/50">
            {/* Perfil de Usuario */}
            <div className="relative">
              <button
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="w-full flex items-center space-x-3 p-3 rounded-lg hover:bg-blue-50 transition-all duration-200 text-left border border-blue-100/50 hover:border-blue-200 hover:shadow-sm"
              >
                <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-blue-700 text-white rounded-full flex items-center justify-center text-sm font-medium flex-shrink-0 shadow-md">
                  {userInitials}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-slate-900 truncate">
                    {userName}
                  </div>
                  <div className="text-xs text-slate-600 truncate">
                    {userRoleDisplay}
                  </div>
                </div>
                <ChevronDown className={cn(
                  "h-4 w-4 text-slate-500 transition-transform flex-shrink-0",
                  showUserMenu && "transform rotate-180"
                )} />
              </button>

              {/* Menú desplegable del usuario */}
              <AnimatePresence>
                {showUserMenu && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.2 }}
                    className="overflow-hidden"
                  >
                    <div className="mt-2 bg-white rounded-lg border border-blue-200 shadow-xl shadow-blue-500/10">
                      <div className="p-4 border-b border-blue-100 bg-gradient-to-r from-blue-50 to-slate-50">
                        <div className="flex items-center space-x-3">
                          <div className="w-12 h-12 bg-gradient-to-br from-blue-600 to-blue-700 text-white rounded-full flex items-center justify-center text-lg font-medium shadow-md">
                            {userInitials}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="font-medium text-slate-900 truncate">
                              {userName}
                            </div>
                            <Badge className={cn("mt-1", getRoleColor(user?.is_admin || false))}>
                              {userRoleDisplay}
                            </Badge>
                          </div>
                        </div>
                      </div>

                      <div className="py-2">
                        <button className="w-full px-4 py-2 text-left text-sm text-slate-700 hover:bg-blue-50 hover:text-blue-700 transition-colors flex items-center space-x-2">
                          <User className="h-4 w-4" />
                          <span>Mi Perfil</span>
                        </button>
                        <button className="w-full px-4 py-2 text-left text-sm text-slate-700 hover:bg-blue-50 hover:text-blue-700 transition-colors flex items-center space-x-2">
                          <Settings className="h-4 w-4" />
                          <span>Configuración</span>
                        </button>
                        {user?.is_admin === false && (
                          <button 
                            onClick={async () => {
                              try {
                                await refreshUser()
                                window.location.reload()
                              } catch (error) {
                                // Error silencioso para evitar loops de logging
                              }
                            }}
                            className="w-full px-4 py-2 text-left text-sm text-blue-600 hover:bg-blue-50 transition-colors flex items-center space-x-2"
                          >
                            <span>🔄 Actualizar Rol</span>
                          </button>
                        )}
                      </div>

                      <div className="border-t border-blue-100 py-2">
                        <button
                          onClick={handleLogout}
                          className="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 transition-colors flex items-center space-x-2"
                        >
                          <LogOut className="h-4 w-4" />
                          <span>Cerrar Sesión</span>
                        </button>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </div>
      </motion.aside>
    </>
  )
}
