/**
 * Pruebas unitarias de componentes (smoke + contratos básicos con la UI actual).
 */
import type { ReactElement } from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter, MemoryRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import { CrearClienteForm } from '@/components/clientes/CrearClienteForm'
import { ClientesList } from '@/components/clientes/ClientesList'
import { LoginForm } from '@/components/auth/LoginForm'
import { Sidebar } from '@/components/layout/Sidebar'
import { Header } from '@/components/layout/Header'
import { Footer } from '@/components/layout/Footer'

const authMock = vi.hoisted(() => ({
  user: null as Record<string, unknown> | null,
  login: vi.fn(),
  logout: vi.fn(),
  isLoading: false,
  error: null as string | null,
  clearError: vi.fn(),
  isAuthenticated: false,
  initializeAuth: vi.fn(),
  refreshUser: vi.fn().mockResolvedValue(undefined),
}))

vi.mock('@/store/simpleAuthStore', () => ({
  useSimpleAuth: () => authMock,
}))

vi.mock('@/hooks/useSidebarCounts', () => ({
  useSidebarCounts: () => ({
    counts: {
      pagosPendientes: 0,
      cuotasEnMora: 0,
      notificacionesNoLeidas: 0,
    },
    loading: false,
  }),
}))

vi.mock('@/services/validadoresService', () => ({
  validadoresService: {
    validarCampo: vi.fn().mockResolvedValue({
      validacion: { valido: true, mensaje: 'Campo válido' },
    }),
  },
}))

vi.mock('@/services/clienteService', () => ({
  clienteService: {
    getClientes: vi.fn(),
    getEstadosCliente: vi.fn().mockResolvedValue({
      estados: [{ valor: 'ACTIVO', etiqueta: 'Activo', orden: 1 }],
    }),
    getStats: vi.fn().mockResolvedValue({
      total: 0,
      activos: 0,
      inactivos: 0,
      finalizados: 0,
      nuevos_este_mes: 0,
      ultima_actualizacion: null,
    }),
    getCliente: vi.fn(),
    createCliente: vi.fn(),
    createClienteWithConfirmation: vi.fn(),
    updateCliente: vi.fn(),
    deleteCliente: vi.fn(),
    getClientesConErrores: vi.fn().mockResolvedValue({ items: [], total: 0 }),
  },
}))

vi.mock('@/services/authService', () => ({
  authService: {
    login: vi.fn(),
    logout: vi.fn(),
    getCurrentUser: vi.fn(),
  },
}))

function renderWithRouter(ui: ReactElement) {
  return render(<BrowserRouter>{ui}</BrowserRouter>)
}

function renderWithQuery(ui: ReactElement) {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  })
  return render(
    <QueryClientProvider client={client}>
      <BrowserRouter>{ui}</BrowserRouter>
    </QueryClientProvider>
  )
}

const usuarioManager = {
  id: 1,
  email: 'gerente@example.com',
  nombre: 'Gema',
  apellido: 'Gerente',
  rol: 'gerente',
  is_active: true,
}

const usuarioAdmin = {
  id: 2,
  email: 'admin@example.com',
  nombre: 'Ada',
  apellido: 'Admin',
  rol: 'administrador',
  is_active: true,
}

const usuarioViewer = {
  id: 3,
  email: 'op@example.com',
  nombre: 'Ope',
  apellido: 'Viewer',
  rol: 'operativo',
  is_active: true,
}

describe('CrearClienteForm', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    authMock.user = {
      email: 'test@example.com',
      id: 1,
      nombre: 'Test',
      apellido: 'User',
      rol: 'gerente',
      is_active: true,
    }
  })

  it('renderiza título y acciones del formulario nuevo cliente', () => {
    renderWithQuery(
      <CrearClienteForm onClose={() => {}} onSuccess={() => {}} />
    )

    expect(
      screen.getByRole('heading', { name: /nuevo cliente/i })
    ).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /guardar cliente/i })
    ).toBeInTheDocument()
    expect(screen.getByText(/cédula/i)).toBeInTheDocument()
  })

  it('el botón Guardar Cliente está deshabilitado con formulario vacío', () => {
    renderWithQuery(
      <CrearClienteForm onClose={() => {}} onSuccess={() => {}} />
    )

    expect(
      screen.getByRole('button', { name: /guardar cliente/i })
    ).toBeDisabled()
  })
})

describe('ClientesList', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    authMock.user = usuarioManager
  })

  it('muestra nombres de clientes cuando la API devuelve datos', async () => {
    const { clienteService } = await import('@/services/clienteService')
    vi.mocked(clienteService.getClientes).mockResolvedValue({
      data: [
        {
          id: 1,
          cedula: 'V12345678',
          nombres: 'Juan Pérez',
          email: 'juan@example.com',
          telefono: '+58412123456',
          estado: 'ACTIVO',
        },
      ],
      total: 1,
      page: 1,
      per_page: 20,
      total_pages: 1,
    })

    renderWithQuery(<ClientesList />)

    await waitFor(() => {
      expect(screen.getByText('Juan Pérez')).toBeInTheDocument()
    })
  })

  it('muestra mensaje cuando no hay clientes', async () => {
    const { clienteService } = await import('@/services/clienteService')
    vi.mocked(clienteService.getClientes).mockResolvedValue({
      data: [],
      total: 0,
      page: 1,
      per_page: 20,
      total_pages: 0,
    })

    renderWithQuery(<ClientesList />)

    await waitFor(() => {
      expect(
        screen.getByText(/no hay clientes que coincidan con los filtros/i)
      ).toBeInTheDocument()
    })
  })

  it('actualiza la búsqueda al escribir en el campo Buscar', async () => {
    const user = userEvent.setup()
    const { clienteService } = await import('@/services/clienteService')
    vi.mocked(clienteService.getClientes).mockResolvedValue({
      data: [],
      total: 0,
      page: 1,
      per_page: 20,
      total_pages: 0,
    })

    renderWithQuery(<ClientesList />)

    const searchInput = await screen.findByPlaceholderText(
      /buscar por cédula o nombres/i
    )
    await user.type(searchInput, 'Juan')

    await waitFor(
      () => {
        const calls = vi.mocked(clienteService.getClientes).mock.calls
        const last = calls[calls.length - 1]
        expect(last[0]).toMatchObject({ search: 'Juan' })
      },
      { timeout: 5000 }
    )
  })
})

