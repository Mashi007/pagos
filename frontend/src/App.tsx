import { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'

// Layout
import { Layout } from '@/components/layout/Layout'

// Auth
import { ProtectedRoute } from '@/components/auth/ProtectedRoute'
import { useAuth } from '@/store/authStore'

// Pages
import { Login } from '@/pages/Login'
import { Dashboard } from '@/pages/Dashboard'
import { Clientes } from '@/pages/Clientes'

// Placeholder components for other pages

const Pagos = () => (
  <div className="p-6">
    <h1 className="text-2xl font-bold mb-4">Gestión de Pagos</h1>
    <p className="text-gray-600">Módulo de pagos en desarrollo...</p>
  </div>
)

const Amortizacion = () => (
  <div className="p-6">
    <h1 className="text-2xl font-bold mb-4">Tabla de Amortización</h1>
    <p className="text-gray-600">Módulo de amortización en desarrollo...</p>
  </div>
)

const Conciliacion = () => (
  <div className="p-6">
    <h1 className="text-2xl font-bold mb-4">Conciliación Bancaria</h1>
    <p className="text-gray-600">Módulo de conciliación en desarrollo...</p>
  </div>
)

const Reportes = () => (
  <div className="p-6">
    <h1 className="text-2xl font-bold mb-4">Reportes</h1>
    <p className="text-gray-600">Módulo de reportes en desarrollo...</p>
  </div>
)

const KPIs = () => (
  <div className="p-6">
    <h1 className="text-2xl font-bold mb-4">KPIs y Métricas</h1>
    <p className="text-gray-600">Módulo de KPIs en desarrollo...</p>
  </div>
)

const Configuracion = () => (
  <div className="p-6">
    <h1 className="text-2xl font-bold mb-4">Configuración</h1>
    <p className="text-gray-600">Módulo de configuración en desarrollo...</p>
  </div>
)

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

function App() {
  const { isAuthenticated, refreshUser } = useAuth()

  useEffect(() => {
    // Verificar autenticación al cargar la app
    if (localStorage.getItem('access_token') && !isAuthenticated) {
      refreshUser()
    }
  }, [isAuthenticated, refreshUser])

  return (
    <AnimatePresence mode="wait">
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
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
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
            element={
              <ProtectedRoute requiredRoles={['ADMIN', 'GERENTE', 'ASESOR_COMERCIAL']}>
                <div className="p-6">
                  <h1 className="text-2xl font-bold mb-4">Gestión de Préstamos</h1>
                  <p className="text-gray-600">Módulo de préstamos en desarrollo...</p>
                </div>
              </ProtectedRoute>
            }
          />

          {/* Pagos */}
          <Route path="pagos" element={<Pagos />} />
          <Route path="pagos/nuevo" element={<Pagos />} />

          {/* Amortización */}
          <Route path="amortizacion" element={<Amortizacion />} />

          {/* Conciliación */}
          <Route
            path="conciliacion"
            element={
              <ProtectedRoute requiredRoles={['ADMIN', 'GERENTE', 'CONTADOR']}>
                <Conciliacion />
              </ProtectedRoute>
            }
          />

          {/* Reportes */}
          <Route
            path="reportes"
            element={
              <ProtectedRoute requiredRoles={['ADMIN', 'GERENTE', 'DIRECTOR', 'CONTADOR', 'AUDITOR']}>
                <Reportes />
              </ProtectedRoute>
            }
          />

          {/* KPIs */}
          <Route
            path="kpis"
            element={
              <ProtectedRoute requiredRoles={['ADMIN', 'GERENTE', 'DIRECTOR']}>
                <KPIs />
              </ProtectedRoute>
            }
          />

          {/* Aprobaciones */}
          <Route
            path="aprobaciones"
            element={
              <ProtectedRoute requiredRoles={['ADMIN', 'GERENTE', 'DIRECTOR']}>
                <div className="p-6">
                  <h1 className="text-2xl font-bold mb-4">Sistema de Aprobaciones</h1>
                  <p className="text-gray-600">Módulo de aprobaciones en desarrollo...</p>
                </div>
              </ProtectedRoute>
            }
          />

          {/* Auditoría */}
          <Route
            path="auditoria"
            element={
              <ProtectedRoute requiredRoles={['ADMIN', 'GERENTE', 'AUDITOR']}>
                <div className="p-6">
                  <h1 className="text-2xl font-bold mb-4">Auditoría</h1>
                  <p className="text-gray-600">Módulo de auditoría en desarrollo...</p>
                </div>
              </ProtectedRoute>
            }
          />

          {/* Carga Masiva */}
          <Route
            path="carga-masiva"
            element={
              <ProtectedRoute requiredRoles={['ADMIN', 'GERENTE']}>
                <div className="p-6">
                  <h1 className="text-2xl font-bold mb-4">Carga Masiva</h1>
                  <p className="text-gray-600">Módulo de carga masiva en desarrollo...</p>
                </div>
              </ProtectedRoute>
            }
          />

          {/* Inteligencia Artificial */}
          <Route
            path="ia"
            element={
              <ProtectedRoute requiredRoles={['ADMIN', 'GERENTE', 'DIRECTOR']}>
                <div className="p-6">
                  <h1 className="text-2xl font-bold mb-4">Inteligencia Artificial</h1>
                  <p className="text-gray-600">Módulo de IA en desarrollo...</p>
                </div>
              </ProtectedRoute>
            }
          />

          {/* Notificaciones */}
          <Route
            path="notificaciones"
            element={
              <div className="p-6">
                <h1 className="text-2xl font-bold mb-4">Notificaciones</h1>
                <p className="text-gray-600">Módulo de notificaciones en desarrollo...</p>
              </div>
            }
          />

          {/* Scheduler */}
          <Route
            path="scheduler"
            element={
              <ProtectedRoute requiredRoles={['ADMIN', 'GERENTE']}>
                <div className="p-6">
                  <h1 className="text-2xl font-bold mb-4">Programador de Tareas</h1>
                  <p className="text-gray-600">Módulo de scheduler en desarrollo...</p>
                </div>
              </ProtectedRoute>
            }
          />

          {/* Configuración */}
          <Route
            path="configuracion"
            element={
              <ProtectedRoute requiredRoles={['ADMIN', 'GERENTE']}>
                <Configuracion />
              </ProtectedRoute>
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
    </AnimatePresence>
  )
}

export default App
