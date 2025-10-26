import { useState, useEffect } from 'react'
import { Bell, Search, Menu, LogOut, Settings, User, ChevronDown } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { useSimpleAuth } from '@/store/simpleAuthStore'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { logoService } from '@/services/logoService'

// Constantes de configuración
const SEARCH_BAR_WIDTH = 96
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
  const [logo, setLogo] = useState<string | null>(null)
  const { logout, user, refreshUser } = useSimpleAuth()
  
  // Cargar logo desde backend
  useEffect(() => {
    const cargarLogo = async () => {
      try {
        const logoUrl = await logoService.obtenerLogo()
        if (logoUrl) {
          setLogo(logoUrl)
        }
      } catch (error) {
        console.error('Error cargando logo en Header:', error)
      }
    }
    
    cargarLogo()
  }, [])

  // Variables derivadas del usuario
  const userInitials = user ? `${user.nombre?.charAt(0) || ''}${user.apellido?.charAt(0) || ''}`.toUpperCase() : 'U'
  const userName = user ? `${user.nombre} ${user.apellido}` : 'Usuario'
  const userRole = user?.is_admin ? 'Administrador' : 'Usuario'  // Cambio clave: rol → is_admin

  // Mock de notificaciones - en producción vendrían del backend
  const notifications = [
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

  const unreadCount = notifications.filter(n => !n.read).length

  const handleLogout = async () => {
    await logout()
    setShowUserMenu(false)
  }

  const getRoleColor = (isAdmin: boolean) => {
    return isAdmin ? 'bg-red-100 text-red-800' : 'bg-blue-100 text-blue-800'
  }

  return (
    <header className="bg-white border-b border-gray-200 shadow-sm sticky top-0 z-40">
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
          {logo ? (
            <img 
              src={logo} 
              alt="Logo" 
              className="w-8 h-8 object-contain"
            />
          ) : (
            <img 
              src="/logo-compact.svg" 
              alt="RAPICREDIT Logo" 
              className="w-8 h-8"
            />
          )}
          <h1 className="text-xl font-semibold text-gray-900">
            RAPICREDIT
          </h1>
        </div>
          </div>

          {/* Search bar */}
          <div className={`hidden md:block w-${SEARCH_BAR_WIDTH}`}>
            <Input
              type="search"
              placeholder="Buscar clientes, pagos, documentos..."
              leftIcon={<Search className="h-4 w-4" />}
              className="bg-gray-50 border-gray-200"
            />
          </div>
        </div>

        {/* Right side */}
        <div className="flex items-center space-x-3">
          {/* Search button for mobile */}
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden"
          >
            <Search className="h-5 w-5" />
          </Button>

          {/* Notifications */}
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
                  className="absolute -top-1 -right-1 h-5 w-5 p-0 flex items-center justify-center text-xs"
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
                  className="absolute right-0 mt-2 w-80 bg-white rounded-lg shadow-lg border border-gray-200 z-50"
                >
                  <div className="p-4 border-b border-gray-200">
                    <h3 className="font-semibold text-gray-900">Notificaciones</h3>
                  </div>
                  <div className="max-h-96 overflow-y-auto">
                    {notifications.map((notification) => (
                      <div
                        key={notification.id}
                        className={`p-4 border-b border-gray-100 hover:bg-gray-50 cursor-pointer ${
                          !notification.read ? 'bg-blue-50' : ''
                        }`}
                      >
                        <div className="flex justify-between items-start">
                          <div className="flex-1">
                            <h4 className="font-medium text-sm text-gray-900">
                              {notification.title}
                            </h4>
                            <p className="text-sm text-gray-600 mt-1">
                              {notification.message}
                            </p>
                          </div>
                          <span className="text-xs text-gray-500 ml-2">
                            {notification.time}
                          </span>
                        </div>
                        {!notification.read && (
                          <div className="w-2 h-2 bg-blue-500 rounded-full mt-2"></div>
                        )}
                      </div>
                    ))}
                  </div>
                  <div className="p-3 border-t border-gray-200">
                    <Button variant="ghost" className="w-full text-sm">
                      Ver todas las notificaciones
                    </Button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* User menu */}
          <div className="relative">
            <Button
              variant="ghost"
              onClick={() => setShowUserMenu(!showUserMenu)}
              className="flex items-center space-x-2 px-3"
            >
              <div className="w-8 h-8 bg-primary text-primary-foreground rounded-full flex items-center justify-center text-sm font-medium">
                {userInitials}
              </div>
              <div className="hidden md:block text-left">
                <div className="text-sm font-medium text-gray-900">
                  {userName}
                </div>
                <div className="text-xs text-gray-500">
                  {userRole}
                </div>
              </div>
              <ChevronDown className="h-4 w-4 text-gray-500" />
            </Button>

            <AnimatePresence>
              {showUserMenu && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className="absolute right-0 mt-2 w-64 bg-white rounded-lg shadow-lg border border-gray-200 z-50"
                >
                  <div className="p-4 border-b border-gray-200">
                    <div className="flex items-center space-x-3">
                      <div className="w-12 h-12 bg-primary text-primary-foreground rounded-full flex items-center justify-center text-lg font-medium">
                        {userInitials}
                      </div>
                      <div>
                        <div className="font-medium text-gray-900">
                          {userName}
                        </div>
                        <Badge className={getRoleColor(user?.is_admin || false)}>
                          {userRole}
                        </Badge>
                      </div>
                    </div>
                  </div>

                  <div className="py-2">
                    <button className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center space-x-2">
                      <User className="h-4 w-4" />
                      <span>Mi Perfil</span>
                    </button>
                    <button className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-50 flex items-center space-x-2">
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
                        className="w-full px-4 py-2 text-left text-sm text-blue-600 hover:bg-blue-50 flex items-center space-x-2"
                      >
                        <span>🔄 Actualizar Rol</span>
                      </button>
                    )}
                  </div>

                  <div className="border-t border-gray-200 py-2">
                    <button
                      onClick={handleLogout}
                      className="w-full px-4 py-2 text-left text-sm text-red-600 hover:bg-red-50 flex items-center space-x-2"
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

      {/* Mobile search bar */}
      <div className="md:hidden px-4 pb-3">
        <Input
          type="search"
          placeholder="Buscar..."
          leftIcon={<Search className="h-4 w-4" />}
          className="bg-gray-50 border-gray-200"
        />
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