describe('LoginForm', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    authMock.user = null
    authMock.error = null
    authMock.login.mockReset()
    authMock.clearError.mockReset()
  })

  it('renderiza correo, contraseña e iniciar sesión', () => {
    renderWithRouter(<LoginForm />)

    expect(screen.getByLabelText(/correo electrónico/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/^contraseña$/i)).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /iniciar sesión/i })
    ).toBeInTheDocument()
  })

  it('muestra errores de validación al enviar vacío', async () => {
    const user = userEvent.setup()
    renderWithRouter(<LoginForm />)

    await user.click(screen.getByRole('button', { name: /iniciar sesión/i }))

    await waitFor(() => {
      expect(screen.getByText(/el email es requerido/i)).toBeInTheDocument()
      expect(
        screen.getByText(/la contraseña es requerida/i)
      ).toBeInTheDocument()
    })
  })

  it('envía credenciales al store al enviar formulario válido', async () => {
    const user = userEvent.setup()
    authMock.login.mockResolvedValue(undefined)

    renderWithRouter(<LoginForm />)

    await user.type(
      screen.getByLabelText(/correo electrónico/i),
      'test@example.com'
    )
    await user.type(screen.getByLabelText(/^contraseña$/i), 'password123')
    await user.click(screen.getByRole('button', { name: /iniciar sesión/i }))

    await waitFor(() => {
      expect(authMock.login).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'password123',
        remember: true,
      })
    })
  })

  it('muestra mensaje del backend en 401', async () => {
    const user = userEvent.setup()
    authMock.login.mockRejectedValue({
      isAxiosError: true,
      response: {
        status: 401,
        data: { detail: 'Email o contraseña incorrectos' },
      },
    })

    renderWithRouter(<LoginForm />)

    await user.type(
      screen.getByLabelText(/correo electrónico/i),
      'bad@example.com'
    )
    await user.type(screen.getByLabelText(/^contraseña$/i), 'wrongpw')
    await user.click(screen.getByRole('button', { name: /iniciar sesión/i }))

    await waitFor(() => {
      expect(
        screen.getByText(/email o contraseña incorrectos/i)
      ).toBeInTheDocument()
    })
  })
})

describe('Sidebar', () => {
  const noop = () => {}

  function renderSidebarAt(path: string) {
    return render(
      <MemoryRouter initialEntries={[path]}>
        <Sidebar isOpen={true} onClose={noop} onToggle={noop} />
      </MemoryRouter>
    )
  }

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('muestra Clientes y Préstamos para rol gerente', async () => {
    authMock.user = usuarioManager
    renderSidebarAt('/clientes')

    expect(
      await screen.findByRole('link', { name: /^clientes$/i })
    ).toBeInTheDocument()
    expect(
      screen.getByRole('link', { name: /^préstamos$/i })
    ).toBeInTheDocument()
  })

  it('muestra Usuarios para administrador', async () => {
    authMock.user = usuarioAdmin
    renderSidebarAt('/usuarios')

    expect(
      await screen.findByRole('link', { name: /^usuarios$/i })
    ).toBeInTheDocument()
  })

  it('no muestra Usuarios para rol operativo (viewer)', () => {
    authMock.user = usuarioViewer
    renderSidebarAt('/reportes')

    expect(
      screen.queryByRole('link', { name: /^usuarios$/i })
    ).not.toBeInTheDocument()
  })
})

describe('Header', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    authMock.user = {
      id: 1,
      email: 'test@example.com',
      nombre: 'Test',
      apellido: 'User',
      rol: 'operativo',
      is_active: true,
    }
    authMock.logout.mockResolvedValue(undefined)
  })

  it('muestra marca y nombre de usuario', () => {
    renderWithRouter(<Header onMenuClick={() => {}} isSidebarOpen={false} />)

    expect(screen.getByText(/rapicredit/i)).toBeInTheDocument()
    expect(screen.getByText(/test user/i)).toBeInTheDocument()
  })

  it('muestra Cerrar sesión al abrir el menú de usuario', async () => {
    const user = userEvent.setup()
    renderWithRouter(<Header onMenuClick={() => {}} isSidebarOpen={false} />)

    await user.click(screen.getByRole('button', { name: /test user/i }))

    expect(
      screen.getByRole('button', { name: /cerrar sesión/i })
    ).toBeInTheDocument()
  })
})

describe('Footer', () => {
  it('muestra copyright con año actual y RAPICREDIT', () => {
    const y = new Date().getFullYear()
    renderWithRouter(<Footer />)

    expect(
      screen.getByText(new RegExp(String.raw`\u00A9\s*${y}`))
    ).toBeInTheDocument()
    expect(screen.getByText(/rapicredit/i)).toBeInTheDocument()
  })
})
