import React, { useState, useEffect } from 'react'

import { NavLink, useLocation } from 'react-router-dom'

import { motion, AnimatePresence } from 'framer-motion'

import {
  LayoutDashboard,
  Users,
  CreditCard,
  FileText,
  Settings,
  Bell,
  Brain,
  Calendar,
  Shield,
  X,
  ChevronDown,
  ChevronRight,
  ChevronLeft,
  Building,
  Car,
  CheckCircle,
  Mail,
  MessageSquare,
  AlertTriangle,
  User,
  LogOut,
  Menu,
  Briefcase,
  Target,
  DollarSign,
  Clock,
  Download,
  TrendingUp,
} from 'lucide-react'

import { cn } from '../../utils'

import { useSimpleAuth } from '../../store/simpleAuthStore'

import { Button } from '../../components/ui/button'

import { Badge } from '../../components/ui/badge'

import { useSidebarCounts } from '../../hooks/useSidebarCounts'

import { Logo } from '../../components/ui/Logo'

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

  const userInitials = user
    ? `${user.nombre?.charAt(0) || ''}${user.apellido?.charAt(0) || ''}`.toUpperCase()
    : 'U'

  const userName = user ? `${user.nombre} ${user.apellido}` : 'Usuario'

  const userRoleDisplay =
    (user?.rol || 'operativo') === 'administrador'
      ? 'Administrador'
      : 'Operativo'

  const handleLogout = async () => {
    await logout()

    setShowUserMenu(false)
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

      href: '/dashboard/menu',

      icon: LayoutDashboard,
    },

    {
      title: 'CRM',

      icon: Briefcase,

      isSubmenu: true,

      children: [
        { title: 'Clientes', href: '/clientes', icon: Users },

        {
          title: 'Comunicaciones',
          href: '/comunicaciones',
          icon: MessageSquare,
        },

        { title: 'Campañas', href: '/crm/campanas', icon: Mail },

        { title: 'Tickets Atención', href: '/crm/tickets', icon: FileText },

        { title: 'Notificaciones', href: '/notificaciones', icon: Bell },
      ],
    },

    // Ventas: oculto y en pausa (no afectar otros procesos)

    // { title: 'Ventas', href: '/ventas', icon: Target },

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
      title: 'Cobros',

      icon: DollarSign,

      isSubmenu: true,

      children: [
        {
          title: 'Pagos Reportados',
          href: '/cobros/pagos-reportados',
          icon: FileText,
        },

        {
          title: 'Histórico por cliente',
          href: '/cobros/historico-cliente',
          icon: Clock,
        },
      ],
    },

    {
      title: 'Reportes',

      icon: FileText,

      isSubmenu: true,

      children: [
        { title: 'Reportes', href: '/reportes', icon: FileText },

        {
          title: 'Informes (estado de cuenta)',
          href: '/informes',
          icon: Download,
        },

        {
          title: 'Finiquito',
          href: '/finiquitos',
          icon: FileText,
        },
      ],
    },

    {
      title: 'Chat AI',

      href: '/chat-ai',

      icon: Brain,
    },

    {
      title: 'Configuración',

      icon: Settings,

      isSubmenu: true,

      children: [
        { title: 'General', href: '/configuracion', icon: Settings },

        {
          title: 'Plantillas',
          href: '/configuracion?tab=plantillas',
          icon: Mail,
        },

        { title: 'Programador', href: '/scheduler', icon: Calendar },

        { title: 'Validadores', href: '/validadores', icon: CheckCircle },

        {
          title: 'Configuración Email',
          href: '/configuracion?tab=email',
          icon: Mail,
        },

        {
          title: 'Configuración WhatsApp',
          href: '/configuracion?tab=whatsapp',
          icon: MessageSquare,
        },

        {
          title: 'Configuración AI',
          href: '/configuracion?tab=ai',
          icon: Brain,
        },

        {
          title: 'Google (Drive, Sheets, Gmail, OCR)',
          href: '/configuracion?tab=informe-pagos',
          icon: FileText,
        },

        { title: 'OCR', href: '/configuracion?tab=ocr', icon: FileText },

        { title: 'Analistas', href: '/analistas', icon: Users },

        { title: 'Concesionarios', href: '/concesionarios', icon: Building },

        {
          title: 'Modelos de Vehículos',
          href: '/modelos-vehiculos',
          icon: Car,
        },

        { title: 'Usuarios', href: '/usuarios', icon: Shield },
      ],
    },
  ]

  // Abrir automáticamente el submenú si alguna de sus rutas está activa

  useEffect(() => {
    const pathname = location.pathname

    menuItems.forEach(item => {
      if (item.isSubmenu && item.children) {
        const hasActiveChild = item.children.some(child => {
          if (!child.href) return false

          if (child.href.includes('?')) {
            return `${pathname}${location.search}` === child.href
          }

          return (
            pathname === child.href ||
            (pathname.startsWith(child.href) && child.href !== '/')
          )
        })

        if (hasActiveChild) {
          setOpenSubmenus(prev => {
            if (!prev.includes(item.title)) {
              return [...prev, item.title]
            }

            return prev
          })
        }
      }
    })
  }, [location.pathname, location.search])

  // Operativo: no ve Configuración (ni auditoría); solo Administrador puede acceder a esos módulos

  const filteredMenuItems = menuItems.filter(item => {
    const isAdmin = (user?.rol || 'operativo') === 'administrador'

    if (item.title === 'Configuración') return isAdmin

    return true
  })

  const isActiveRoute = (href: string) => {
    // âœ… Manejar dashboard especial

    if (href === '/dashboard') {
      return location.pathname === '/' || location.pathname === '/dashboard'
    }

    // âœ… Para rutas con query parameters, comparar URL completa (EXACTA)

    if (href.includes('?')) {
      // Si el href tiene query params, comparar URL completa EXACTAMENTE

      const currentUrl = `${location.pathname}${location.search}`

      return currentUrl === href
    }

    // âœ… Para rutas sin query params, verificar que sea exacta Y que no haya query params en la URL actual

    // Esto evita que /configuracion resalte cuando estás en /configuracion?tab=email

    if (location.search) {
      // Si la URL actual tiene query params pero el href no, NO resaltar

      return false
    }

    // âœ… Comparación exacta de pathname para rutas sin query params

    return location.pathname === href
  }

  const sidebarVariants = {
    open: {
      x: 0,

      transition: {
        type: 'spring',

        stiffness: 300,

        damping: 40,
      },
    },

    closed: {
      x: '-100%',

      transition: {
        type: 'spring',

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
        type: 'spring',

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
            className="fixed inset-0 z-40 bg-black bg-opacity-50 lg:hidden"
            onClick={onClose}
          />
        )}
      </AnimatePresence>

      {/* Sidebar */}

      <motion.aside
        variants={sidebarVariants}
        initial="closed"
        animate={isOpen ? 'open' : 'closed'}
        className={cn(
          'fixed left-0 top-0 z-50 h-screen border-r border-blue-200/50 bg-gradient-to-b from-slate-50 to-blue-50/30 shadow-xl transition-all duration-300 lg:relative lg:h-full lg:translate-x-0',

          isCompact ? 'w-20' : 'w-64'
        )}
      >
        <div className="flex h-full flex-col">
          {/* Header */}

          <div
            className={cn(
              'flex items-center border-b border-blue-300/40 bg-gradient-to-br from-blue-700 via-blue-600 to-blue-700 shadow-inner',

              isCompact ? 'justify-center p-3' : 'justify-between p-4'
            )}
          >
            {!isCompact && (
              <div className="flex w-full items-center justify-center">
                <motion.div
                  initial={{ scale: 0.9, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  transition={{
                    type: 'spring',

                    stiffness: 200,

                    damping: 15,

                    delay: 0.1,
                  }}
                  whileHover={{ scale: 1.05 }}
                  className="relative flex h-20 w-20 cursor-pointer items-center justify-center rounded-2xl bg-gradient-to-br from-white via-white to-gray-50 p-2.5 transition-all duration-300"
                  style={{
                    boxShadow: `





                      0 10px 25px -5px rgba(0, 0, 0, 0.3),





                      0 8px 10px -6px rgba(0, 0, 0, 0.2),





                      0 0 0 1px rgba(255, 255, 255, 0.9),





                      inset 0 2px 4px rgba(255, 255, 255, 0.6),





                      inset 0 -2px 4px rgba(0, 0, 0, 0.05)





                    `,

                    filter: 'drop-shadow(0 4px 6px rgba(0, 0, 0, 0.15))',
                  }}
                >
                  {/* Efecto de luz superior para relieve */}

                  <div className="pointer-events-none absolute inset-0 rounded-2xl bg-gradient-to-b from-white/60 to-transparent" />

                  {/* Borde interno sutil para profundidad */}

                  <div className="pointer-events-none absolute inset-[1px] rounded-[15px] border border-white/50" />

                  <Logo
                    size="lg"
                    className="relative z-10 brightness-110 contrast-125 drop-shadow-xl"
                  />
                </motion.div>
              </div>
            )}

            {isCompact && (
              <div className="flex items-center justify-center">
                <div
                  className="relative flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-white via-white to-gray-50 p-1.5 transition-all duration-300"
                  style={{
                    boxShadow: `





                      0 6px 15px -3px rgba(0, 0, 0, 0.25),





                      0 4px 6px -4px rgba(0, 0, 0, 0.15),





                      0 0 0 1px rgba(255, 255, 255, 0.9),





                      inset 0 1px 2px rgba(255, 255, 255, 0.6),





                      inset 0 -1px 2px rgba(0, 0, 0, 0.04)





                    `,

                    filter: 'drop-shadow(0 2px 4px rgba(0, 0, 0, 0.12))',
                  }}
                >
                  {/* Efecto de luz superior para relieve */}

                  <div className="pointer-events-none absolute inset-0 rounded-xl bg-gradient-to-b from-white/60 to-transparent" />

                  {/* Borde interno sutil para profundidad */}

                  <div className="pointer-events-none absolute inset-[1px] rounded-[9px] border border-white/50" />

                  <Logo
                    size="md"
                    className="relative z-10 brightness-110 contrast-125 drop-shadow-lg"
                  />
                </div>
              </div>
            )}

            <div
              className={cn(
                'flex items-center',

                isCompact ? 'hidden' : 'space-x-2'
              )}
            >
              {onToggle && (
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={onToggle}
                  className="text-white hover:bg-blue-800/50 lg:hidden"
                >
                  <Menu className="h-5 w-5" />
                </Button>
              )}

              <Button
                variant="ghost"
                size="icon"
                onClick={onClose}
                className="text-white hover:bg-blue-800/50 lg:hidden"
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
                title={isCompact ? 'Expandir sidebar' : 'Compactar sidebar'}
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
            <div
              className={cn(
                'space-y-1',

                isCompact ? 'px-2' : 'px-3'
              )}
            >
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
                          'flex w-full items-center justify-between rounded-lg text-sm font-medium transition-all duration-200',

                          'text-slate-700 hover:bg-blue-50 hover:text-blue-700 hover:shadow-sm',

                          isCompact ? 'justify-center px-2 py-2' : 'px-3 py-2'
                        )}
                        title={isCompact ? item.title : undefined}
                      >
                        <div
                          className={cn(
                            'flex items-center',

                            isCompact ? 'justify-center' : 'space-x-3'
                          )}
                        >
                          <item.icon className="h-5 w-5" />

                          {!isCompact && <span>{item.title}</span>}
                        </div>

                        {!isCompact &&
                          (openSubmenus.includes(item.title) ? (
                            <ChevronDown className="h-4 w-4" />
                          ) : (
                            <ChevronRight className="h-4 w-4" />
                          ))}
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
                            <div
                              className={cn(
                                'mt-1 space-y-1',

                                isCompact ? 'ml-0' : 'ml-6'
                              )}
                            >
                              {item.children.map(child => (
                                <NavLink
                                  key={child.href}
                                  to={child.href!}
                                  onClick={() => {
                                    if (window.innerWidth < 1024) {
                                      onClose()
                                    }
                                  }}
                                  className={() =>
                                    cn(
                                      'flex items-center rounded-lg text-sm font-medium transition-all duration-200',

                                      isActiveRoute(child.href!)
                                        ? 'bg-blue-600 text-white shadow-md shadow-blue-500/30'
                                        : 'text-slate-600 hover:bg-blue-50 hover:text-blue-700 hover:shadow-sm',

                                      isCompact
                                        ? 'justify-center px-2 py-2'
                                        : 'space-x-3 px-3 py-2'
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
                                          className="ml-auto flex h-5 min-w-[20px] items-center justify-center px-1.5 text-xs"
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
                        className={() =>
                          cn(
                            'flex items-center rounded-lg text-sm font-medium transition-all duration-200',

                            isActiveRoute(item.href!)
                              ? 'bg-blue-600 text-white shadow-md shadow-blue-500/30'
                              : 'text-slate-700 hover:bg-blue-50 hover:text-blue-700 hover:shadow-sm',

                            isCompact
                              ? 'justify-center px-2 py-2'
                              : 'justify-between px-3 py-2'
                          )
                        }
                        title={isCompact ? item.title : undefined}
                      >
                        <div
                          className={cn(
                            'flex items-center',

                            isCompact ? 'justify-center' : 'space-x-3'
                          )}
                        >
                          <item.icon className="h-5 w-5" />

                          {!isCompact && <span>{item.title}</span>}
                        </div>

                        {!isCompact && item.badge && (
                          <Badge
                            variant="destructive"
                            className="flex h-5 min-w-[20px] items-center justify-center px-1.5 text-xs"
                          >
                            {item.badge}
                          </Badge>
                        )}
                      </NavLink>

                      {isCompact && item.badge && (
                        <span className="absolute right-1 top-1 z-10 h-2.5 w-2.5 rounded-full border-2 border-white bg-red-500" />
                      )}
                    </div>
                  )}
                </motion.div>
              ))}
            </div>
          </nav>

          {/* Footer con información de usuario */}

          <div
            className={cn(
              'border-t border-blue-200/60 bg-white/50',

              isCompact ? 'p-2' : 'p-4'
            )}
          >
            {/* Perfil de Usuario */}

            <div className="relative">
              <button
                onClick={() => setShowUserMenu(!showUserMenu)}
                className={cn(
                  'flex w-full items-center rounded-lg border border-blue-100/50 text-left transition-all duration-200 hover:border-blue-200 hover:bg-blue-50 hover:shadow-sm',

                  isCompact ? 'justify-center p-2' : 'space-x-3 p-3'
                )}
                title={isCompact ? userName : undefined}
              >
                <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-blue-600 to-blue-700 text-sm font-medium text-white shadow-md">
                  {userInitials}
                </div>

                {!isCompact && (
                  <>
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-sm font-medium text-slate-900">
                        {userName}
                      </div>

                      <div className="truncate text-xs text-slate-600">
                        {userRoleDisplay}
                      </div>
                    </div>

                    <ChevronDown
                      className={cn(
                        'h-4 w-4 flex-shrink-0 text-slate-500 transition-transform',

                        showUserMenu && 'rotate-180 transform'
                      )}
                    />
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
                    <div className="mt-2 rounded-lg border border-blue-200 bg-white shadow-xl shadow-blue-500/10">
                      <div className="py-2">
                        <button className="flex w-full items-center space-x-2 px-4 py-2 text-left text-sm text-slate-700 transition-colors hover:bg-blue-50 hover:text-blue-700">
                          <User className="h-4 w-4" />

                          <span>Mi Perfil</span>
                        </button>

                        {(user?.rol || 'operativo') === 'administrador' && (
                          <NavLink
                            to="/configuracion"
                            className="block flex w-full items-center space-x-2 px-4 py-2 text-left text-sm text-slate-700 transition-colors hover:bg-blue-50 hover:text-blue-700"
                          >
                            <Settings className="h-4 w-4" />

                            <span>Configuración</span>
                          </NavLink>
                        )}

                        {(user?.rol || 'operativo') !== 'administrador' && (
                          <button
                            onClick={async () => {
                              try {
                                await refreshUser()

                                window.location.reload()
                              } catch (error) {
                                // Error silencioso para evitar loops de logging
                              }
                            }}
                            className="flex w-full items-center space-x-2 px-4 py-2 text-left text-sm text-blue-600 transition-colors hover:bg-blue-50"
                          >
                            <span>ðŸ"„ Actualizar Rol</span>
                          </button>
                        )}
                      </div>

                      <div className="border-t border-blue-100 py-2">
                        <button
                          onClick={handleLogout}
                          className="flex w-full items-center space-x-2 px-4 py-2 text-left text-sm text-red-600 transition-colors hover:bg-red-50"
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
