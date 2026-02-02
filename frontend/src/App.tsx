import React, { useEffect, Suspense, useRef } from 'react'
import { Routes, Route, Navigate, useLocation, useNavigate, Outlet } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'

// Layout
import { Layout } from './components/layout/Layout'

// Auth
import { SimpleProtectedRoute } from './components/auth/SimpleProtectedRoute'
import { useSimpleAuth } from './store/simpleAuthStore'
import { BASE_PATH } from './config/env'

/** En rutas públicas (/, /login) solo muestra el Outlet. En el resto muestra Layout con Outlet para que el dashboard y demás carguen. */
function RootLayoutWrapper() {
  const location = useLocation()
  useSimpleAuth()
  const base = BASE_PATH || '/'
  const isPublic = location.pathname === base || location.pathname === base + '/' || location.pathname === base + '/login'
  if (isPublic) return <Outlet />
  return (
    <SimpleProtectedRoute>
      <Layout />
    </SimpleProtectedRoute>
  )
}

// Constantes de configuración
const ANIMATION_DURATION = 0.3

// Pages - Welcome y Login import directo para evitar React #321 (Invalid hook call) en chunks lazy con framer-motion/context.
import { Welcome } from './pages/Welcome'
import { Login } from './pages/Login'
import DashboardMenu from './pages/DashboardMenu'
import Configuracion from './pages/Configuracion'
import Plantillas from './pages/Plantillas'
import Programador from './pages/Programador'
import Clientes from './pages/Clientes'
import Prestamos from './pages/Prestamos'
import Reportes from './pages/Reportes'
import Cobranzas from './pages/Cobranzas'
import ChatAI from './pages/ChatAI'
import Notificaciones from './pages/Notificaciones'
import Analistas from './pages/Analistas'
import PagosPage from './pages/PagosPage'
import AmortizacionPage from './pages/AmortizacionPage'
import Validadores from './pages/Validadores'
import Concesionarios from './pages/Concesionarios'
import ModelosVehiculos from './pages/ModelosVehiculos'
import Usuarios from './pages/Usuarios'
import Solicitudes from './pages/Solicitudes'
import EmbudoClientes from './pages/EmbudoClientes'
import TicketsAtencion from './pages/TicketsAtencion'
import EmbudoConcesionarios from './pages/EmbudoConcesionarios'
// Ventas: en pausa (ruta redirige a /pagos)
import ConversacionesWhatsAppPage from './pages/ConversacionesWhatsApp'
import ComunicacionesPage from './pages/Comunicaciones'

// Todas las páginas ahora están importadas desde archivos reales

const NotFound = () => (
  <div className="min-h-screen flex items-center justify-center">
    <div className="text-center">
      <h1 className="text-6xl font-bold text-gray-300 mb-4">404</h1>
      <h2 className="text-2xl font-semibold text-gray-700 mb-4">
        Página no encontrada
      </h2>
      <p className="text-gray-500 mb-6">
        La página que buscas no existe o ha sido movida.
      </p>
      <button
        onClick={() => window.history.back()}
        className="bg-primary text-primary-foreground px-6 py-2 rounded-lg hover:bg-primary/90 transition-colors"
      >
        Volver atrás
      </button>
    </div>
  </div>
)

// Componente de loading para Suspense
const PageLoader = () => (
  <div className="min-h-screen flex items-center justify-center">
    <div className="text-center">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
      <p className="text-gray-600">Cargando página...</p>
    </div>
  </div>
)

// Una sola ejecución de init auth por sesión (evita doble llamada en StrictMode
// y reduce "demasiadas llamadas a location/history" → "The operation is insecure")
let _authInitDone = false

