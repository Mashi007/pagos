import { useEffect, useState, lazy, Suspense } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'

// Layout
import { Layout } from '@/components/layout/Layout'

// Auth
import { SimpleProtectedRoute } from '@/components/auth/SimpleProtectedRoute'
import { useSimpleAuth } from '@/store/simpleAuthStore'

// Pages - Lazy loading para optimización
const Login = lazy(() => import('@/pages/Login'))
const Dashboard = lazy(() => import('@/pages/Dashboard'))
const Clientes = lazy(() => import('@/pages/Clientes'))
const Prestamos = lazy(() => import('@/pages/Prestamos'))
const Pagos = lazy(() => import('@/pages/Pagos'))
const NuevoPago = lazy(() => import('@/pages/NuevoPago'))
const ConciliacionBancaria = lazy(() => import('@/pages/ConciliacionBancaria'))
const Amortizacion = lazy(() => import('@/pages/Amortizacion'))
const Reportes = lazy(() => import('@/pages/Reportes'))
const Aprobaciones = lazy(() => import('@/pages/Aprobaciones'))
const Auditoria = lazy(() => import('@/pages/Auditoria'))
const Notificaciones = lazy(() => import('@/pages/Notificaciones'))
const Programador = lazy(() => import('@/pages/Programador'))
const Configuracion = lazy(() => import('@/pages/Configuracion'))
const PrestamosPage = lazy(() => import('@/pages/PrestamosPage'))
const Analistas = lazy(() => import('@/pages/Analistas'))
const PagosPage = lazy(() => import('@/pages/PagosPage'))
const AmortizacionPage = lazy(() => import('@/pages/AmortizacionPage'))
const ReportesPage = lazy(() => import('@/pages/ReportesPage'))
const VisualizacionBD = lazy(() => import('@/pages/VisualizacionBD'))
const Validadores = lazy(() => import('@/pages/Validadores'))
const Concesionarios = lazy(() => import('@/pages/Concesionarios'))
const ModelosVehiculos = lazy(() => import('@/pages/ModelosVehiculos'))
const Usuarios = lazy(() => import('@/pages/Usuarios'))
const Solicitudes = lazy(() => import('@/pages/Solicitudes'))

// Todas las páginas ahora están importadas desde archivos reales

const NotFound = () => (
  <div className="min-h-screen flex items-center justify-center">
    <div className="text-center">
      <h1 className="text-6xl font-bold text-gray-300 mb-4">404</h1>
      <h2 className="text-2xl font-semibold text-gray-700 mb-2">
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

function App() {
  const { isAuthenticated, initializeAuth } = useSimpleAuth()

  useEffect(() => {
    // Inicializar autenticación desde almacenamiento seguro CON VERIFICACIÓN AUTOMÁTICA
    initializeAuth()
  }, [initializeAuth])

  return (
    <AnimatePresence mode="wait">
      <Suspense fallback={<PageLoader />}>
        <Routes>
        {/* Ruta de login */}
        <Route
          path="/login"
          element={
            isAuthenticated ? (
              <Navigate to="/dashboard" replace />
            ) : (
              <motion.div
                key="login"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.3 }}
              >
                <Login />
              </motion.div>
            )
          }
        />

        {/* Rutas protegidas */}
        <Route
          path="/*"
          element={
            <SimpleProtectedRoute>
              <Layout />
            </SimpleProtectedRoute>
          }
        >
          {/* Dashboard */}
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />

          {/* Clientes */}
          <Route path="clientes" element={<Clientes />} />
          <Route path="clientes/nuevo" element={<Clientes />} />
          <Route path="clientes/:id" element={<Clientes />} />

          {/* Préstamos */}
          <Route
            path="prestamos"
            element={<PrestamosPage />}
          />

          {/* Pagos */}
          <Route path="pagos" element={<Pagos />} />
          <Route path="pagos/nuevo" element={<NuevoPago />} />
          <Route path="pagos/conciliacion" element={<ConciliacionBancaria />} />
          <Route path="pagos/:id" element={<Pagos />} />
          <Route path="pagos/:id/editar" element={<NuevoPago />} />

          {/* Amortización */}
          <Route path="amortizacion" element={<AmortizacionPage />} />

          {/* Conciliación */}

          {/* Reportes */}
          <Route
            path="reportes"
            element={<ReportesPage />}
          />


          {/* Aprobaciones */}
          <Route
            path="aprobaciones"
            element={<Aprobaciones />}
          />

          {/* Auditoría */}
          <Route
            path="auditoria"
            element={
              <SimpleProtectedRoute requireAdmin={true}>
                <Auditoria />
              </SimpleProtectedRoute>
            }
          />

          {/* Notificaciones */}
          <Route path="notificaciones" element={<Notificaciones />} />

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

          {/* Asesores */}
          <Route
            path="analistaes"
            element={
              <SimpleProtectedRoute requireAdmin={true}>
                <Analistas />
              </SimpleProtectedRoute>
            }
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

          {/* Auditoría */}
          <Route
            path="auditoria"
            element={
              <SimpleProtectedRoute requireAdmin={true}>
                <Auditoria />
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

          {/* 404 para rutas no encontradas */}
          <Route path="*" element={<NotFound />} />
        </Route>

        {/* Redirect root to dashboard if authenticated, login if not */}
        <Route
          path="/"
          element={
            isAuthenticated ? (
              <Navigate to="/dashboard" replace />
            ) : (
              <Navigate to="/login" replace />
            )
          }
        />
      </Routes>
      </Suspense>
    </AnimatePresence>
  )
}

export default App
