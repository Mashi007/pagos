import React, { useState, useEffect } from 'react'
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
  ChevronLeft,
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
import { useSidebarCounts } from '@/hooks/useSidebarCounts'

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
  const [isCompact, setIsCompact] = useState(() => {
    // Obtener preferencia guardada en localStorage
    const saved = localStorage.getItem('sidebar-compact')
    return saved === 'true'
  })
  const { counts } = useSidebarCounts()

  // Guardar preferencia en localStorage cuando cambie
  useEffect(() => {
    localStorage.setItem('sidebar-compact', String(isCompact))
  }, [isCompact])

  const toggleCompact = () => {
    setIsCompact(!isCompact)
    // Si se está compactando, cerrar submenús
    if (!isCompact) {
      setOpenSubmenus([])
    }
  }

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
      badge: counts.pagosPendientes > 0 ? String(counts.pagosPendientes) : undefined,
    },
    {
      title: 'Cobranzas',
      href: '/cobranzas',
      icon: AlertTriangle,
      badge: counts.cuotasEnMora > 0 ? String(counts.cuotasEnMora) : undefined,
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
        { 
          title: 'Notificaciones', 
          href: '/notificaciones', 
          icon: Bell,
          badge: counts.notificacionesNoLeidas > 0 ? String(counts.notificacionesNoLeidas) : undefined,
        },
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
        className={cn(
          "fixed left-0 top-0 z-50 h-screen bg-gradient-to-b from-slate-50 to-blue-50/30 border-r border-blue-200/50 shadow-xl lg:relative lg:translate-x-0 lg:h-full transition-all duration-300",
          isCompact ? "w-20" : "w-64"
        )}
      >
        <div className="flex flex-col h-full">
          {/* Header */}
          <div className={cn(
            "flex items-center border-b border-blue-300/40 bg-gradient-to-br from-blue-700 via-blue-600 to-blue-700 shadow-inner",
            isCompact ? "justify-center p-3" : "justify-between p-4"
          )}>
            {!isCompact && (
              <div className="flex items-center justify-center w-full">
                <motion.div
                  initial={{ scale: 0.9, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{ 
                    type: "spring", 
                    stiffness: 200, 
                    damping: 15,
                    delay: 0.1 
                  }}
                  whileHover={{ scale: 1.05 }}
                  className="w-20 h-20 bg-white rounded-2xl flex items-center justify-center shadow-2xl p-3.5 ring-2 ring-white/40 backdrop-blur-sm cursor-pointer transition-all duration-300 hover:shadow-blue-500/20 hover:ring-white/60"
                >
                  <img 
                    src="/logo-compact.svg" 
                    alt="RAPICREDIT Logo" 
                    className="w-full h-full object-contain select-none"
                  />
                </motion.div>
              </div>
            )}
            {isCompact && (
              <div className="flex items-center justify-center">
                <div className="w-12 h-12 bg-white rounded-xl flex items-center justify-center shadow-xl p-2 ring-1 ring-white/40">
                  <img 
                    src="/logo-compact.svg" 
                    alt="RAPICREDIT Logo" 
                    className="w-full h-full object-contain select-none"
                  />
                </div>
              </div>
            )}
            <div className={cn(
              "flex items-center",
              isCompact ? "hidden" : "space-x-2"
            )}>
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
            {/* Botón toggle modo compacto - solo desktop */}
            <div className="hidden lg:block">
              <Button
                variant="ghost"
                size="icon"
                onClick={toggleCompact}
                className="text-white hover:bg-blue-800/50"
                title={isCompact ? "Expandir sidebar" : "Compactar sidebar"}
              >
                {isCompact ? (
                  <ChevronRight className="h-4 w-4" />
                ) : (
                  <ChevronLeft className="h-4 w-4" />
                )}
              </Button>
            </div>
          </div>

          {/* Navigation */}
          <nav className="flex-1 overflow-y-auto py-4">
            <div className={cn(
              "space-y-1",
              isCompact ? "px-2" : "px-3"
            )}>
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
                          "w-full flex items-center justify-between rounded-lg text-sm font-medium transition-all duration-200",
                          "text-slate-700 hover:bg-blue-50 hover:text-blue-700 hover:shadow-sm",
                          isCompact ? "justify-center px-2 py-2" : "px-3 py-2"
                        )}
                        title={isCompact ? item.title : undefined}
                      >
                        <div className={cn(
                          "flex items-center",
                          isCompact ? "justify-center" : "space-x-3"
                        )}>
                          <item.icon className="h-5 w-5" />
                          {!isCompact && <span>{item.title}</span>}
                        </div>
                        {!isCompact && (
                          openSubmenus.includes(item.title) ? (
                            <ChevronDown className="h-4 w-4" />
                          ) : (
                            <ChevronRight className="h-4 w-4" />
                          )
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
                            <div className={cn(
                              "mt-1 space-y-1",
                              isCompact ? "ml-0" : "ml-6"
                            )}>
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
                                      "flex items-center rounded-lg text-sm font-medium transition-all duration-200",
                                      isActive || isActiveRoute(child.href!)
                                        ? "bg-blue-600 text-white shadow-md shadow-blue-500/30"
                                        : "text-slate-600 hover:bg-blue-50 hover:text-blue-700 hover:shadow-sm",
                                      isCompact ? "justify-center px-2 py-2" : "space-x-3 px-3 py-2"
                                    )
                                  }
                                  title={isCompact ? child.title : undefined}
                                >
                                  <child.icon className="h-4 w-4" />
                                  {!isCompact && (
                                    <>
                                      <span>{child.title}</span>
                                      {child.badge && (
                                        <Badge 
                                          variant="destructive" 
                                          className="ml-auto text-xs min-w-[20px] h-5 flex items-center justify-center px-1.5"
                                        >
                                          {child.badge}
                                        </Badge>
                                      )}
                                    </>
                                  )}
                                </NavLink>
                              ))}
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  ) : (
                    // Renderizar item normal
                    <div className="relative">
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
                            "flex items-center rounded-lg text-sm font-medium transition-all duration-200",
                            isActive || isActiveRoute(item.href!)
                              ? "bg-blue-600 text-white shadow-md shadow-blue-500/30"
                              : "text-slate-700 hover:bg-blue-50 hover:text-blue-700 hover:shadow-sm",
                            isCompact ? "justify-center px-2 py-2" : "justify-between px-3 py-2"
                          )
                        }
                        title={isCompact ? item.title : undefined}
                      >
                        <div className={cn(
                          "flex items-center",
                          isCompact ? "justify-center" : "space-x-3"
                        )}>
                          <item.icon className="h-5 w-5" />
                          {!isCompact && <span>{item.title}</span>}
                        </div>
                        {!isCompact && item.badge && (
                          <Badge
                            variant="destructive"
                            className="text-xs min-w-[20px] h-5 flex items-center justify-center px-1.5"
                          >
                            {item.badge}
                          </Badge>
                        )}
                      </NavLink>
                      {isCompact && item.badge && (
                        <span className="absolute top-1 right-1 w-2.5 h-2.5 bg-red-500 rounded-full border-2 border-white z-10" />
                      )}
                    </div>
                  )}
                </motion.div>
              ))}
            </div>
          </nav>

          {/* Footer con información de usuario */}
          <div className={cn(
            "border-t border-blue-200/60 bg-white/50",
            isCompact ? "p-2" : "p-4"
          )}>
            {/* Perfil de Usuario */}
            <div className="relative">
              <button
                onClick={() => setShowUserMenu(!showUserMenu)}
                className={cn(
                  "w-full flex items-center rounded-lg hover:bg-blue-50 transition-all duration-200 text-left border border-blue-100/50 hover:border-blue-200 hover:shadow-sm",
                  isCompact ? "justify-center p-2" : "space-x-3 p-3"
                )}
                title={isCompact ? userName : undefined}
              >
                <div className="w-10 h-10 bg-gradient-to-br from-blue-600 to-blue-700 text-white rounded-full flex items-center justify-center text-sm font-medium flex-shrink-0 shadow-md">
                  {userInitials}
                </div>
                {!isCompact && (
                  <>
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
                  </>
                )}
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
