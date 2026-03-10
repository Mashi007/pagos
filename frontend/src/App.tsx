import React, { useEffect, Suspense } from 'react'
import { Routes, Route, Navigate, useLocation, Outlet } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'

// Layout
import { Layout } from './components/layout/Layout'

// Auth
import { SimpleProtectedRoute } from './components/auth/SimpleProtectedRoute'
import { useSimpleAuth } from './store/simpleAuthStore'
import { BASE_PATH } from './config/env'

/** Rutas que no requieren login: solo formulario de reporte de pago y login. El resto usa Layout con sidebar (protegido). */
const PUBLIC_PATHS = ['/', '/login', '/reporte-pago', '/rapicredit']

/** En rutas públicas solo muestra el Outlet (sin Layout). En el resto, si no hay sesión, redirige a /rapicredit
 * para que un cliente nunca vea login ni app interna. Con basename="/pagos", pathname puede ser "/pagos/rapicredit";
 * normalizamos quitando el basename. */
function RootLayoutWrapper() {
  const location = useLocation()
  const { isAuthenticated, isLoading } = useSimpleAuth()
  let pathname = (location.pathname || '').replace(/\/$/, '') || '/'
  if (BASE_PATH && pathname.startsWith(BASE_PATH)) {
    pathname = pathname.slice(BASE_PATH.length) || '/'
  }
  const isPublic = PUBLIC_PATHS.some(p => pathname === p)
  // Raíz (/ o /pagos/) sin sesión: redirigir al formulario público de inmediato (no mostrar login ni index)
  const isRoot = pathname === '/' || pathname === ''
  if (isRoot && !isLoading && !isAuthenticated) {
    return <Navigate to="/rapicredit" replace />
  }
  if (isPublic) return <Outlet />
  // Ruta no pública y sin sesión → redirigir al formulario público (no mostrar Layout/dashboard)
  if (!isLoading && !isAuthenticated) {
    return <Navigate to="/rapicredit" replace />
  }
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
import Programador from './pages/Programador'
import Clientes from './pages/Clientes'
import Prestamos from './pages/Prestamos'
import Reportes from './pages/Reportes'
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
import RevisionManual from './pages/RevisionManual'
import EditarRevisionManual from './pages/EditarRevisionManual'
// Ventas: en pausa (ruta redirige a /pagos)
import ConversacionesWhatsAppPage from './pages/ConversacionesWhatsApp'
import ComunicacionesPage from './pages/Comunicaciones'
import ReportePagoPage from './pages/ReportePagoPage'
import CobrosPagosReportadosPage from './pages/CobrosPagosReportadosPage'
import CobrosDetallePage from './pages/CobrosDetallePage'
import CobrosHistoricoPage from './pages/CobrosHistoricoPage'

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

  useEffect(() => {
    if (_authInitDone) return
    _authInitDone = true
    initializeAuth()
  }, [initializeAuth])

  // Mostrar loader solo si está cargando Y hay datos de auth (para evitar flash)
  if (isLoading) {
    return <PageLoader />
  }

  return (
    <AnimatePresence mode="wait">
      <Suspense fallback={<PageLoader />}>
        <Routes>
        {/* Una sola raíz path="/" para que Layout reciba correctamente las rutas hijas (dashboard, clientes, etc.) */}
        <Route path="/" element={<RootLayoutWrapper />}>
          {/* Raíz /pagos/ sin auth → redirigir al formulario público (cliente no ve login ni resto de la app) */}
          <Route
            index
            element={
              isAuthenticated ? (
                <Navigate to="/dashboard/menu" replace />
              ) : (
                <Navigate to="/rapicredit" replace />
              )
            }
          />

          {/* Formulario público de reporte de pago (sin login). Link canónico termina en /rapicredit */}
          <Route path="reporte-pago" element={<ReportePagoPage />} />
          <Route path="rapicredit" element={<ReportePagoPage />} />

          {/* Login: misma pantalla que index cuando no autenticado */}
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

          {/* Pagos (URL: /pagos/pagos con basename /pagos) */}
          <Route path="pagos">
            <Route index element={<PagosPage />} />
            <Route path=":id" element={<PagosPage />} />
          </Route>

          {/* Amortización */}
          <Route path="amortizacion" element={<AmortizacionPage />} />

          {/* Conciliación */}

          {/* Cobros (Pagos Reportados, Detalle, Histórico) */}
          <Route path="cobros/pagos-reportados" element={<CobrosPagosReportadosPage />} />
          <Route path="cobros/pagos-reportados/:id" element={<CobrosDetallePage />} />
          <Route path="cobros/historico-cliente" element={<CobrosHistoricoPage />} />

          {/* Reportes */}
          <Route
            path="reportes"
            element={<Reportes />}
          />

          {/* Revisión Manual de Préstamos */}
          <Route path="revision-manual" element={<RevisionManual />} />
          <Route path="revision-manual/editar/:prestamoId" element={<EditarRevisionManual />} />

{/* Notificaciones (dentro de CRM en sidebar) */}
          <Route path="notificaciones" element={<Notificaciones />} />

          {/* Redirecciones: plantillas viven en Configuración */}
          <Route path="notificaciones/plantillas" element={<Navigate to="/configuracion?tab=plantillas" replace />} />
          <Route path="herramientas/notificaciones" element={<Navigate to="/notificaciones" replace />} />
          <Route path="herramientas/plantillas" element={<Navigate to="/configuracion?tab=plantillas" replace />} />

          {/* Comunicaciones (Unificado WhatsApp y Email) */}
          <Route path="comunicaciones" element={<ComunicacionesPage />} />
          {/* Conversaciones WhatsApp (Legacy - mantener por compatibilidad) */}
          <Route path="conversaciones-whatsapp" element={<ConversacionesWhatsAppPage />} />

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

          {/* Chat AI — accesible por cualquier usuario autenticado (no solo admin) */}
          <Route
            path="chat-ai"
            element={
              <SimpleProtectedRoute>
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
