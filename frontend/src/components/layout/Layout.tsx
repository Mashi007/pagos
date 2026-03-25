import { useState, useEffect, useCallback } from 'react'

import { Outlet } from 'react-router-dom'

import { motion } from 'framer-motion'

import { Sidebar } from './Sidebar'

import { Footer } from './Footer'

import { TasaCambioNotificacion } from '../TasaCambioNotificacion'

// Constantes de configuración

const DESKTOP_BREAKPOINT = 1024

const ANIMATION_DURATION = 0.3

export function Layout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const checkScreenSize = () => {
      setIsMobile(window.innerWidth < DESKTOP_BREAKPOINT)

      // En desktop, mantener sidebar abierto por defecto

      if (window.innerWidth >= DESKTOP_BREAKPOINT) {
        setSidebarOpen(true)
      }
    }

    checkScreenSize()

    window.addEventListener('resize', checkScreenSize)

    return () => window.removeEventListener('resize', checkScreenSize)
  }, [])

  const toggleSidebar = useCallback(() => {
    setSidebarOpen(prev => !prev)
  }, [])

  const closeSidebar = useCallback(() => {
    setSidebarOpen(false)
  }, [])

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-gray-50">
      {/* Notificación de Tasa de Cambio (si es necesaria) */}

      <TasaCambioNotificacion />

      {/* Contenedor principal */}

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}

        <Sidebar
          isOpen={sidebarOpen}
          onClose={closeSidebar}
          onToggle={toggleSidebar}
        />

        {/* Main content */}

        <div className="flex min-w-0 flex-1 flex-col">
          {/* Page content */}

          <main className="flex-1 overflow-auto">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: ANIMATION_DURATION }}
              className="container mx-auto max-w-7xl px-4 py-6"
            >
              <Outlet />
            </motion.div>
          </main>

          {/* Footer */}

          <Footer />
        </div>
      </div>
    </div>
  )
}