function App() {
  const { isAuthenticated, isLoading, initializeAuth } = useSimpleAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const redirectDoneRef = useRef(false)

  useEffect(() => {
    if (_authInitDone) return
    _authInitDone = true
    initializeAuth()
  }, [initializeAuth])

  // Un único redirect cuando está autenticado en / o /login (evita múltiples
  // <Navigate> y demasiadas llamadas a la API de historial)
  useEffect(() => {
    if (!isAuthenticated || isLoading) return
    const pathname = location.pathname.replace(/\/$/, '') || '/'
    if (pathname !== '/' && pathname !== '/login') return
    if (redirectDoneRef.current) return
    redirectDoneRef.current = true
    try {
      navigate('/dashboard/menu', { replace: true })
    } catch {
      redirectDoneRef.current = false
    }
  }, [isAuthenticated, isLoading, location.pathname, navigate])

  // Mostrar loader solo si está cargando Y hay datos de auth (para evitar flash)
  if (isLoading) {
    return <PageLoader />
  }

  // Mientras hacemos el único redirect, mostrar loader para no pintar brevemente login
  const pathname = location.pathname.replace(/\/$/, '') || '/'
  if (isAuthenticated && (pathname === '/' || pathname === '/login')) {
    return <PageLoader />
  }

  return (
    <AnimatePresence mode="wait">
      <Suspense fallback={<PageLoader />}>
        <Routes>
        {/* Una sola raíz path="/" para que Layout reciba correctamente las rutas hijas (dashboard, clientes, etc.) */}
        <Route path="/" element={<RootLayoutWrapper />}>
          {/* Raíz /pagos/ → redirigir a login (formulario visible) o dashboard si ya está autenticado */}
          <Route
            index
            element={
              isAuthenticated ? (
                <Navigate to="/dashboard/menu" replace />
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />

          {/* Login */}
          <Route
            path="login"
            element={
              isAuthenticated ? (
                <Navigate to="/dashboard/menu" replace />
              ) : (
                <motion.div
                  key="login"
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: ANIMATION_DURATION }}
                >
                  <Login />
                </motion.div>
              )
            }
          />

          {/* Dashboard - ruta más específica primero */}
          <Route path="dashboard/menu" element={<DashboardMenu />} />
          <Route path="dashboard" element={<Navigate to="/dashboard/menu" replace />} />

          {/* Clientes */}
          <Route path="clientes" element={<Clientes />} />
          <Route path="clientes/nuevo" element={<Clientes />} />
          <Route path="clientes/:id" element={<Clientes />} />

          {/* Préstamos */}
          <Route
            path="prestamos"
            element={<Prestamos />}
          />

          {/* Pagos */}
          <Route path="pagos" element={<PagosPage />} />
          <Route path="pagos/:id" element={<PagosPage />} />

          {/* Amortización */}
          <Route path="amortizacion" element={<AmortizacionPage />} />

          {/* Conciliación */}

          {/* Reportes */}
          <Route
            path="reportes"
            element={<Reportes />}
          />

          {/* Cobranzas */}
          <Route
            path="cobranzas"
            element={<Cobranzas />}
          />

          {/* Notificaciones */}
          <Route path="notificaciones" element={<Notificaciones />} />

          {/* Comunicaciones (Unificado WhatsApp y Email) */}
          <Route path="comunicaciones" element={<ComunicacionesPage />} />
          {/* Conversaciones WhatsApp (Legacy - mantener por compatibilidad) */}
          <Route path="conversaciones-whatsapp" element={<ConversacionesWhatsAppPage />} />

          {/* Herramientas: Plantillas (solo admin) */}
          <Route
            path="herramientas/plantillas"
            element={
              <SimpleProtectedRoute requireAdmin={true}>
                <Plantillas />
              </SimpleProtectedRoute>
            }
          />

          {/* Scheduler */}
          <Route
            path="scheduler"
            element={
              <SimpleProtectedRoute requireAdmin={true}>
                <Programador />
              </SimpleProtectedRoute>
            }
          />

          {/* Configuración */}
          <Route
            path="configuracion"
            element={
              <SimpleProtectedRoute requireAdmin={true}>
                <Configuracion />
              </SimpleProtectedRoute>
            }
          />

          {/* Analistas */}
          <Route
            path="analistas"
            element={
              <SimpleProtectedRoute requireAdmin={true}>
                <Analistas />
              </SimpleProtectedRoute>
            }
          />

          {/* Validadores */}
          <Route
            path="validadores"
            element={
              <SimpleProtectedRoute requireAdmin={true}>
                <Validadores />
              </SimpleProtectedRoute>
            }
          />

          {/* Analistas (ruta alternativa - redirige a /analistas) */}
          <Route
            path="analistaes"
            element={<Navigate to="/analistas" replace />}
          />

          {/* Concesionarios */}
          <Route
            path="concesionarios"
            element={
              <SimpleProtectedRoute requireAdmin={true}>
                <Concesionarios />
              </SimpleProtectedRoute>
            }
          />

          {/* Modelos de Vehículos */}
          <Route
            path="modelos-vehiculos"
            element={
              <SimpleProtectedRoute requireAdmin={true}>
                <ModelosVehiculos />
              </SimpleProtectedRoute>
            }
          />

          {/* Chat AI */}
          <Route
            path="chat-ai"
            element={
              <SimpleProtectedRoute requireAdmin={true}>
                <ChatAI />
              </SimpleProtectedRoute>
            }
          />

          {/* Usuarios */}
          <Route
            path="usuarios"
            element={
              <SimpleProtectedRoute requireAdmin={true}>
                <Usuarios />
              </SimpleProtectedRoute>
            }
          />

          {/* Solicitudes */}
          <Route
            path="solicitudes"
            element={
              <SimpleProtectedRoute requireAdmin={true}>
                <Solicitudes />
              </SimpleProtectedRoute>
            }
          />

          {/* Ventas: en pausa - redirige a inicio para no cargar procesos */}
          <Route path="ventas" element={<Navigate to="/pagos" replace />} />

          {/* CRM */}
          <Route path="crm/embudo-clientes" element={<EmbudoClientes />} />
          <Route path="crm/tickets" element={<TicketsAtencion />} />
          <Route path="crm/embudo-concesionarios" element={<EmbudoConcesionarios />} />

          {/* 404 para rutas no encontradas */}
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
      </Suspense>
    </AnimatePresence>
  )
}

export default App
