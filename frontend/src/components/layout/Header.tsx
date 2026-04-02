import { useState, useEffect } from 'react'

import { Bell, Menu, LogOut, Settings, User, ChevronDown } from 'lucide-react'

import { motion, AnimatePresence } from 'framer-motion'

import { useSimpleAuth } from '../../store/simpleAuthStore'
import { isAdminRole } from '../../utils/rol'

import { Button } from '../../components/ui/button'

import { Badge } from '../../components/ui/badge'

import { Logo } from '../../components/ui/Logo'

// Constantes de configuración

const NOTIFICATIONS_WIDTH = 80

const USER_MENU_WIDTH = 64

const NOTIFICATIONS_MAX_HEIGHT = 96

const DROPDOWN_Z_INDEX = 50

const OVERLAY_Z_INDEX = 30

interface HeaderProps {
  onMenuClick: () => void

  isSidebarOpen: boolean
}

export function Header({ onMenuClick, isSidebarOpen }: HeaderProps) {
  const [showUserMenu, setShowUserMenu] = useState(false)

  const [showNotifications, setShowNotifications] = useState(false)

  const { logout, user, refreshUser } = useSimpleAuth()

  // Variables derivadas del usuario

  const userInitials = user
    ? `${user.nombre?.charAt(0) || ''}${user.apellido?.charAt(0) || ''}`.toUpperCase()
    : 'U'

  const userName = user ? `${user.nombre} ${user.apellido}` : 'Usuario'

  const userRole = isAdminRole(user?.rol) ? 'Administrador' : 'Operativo'

  const showAdminNotifications = isAdminRole(user?.rol)

  // Solo administradores: campana (módulo de notificaciones lo gestiona admin)

  const notifications = showAdminNotifications
    ? [
        {
          id: 1,
          title: 'Pago recibido',
          message: 'Cliente Juan Pérez realizó pago de $500',
          time: '5 min',
          read: false,
        },
        {
          id: 2,
          title: 'Cuota vencida',
          message: '3 clientes tienen cuotas vencidas hoy',
          time: '1 hora',
          read: false,
        },
        {
          id: 3,
          title: 'Reporte generado',
          message: 'Reporte de cartera mensual disponible',
          time: '2 horas',
          read: true,
        },
      ]
    : []

  const unreadCount = notifications.filter(n => !n.read).length

  const handleLogout = async () => {
    await logout()

    setShowUserMenu(false)
  }

  const getRoleColor = (isAdmin: boolean) => {
    return isAdmin ? 'bg-red-100 text-red-800' : 'bg-blue-100 text-blue-800'
  }

  return (
    <header className="sticky top-0 z-40 border-b border-gray-200 bg-white shadow-sm">
      <div className="flex items-center justify-between px-4 py-3">
        {/* Left side */}

        <div className="flex items-center space-x-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={onMenuClick}
            className="lg:hidden"
          >
            <Menu className="h-5 w-5" />
          </Button>

          <div className="hidden lg:block">
            <div className="flex items-center space-x-3">
              <div className="flex h-12 w-12 items-center justify-center rounded-xl border border-gray-200 bg-white p-2 shadow-lg ring-2 ring-gray-50">
                <Logo
                  size="md"
                  className="contrast-110 brightness-110 drop-shadow-md"
                />
              </div>

              <h1 className="text-xl font-semibold text-gray-900">
                RAPICREDIT
              </h1>
            </div>
          </div>
        </div>

        {/* Right side */}

        <div className="flex items-center space-x-3">
          {showAdminNotifications && (
            <div className="relative">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setShowNotifications(!showNotifications)}
                className="relative"
              >
                <Bell className="h-5 w-5" />

                {unreadCount > 0 && (
                  <Badge
                    variant="destructive"
                    className="absolute -right-1 -top-1 flex h-5 w-5 items-center justify-center p-0 text-xs"
                  >
                    {unreadCount}
                  </Badge>
                )}
              </Button>

              <AnimatePresence>
                {showNotifications && (
                  <motion.div
                    initial={{ opacity: 0, y: -10 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0, y: -10 }}
                    className="absolute right-0 z-50 mt-2 w-80 rounded-lg border border-gray-200 bg-white shadow-lg"
                  >
                    <div className="border-b border-gray-200 p-4">
                      <h3 className="font-semibold text-gray-900">
                        Notificaciones
                      </h3>
                    </div>

                    <div className="max-h-96 overflow-y-auto">
                      {notifications.map(notification => (
                        <div
                          key={notification.id}
                          className={`cursor-pointer border-b border-gray-100 p-4 hover:bg-gray-50 ${
                            !notification.read ? 'bg-blue-50' : ''
                          }`}
                        >
                          <div className="flex items-start justify-between">
                            <div className="flex-1">
                              <h4 className="text-sm font-medium text-gray-900">
                                {notification.title}
                              </h4>

                              <p className="mt-1 text-sm text-gray-600">
                                {notification.message}
                              </p>
                            </div>

                            <span className="ml-2 text-xs text-gray-500">
                              {notification.time}
                            </span>
                          </div>

                          {!notification.read && (
                            <div className="mt-2 h-2 w-2 rounded-full bg-blue-500"></div>
                          )}
                        </div>
                      ))}
                    </div>

                    <div className="border-t border-gray-200 p-3">
                      <Button variant="ghost" className="w-full text-sm">
                        Ver todas las notificaciones
                      </Button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}

          {/* User menu */}

          <div className="relative">
            <Button
              variant="ghost"
              onClick={() => setShowUserMenu(!showUserMenu)}
              className="flex items-center space-x-2 px-3"
            >
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary text-sm font-medium text-primary-foreground">
                {userInitials}
              </div>

              <div className="hidden text-left md:block">
                <div className="text-sm font-medium text-gray-900">
                  {userName}
                </div>

                <div className="text-xs text-gray-500">{userRole}</div>
              </div>

              <ChevronDown className="h-4 w-4 text-gray-500" />
            </Button>

            <AnimatePresence>
              {showUserMenu && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="absolute right-0 z-50 mt-2 w-64 rounded-lg border border-gray-200 bg-white shadow-lg"
                >
                  <div className="border-b border-gray-200 p-4">
                    <div className="flex items-center space-x-3">
                      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary text-lg font-medium text-primary-foreground">
                        {userInitials}
                      </div>

                      <div>
                        <div className="font-medium text-gray-900">
                          {userName}
                        </div>

                        <Badge className={getRoleColor(isAdminRole(user?.rol))}>
                          {userRole}
                        </Badge>
                      </div>
                    </div>
                  </div>

                  <div className="py-2">
                    <button className="flex w-full items-center space-x-2 px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50">
                      <User className="h-4 w-4" />

                      <span>Mi Perfil</span>
                    </button>

                    <button className="flex w-full items-center space-x-2 px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50">
                      <Settings className="h-4 w-4" />

                      <span>Configuración</span>
                    </button>

                    {!isAdminRole(user?.rol) && (
                      <button
                        onClick={async () => {
                          try {
                            await refreshUser()

                            window.location.reload()
                          } catch (error) {
                            // Error silencioso para evitar loops de logging
                          }
                        }}
                        className="flex w-full items-center space-x-2 px-4 py-2 text-left text-sm text-blue-600 hover:bg-blue-50"
                      >
                        <span>ðŸ"„ Actualizar Rol</span>
                      </button>
                    )}
                  </div>

                  <div className="border-t border-gray-200 py-2">
                    <button
                      onClick={handleLogout}
                      className="flex w-full items-center space-x-2 px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50"
                    >
                      <LogOut className="h-4 w-4" />

                      <span>Cerrar Sesión</span>
                    </button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </div>
      </div>

      {/* Click outside to close dropdowns */}

      {(showUserMenu || showNotifications) && (
        <div
          className="fixed inset-0 z-30"
          onClick={() => {
            setShowUserMenu(false)

            setShowNotifications(false)
          }}
        />
      )}
    </header>
  )
}
