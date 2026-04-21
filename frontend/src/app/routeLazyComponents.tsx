/**
 * Rutas cargadas bajo demanda (code-splitting) para reducir JS inicial.
 * Login y páginas mínimas del shell siguen import estático en App.tsx.
 */
import { lazy } from 'react'

export const PublicBasenameIndexPage = lazy(() =>
  import('../pages/PublicBasenameIndexPage').then(m => ({
    default: m.PublicBasenameIndexPage,
  }))
)

export const ReportePagoPage = lazy(() => import('../pages/ReportePagoPage'))

export const EstadoCuentaPublicoPage = lazy(
  () => import('../pages/EstadoCuentaPublicoPage')
)

export const AccesoLimitadoPage = lazy(() => import('../pages/AccesoLimitadoPage'))

export const DashboardMenu = lazy(() => import('../pages/DashboardMenu'))

export const Clientes = lazy(() => import('../pages/Clientes'))

export const Prestamos = lazy(() => import('../pages/Prestamos'))

export const FiniquitoRootPage = lazy(() =>
  import('../pages/FiniquitoRootPage').then(m => ({
    default: m.FiniquitoRootPage,
  }))
)

export const FiniquitoAccesoPage = lazy(() =>
  import('../pages/FiniquitoAccesoPage').then(m => ({
    default: m.FiniquitoAccesoPage,
  }))
)

export const FiniquitoGestionGatePage = lazy(() =>
  import('../pages/FiniquitoGestionGatePage').then(m => ({
    default: m.FiniquitoGestionGatePage,
  }))
)

export const PagosPage = lazy(() => import('../pages/PagosPage'))

export const PagoBsPage = lazy(() => import('../pages/PagoBsPage'))

export const TasaCambioPage = lazy(() => import('../pages/TasaCambioPage'))

export const InfopagosPage = lazy(() => import('../pages/InfopagosPage'))

export const EscanerInfopagosPage = lazy(() => import('../pages/EscanerInfopagosPage'))

export const EscanerInfopagosLotePage = lazy(() => import('../pages/EscanerInfopagosLotePage'))

export const AmortizacionPage = lazy(() => import('../pages/AmortizacionPage'))

export const CobrosPagosReportadosPage = lazy(
  () => import('../pages/CobrosPagosReportadosPage')
)

export const CobrosEditarPage = lazy(() => import('../pages/CobrosEditarPage'))

export const CobrosDetallePage = lazy(() => import('../pages/CobrosDetallePage'))

export const CobrosHistoricoPage = lazy(() => import('../pages/CobrosHistoricoPage'))

export const Reportes = lazy(() => import('../pages/Reportes'))

export const RevisionManual = lazy(() => import('../pages/RevisionManual'))

export const EditarRevisionManual = lazy(() => import('../pages/EditarRevisionManual'))

export const Auditoria = lazy(() => import('../pages/Auditoria'))

export const Notificaciones = lazy(() => import('../pages/Notificaciones'))

export const NotificacionesClientesDrive = lazy(
  () => import('../pages/NotificacionesClientesDrive')
)

export const NotificacionesRecibosPage = lazy(
  () => import('../pages/NotificacionesRecibosPage')
)

export const ActualizacionesPrestamosDrivePage = lazy(
  () => import('../pages/ActualizacionesPrestamosDrivePage')
)

export const ActualizacionesFechas2Page = lazy(
  () => import('../pages/ActualizacionesFechas2Page')
)

export const FechaQAuditoriaTotalPage = lazy(
  () => import('../pages/FechaQAuditoriaTotalPage')
)

export const ComunicacionesPage = lazy(() => import('../pages/Comunicaciones'))

export const ConversacionesWhatsAppPage = lazy(
  () => import('../pages/ConversacionesWhatsApp')
)

export const Programador = lazy(() => import('../pages/Programador'))

export const Configuracion = lazy(() => import('../pages/Configuracion'))

export const Analistas = lazy(() => import('../pages/Analistas'))

export const Validadores = lazy(() => import('../pages/Validadores'))

export const Concesionarios = lazy(() => import('../pages/Concesionarios'))

export const ModelosVehiculos = lazy(() => import('../pages/ModelosVehiculos'))

export const ChatAI = lazy(() => import('../pages/ChatAI'))

export const Usuarios = lazy(() => import('../pages/Usuarios'))

export const Solicitudes = lazy(() => import('../pages/Solicitudes'))

export const EmbudoClientes = lazy(() => import('../pages/EmbudoClientes'))

export const EmbudoConcesionarios = lazy(() => import('../pages/EmbudoConcesionarios'))

export const AdminTasaCambioPage = lazy(() =>
  import('../pages/AdminTasaCambioPage').then(m => ({
    default: m.AdminTasaCambioPage,
  }))
)
