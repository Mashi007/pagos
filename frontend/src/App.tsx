import React, { useEffect, Suspense } from 'react'

import { Routes, Route, Navigate, useLocation, Outlet } from 'react-router-dom'

import { motion, AnimatePresence } from 'framer-motion'

// Layout

import { Layout } from './components/layout/Layout'

// Auth

import { SimpleProtectedRoute } from './components/auth/SimpleProtectedRoute'

import { useSimpleAuth } from './store/simpleAuthStore'

import { getFiniquitoAccessToken } from './services/finiquitoService'

import { BASE_PATH } from './config/env'

import { RUTAS_REPORTE_PAGO_PUBLICO } from './constants/rutasIngresoPago'

/** Rutas que no requieren login: reporte de pago (un solo flujo, varias URLs), login e informes publicos. */

const PUBLIC_PATHS = [
  '/',
  '/login',
  '/acceso-limitado',
  ...RUTAS_REPORTE_PAGO_PUBLICO,
  '/rapicredit-estadocuenta',
]

/** En rutas pblicas solo muestra el Outlet (sin Layout). En el resto, si no hay token activo, redirige a /login





 * para pedir usuario y clave. Con basename="/pagos", pathname puede ser "/pagos/rapicredit-cobros"; normalizamos. */

function RootLayoutWrapper() {
  const location = useLocation()

  const { isAuthenticated, isLoading, user } = useSimpleAuth()

  let pathname = (location.pathname || '').replace(/\/$/, '') || '/'

  if (BASE_PATH && pathname.startsWith(BASE_PATH)) {
    const rest = pathname.slice(BASE_PATH.length)
    if (rest !== '' && rest !== '/') pathname = rest
  }

  const isPublic = PUBLIC_PATHS.some(p => pathname === p)

  if (isPublic) return <Outlet />

  // Si no está autenticado y NO está en una ruta pública: mostrar "Acceso limitado"
  // Esto previene que intenten acceder al dashboard quitando /infopagos de la URL

  if (!isLoading && !isAuthenticated) {
    return <Navigate to="/pagos/acceso-limitado" replace />
  }

  const esGestionFiniquito = pathname === '/finiquitos/gestion'

  const tokenPortalFiniquito = getFiniquitoAccessToken()?.trim()

  const esAdminPanel =
    isAuthenticated && (user?.rol || 'operativo') === 'administrador'

  if (esGestionFiniquito && !esAdminPanel) {
    if (tokenPortalFiniquito) {
      return <Outlet />
    }

    if (isLoading) {
      return (
        <div className="flex min-h-[100dvh] items-center justify-center bg-slate-100/80">
          <div
            className="h-10 w-10 animate-spin rounded-full border-2 border-slate-400 border-t-transparent"
            aria-label="Cargando"
            role="status"
          />
        </div>
      )
    }

    return <Navigate to="/finiquitos/acceso" replace />
  }

  // Sin token activo en ruta no pblica ? pedir usuario y clave (login)

  if (!isLoading && !isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  return (
    <SimpleProtectedRoute>
      <Layout />
    </SimpleProtectedRoute>
  )
}

// Constantes de configuracin

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

import EmbudoConcesionarios from './pages/EmbudoConcesionarios'

import RevisionManual from './pages/RevisionManual'

import Auditoria from './pages/Auditoria.tsx'

import EditarRevisionManual from './pages/EditarRevisionManual'

// Ventas: en pausa (ruta redirige a /pagos)

import ConversacionesWhatsAppPage from './pages/ConversacionesWhatsApp'

import ComunicacionesPage from './pages/Comunicaciones'

import ReportePagoPage from './pages/ReportePagoPage'

import InfopagosPage from './pages/InfopagosPage'

import EstadoCuentaPublicoPage from './pages/EstadoCuentaPublicoPage'

import { FiniquitoRootPage } from './pages/FiniquitoRootPage'

import { FiniquitoAccesoPage } from './pages/FiniquitoAccesoPage'

import { FiniquitoGestionGatePage } from './pages/FiniquitoGestionGatePage'

import CobrosPagosReportadosPage from './pages/CobrosPagosReportadosPage'

import CobrosDetallePage from './pages/CobrosDetallePage'

import CobrosEditarPage from './pages/CobrosEditarPage'

import CobrosHistoricoPage from './pages/CobrosHistoricoPage'

import { AdminTasaCambioPage } from './pages/AdminTasaCambioPage'

import AccesoLimitadoPage from './pages/AccesoLimitadoPage'

// Todas las pginas ahora estn importadas desde archivos reales

const NotFound = () => (
  <div className="flex min-h-screen items-center justify-center">
    <div className="text-center">
      <h1 className="mb-4 text-6xl font-bold text-gray-300">404</h1>

      <h2 className="mb-4 text-2xl font-semibold text-gray-700">
        Pgina no encontrada
      </h2>

      <p className="mb-6 text-gray-500">
        La pgina que buscas no existe o ha sido movida.
      </p>

      <button
        onClick={() => window.history.back()}
        className="rounded-lg bg-primary px-6 py-2 text-primary-foreground transition-colors hover:bg-primary/90"
      >
        Volver atrs
      </button>
    </div>
  </div>
)

// Componente de loading para Suspense

const PageLoader = () => (
  <div className="flex min-h-screen items-center justify-center">
    <div className="text-center">
      <div className="mx-auto mb-4 h-12 w-12 animate-spin rounded-full border-b-2 border-blue-600"></div>

      <p className="text-gray-600">Cargando pgina...</p>
    </div>
  </div>
)

// Una sola ejecucin de init auth por sesin (evita doble llamada en StrictMode

// y reduce "demasiadas llamadas a location/history" ? "The operation is insecure")

let _authInitDone = false

function App() {
  const location = useLocation()

  const { isAuthenticated, isLoading, initializeAuth } = useSimpleAuth()

  useEffect(() => {
    if (_authInitDone) return

    _authInitDone = true

    initializeAuth()
  }, [initializeAuth])

  // Mostrar loader solo si est cargando Y hay datos de auth (para evitar flash)

  let pathname = (location.pathname || '').replace(/\/$/, '') || '/'

  if (BASE_PATH && pathname.startsWith(BASE_PATH)) {
    const r = pathname.slice(BASE_PATH.length)
    pathname = r === '' ? '/' : r
  }

  const isPublicPath = PUBLIC_PATHS.some((p: string) => pathname === p)

  const colaboradorFiniquitoEnGestion =
    pathname === '/finiquitos/gestion' && !!getFiniquitoAccessToken()?.trim()

  if (isLoading && !isPublicPath && !colaboradorFiniquitoEnGestion) {
    return <PageLoader />
  }

  return (
    <AnimatePresence mode="wait">
      <Suspense fallback={<PageLoader />}>
        <Routes>
          {/* Una sola raz path="/" para que Layout reciba correctamente las rutas hijas (dashboard, clientes, etc.) */}

          <Route path="/" element={<RootLayoutWrapper />}>
            {/* Raz /pagos/ sin token ? pedir usuario y clave (login) */}

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

            {/* Formulario pblico de reporte de pago (sin login). Link cannico: /rapicredit-cobros */}

            <Route path="reporte-pago" element={<ReportePagoPage />} />

            <Route path="rapicredit-cobros" element={<ReportePagoPage />} />

            <Route
              path="rapicredit"
              element={<Navigate to="/rapicredit-cobros" replace />}
            />

            {/* Consulta pblica de estado de cuenta (sin login). Solo esta consulta, sin acceso a otros servicios. */}

            <Route
              path="rapicredit-estadocuenta"
              element={<EstadoCuentaPublicoPage />}
            />

            {/* Infopagos: formulario de ingreso de pagos para colaboradores (sin login) */}

            <Route path="infopagos" element={<InfopagosPage />} />

            {/* Acceso limitado: se muestra cuando alguien intenta acceder a /pagos desde /infopagos */}

            <Route path="acceso-limitado" element={<AccesoLimitadoPage />} />

            {/* Finiquito: portal OTP y gestion comparten URL /finiquitos/gestion (gate); panel redirige */}

            {/* Nota: Rutas de finiquitos han sido movidas a sección protegida (después de login) */}

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

            {/* Dashboard - ruta ms especfica primero */}

            <Route path="dashboard/menu" element={<DashboardMenu />} />

            <Route
              path="dashboard"
              element={<Navigate to="/dashboard/menu" replace />}
            />

            {/* Clientes */}

            <Route path="clientes" element={<Clientes />} />

            <Route path="clientes/nuevo" element={<Clientes />} />

            <Route path="clientes/:id" element={<Clientes />} />

            {/* Prstamos */}

            <Route path="prestamos" element={<Prestamos />} />

            {/* Pagos (URL: /pagos/pagos con basename /pagos) */}

            <Route path="pagos">
              <Route index element={<PagosPage />} />

              <Route path=":id" element={<PagosPage />} />
            </Route>

            {/* Amortizacin */}

            <Route path="amortizacion" element={<AmortizacionPage />} />

            {/* Conciliacin */}

            {/* Cobros (Pagos Reportados, Detalle, Histrico) */}

            <Route
              path="cobros/pagos-reportados"
              element={<CobrosPagosReportadosPage />}
            />

            <Route
              path="cobros/pagos-reportados/:id/editar"
              element={<CobrosEditarPage />}
            />

            <Route
              path="cobros/pagos-reportados/:id"
              element={<CobrosDetallePage />}
            />

            <Route
              path="cobros/historico-cliente"
              element={<CobrosHistoricoPage />}
            />

            {/* Informes: generador de estado de cuenta (requiere login) */}

            <Route path="informes" element={<EstadoCuentaPublicoPage />} />

            {/* Finiquitos: portal de finiquitos (requiere login) */}

            <Route path="finiquitos" element={<FiniquitoRootPage />} />

            <Route path="finiquitos/acceso" element={<FiniquitoAccesoPage />} />

            <Route
              path="finiquitos/panel"
              element={<Navigate to="/finiquitos/gestion" replace />}
            />

            <Route
              path="finiquitos/gestion"
              element={<FiniquitoGestionGatePage />}
            />

            {/* Reportes */}

            <Route path="reportes" element={<Reportes />} />

            {/* Revisin Manual de Prstamos */}

            <Route path="revision-manual" element={<RevisionManual />} />

            <Route
              path="revision-manual/editar/:prestamoId"
              element={<EditarRevisionManual />}
            />

            <Route path="auditoria" element={<Auditoria />} />

            {/* Notificaciones (dentro de CRM en sidebar) */}

            <Route path="notificaciones" element={<Notificaciones />} />

            {/* Redirecciones: plantillas viven en Configuracin */}

            <Route
              path="notificaciones/plantillas"
              element={<Navigate to="/configuracion?tab=plantillas" replace />}
            />

            <Route
              path="herramientas/notificaciones"
              element={<Navigate to="/notificaciones" replace />}
            />

            <Route
              path="herramientas/plantillas"
              element={<Navigate to="/configuracion?tab=plantillas" replace />}
            />

            {/* Comunicaciones (Unificado WhatsApp y Email) */}

            <Route path="comunicaciones" element={<ComunicacionesPage />} />

            {/* Conversaciones WhatsApp (Legacy - mantener por compatibilidad) */}

            <Route
              path="conversaciones-whatsapp"
              element={<ConversacionesWhatsAppPage />}
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

            {/* Configuracin */}

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

            {/* Modelos de Vehculos */}

            <Route
              path="modelos-vehiculos"
              element={
                <SimpleProtectedRoute requireAdmin={true}>
                  <ModelosVehiculos />
                </SimpleProtectedRoute>
              }
            />

            {/* Chat AI  accesible por cualquier usuario autenticado (no solo admin) */}

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

            {/* CRM campañas y tickets: ocultos - redirigen a clientes */}

            <Route
              path="crm/tickets"
              element={<Navigate to="/clientes" replace />}
            />

            <Route
              path="crm/campanas"
              element={<Navigate to="/clientes" replace />}
            />

            <Route
              path="crm/embudo-concesionarios"
              element={<EmbudoConcesionarios />}
            />

            {/* 404 para rutas no encontradas */}

            <Route path="*" element={<NotFound />} />
          </Route>

          <Route path="/admin/tasas-cambio" element={<AdminTasaCambioPage />} />
        </Routes>
      </Suspense>
    </AnimatePresence>
  )
}

export default App
