/**
 * Pruebas Unitarias - Componentes
 * Testing de componentes React individuales
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'

// Componentes a probar
import { CrearClienteForm } from '@/components/clientes/CrearClienteForm'
import { ClientesList } from '@/components/clientes/ClientesList'
import { LoginForm } from '@/components/auth/LoginForm'
import { Sidebar } from '@/components/layout/Sidebar'
import { Header } from '@/components/layout/Header'
import { Footer } from '@/components/layout/Footer'

// Mocks
vi.mock('@/services/clienteService', () => ({
  clienteService: {
    createCliente: vi.fn(),
    createClienteWithConfirmation: vi.fn(),
    getClientes: vi.fn(),
    updateCliente: vi.fn(),
    deleteCliente: vi.fn(),
  }
}))

vi.mock('@/services/authService', () => ({
  authService: {
    login: vi.fn(),
    logout: vi.fn(),
    getCurrentUser: vi.fn(),
  }
}))

// Helper para renderizar con router
const renderWithRouter = (component: React.ReactElement) => {
  return render(
    <BrowserRouter>
      {component}
    </BrowserRouter>
  )
}

describe('CrearClienteForm', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('deberÃ­a renderizar el formulario correctamente', () => {
    renderWithRouter(<CrearClienteForm />)

    expect(screen.getByLabelText(/cÃ©dula/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/nombres/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/apellidos/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/telÃ©fono/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /guardar/i })).toBeInTheDocument()
  })

  it('deberÃ­a mostrar errores de validaciÃ³n', async () => {
    const user = userEvent.setup()
    renderWithRouter(<CrearClienteForm />)

    const submitButton = screen.getByRole('button', { name: /guardar/i })
    await user.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText(/cÃ©dula es requerida/i)).toBeInTheDocument()
      expect(screen.getByText(/nombres son requeridos/i)).toBeInTheDocument()
    })
  })

  it('deberÃ­a enviar el formulario con datos vÃ¡lidos', async () => {
    const user = userEvent.setup()
    const mockCreateCliente = vi.fn().mockResolvedValue({ id: 1 })

    // Mock del servicio
    const { clienteService } = await import('@/services/clienteService')
    clienteService.createCliente = mockCreateCliente

    renderWithRouter(<CrearClienteForm />)

    // Llenar formulario
    await user.type(screen.getByLabelText(/cÃ©dula/i), 'V12345678')
    await user.type(screen.getByLabelText(/nombres/i), 'Juan')
    await user.type(screen.getByLabelText(/apellidos/i), 'PÃ©rez')
    await user.type(screen.getByLabelText(/telÃ©fono/i), '+58412123456')
    await user.type(screen.getByLabelText(/email/i), 'juan@example.com')

    // Enviar formulario
    const submitButton = screen.getByRole('button', { name: /guardar/i })
    await user.click(submitButton)

    await waitFor(() => {
      expect(mockCreateCliente).toHaveBeenCalledWith({
        cedula: 'V12345678',
        nombres: 'Juan',
        apellidos: 'PÃ©rez',
        telefono: '+58412123456',
        email: 'juan@example.com',
        direccion: '',
        fecha_nacimiento: '',
        ocupacion: '',
        modelo_vehiculo: '',
        concesionario: '',
        analista: '',
        estado: 'ACTIVO',
        notas: ''
      })
    })
  })

  it('deberÃ­a mostrar popup de confirmaciÃ³n para cÃ©dula duplicada', async () => {
    const user = userEvent.setup()
    const mockCreateCliente = vi.fn().mockRejectedValue({
      response: {
        status: 503,
        data: {
          detail: 'duplicate key value violates unique constraint - cÃ©dula V12345678 already exists'
        }
      }
    })

    const { clienteService } = await import('@/services/clienteService')
    clienteService.createCliente = mockCreateCliente

    renderWithRouter(<CrearClienteForm />)

    // Llenar formulario
    await user.type(screen.getByLabelText(/cÃ©dula/i), 'V12345678')
    await user.type(screen.getByLabelText(/nombres/i), 'Juan')
    await user.type(screen.getByLabelText(/apellidos/i), 'PÃ©rez')

    // Enviar formulario
    const submitButton = screen.getByRole('button', { name: /guardar/i })
    await user.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText(/cÃ©dula duplicada/i)).toBeInTheDocument()
      expect(screen.getByText(/Â¿desea continuar/i)).toBeInTheDocument()
    })
  })
})

describe('ClientesList', () => {
  const mockClientes = [
    {
      id: 1,
      cedula: 'V12345678',
      nombres: 'Juan',
      apellidos: 'PÃ©rez',
      telefono: '+58412123456',
      email: 'juan@example.com',
      estado: 'ACTIVO'
    },
    {
      id: 2,
      cedula: 'V87654321',
      nombres: 'MarÃ­a',
      apellidos: 'GonzÃ¡lez',
      telefono: '+58412987654',
      email: 'maria@example.com',
      estado: 'ACTIVO'
    }
  ]

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('deberÃ­a renderizar la lista de clientes', async () => {
    const mockGetClientes = vi.fn().mockResolvedValue({
      data: mockClientes,
      total: 2,
      page: 1,
      per_page: 20
    })

    const { clienteService } = await import('@/services/clienteService')
    clienteService.getClientes = mockGetClientes

    renderWithRouter(<ClientesList />)

    await waitFor(() => {
      expect(screen.getByText('Juan PÃ©rez')).toBeInTheDocument()
      expect(screen.getByText('MarÃ­a GonzÃ¡lez')).toBeInTheDocument()
    })
  })

  it('deberÃ­a mostrar mensaje cuando no hay clientes', async () => {
    const mockGetClientes = vi.fn().mockResolvedValue({
      data: [],
      total: 0,
      page: 1,
      per_page: 20
    })

    const { clienteService } = await import('@/services/clienteService')
    clienteService.getClientes = mockGetClientes

    renderWithRouter(<ClientesList />)

    await waitFor(() => {
      expect(screen.getByText(/no hay clientes/i)).toBeInTheDocument()
    })
  })

  it('deberÃ­a filtrar clientes por bÃºsqueda', async () => {
    const user = userEvent.setup()
    const mockGetClientes = vi.fn().mockResolvedValue({
      data: mockClientes,
      total: 2,
      page: 1,
      per_page: 20
    })

    const { clienteService } = await import('@/services/clienteService')
    clienteService.getClientes = mockGetClientes

    renderWithRouter(<ClientesList />)

    const searchInput = screen.getByPlaceholderText(/buscar/i)
    await user.type(searchInput, 'Juan')

    await waitFor(() => {
      expect(mockGetClientes).toHaveBeenCalledWith({
        search: 'Juan',
        page: 1,
        per_page: 20
      })
    })
  })
})

describe('LoginForm', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('deberÃ­a renderizar el formulario de login', () => {
    renderWithRouter(<LoginForm />)

    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/contraseÃ±a/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /iniciar sesiÃ³n/i })).toBeInTheDocument()
  })

  it('deberÃ­a mostrar errores de validaciÃ³n', async () => {
    const user = userEvent.setup()
    renderWithRouter(<LoginForm />)

    const submitButton = screen.getByRole('button', { name: /iniciar sesiÃ³n/i })
    await user.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText(/email es requerido/i)).toBeInTheDocument()
      expect(screen.getByText(/contraseÃ±a es requerida/i)).toBeInTheDocument()
    })
  })

  it('deberÃ­a enviar credenciales vÃ¡lidas', async () => {
    const user = userEvent.setup()
    const mockLogin = vi.fn().mockResolvedValue({
      access_token: 'mock-token',
      token_type: 'bearer'
    })

    const { authService } = await import('@/services/authService')
    authService.login = mockLogin

    renderWithRouter(<LoginForm />)

    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.type(screen.getByLabelText(/contraseÃ±a/i), 'password123')

    const submitButton = screen.getByRole('button', { name: /iniciar sesiÃ³n/i })
    await user.click(submitButton)

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'password123'
      })
    })
  })

  it('deberÃ­a mostrar error de credenciales invÃ¡lidas', async () => {
    const user = userEvent.setup()
    const mockLogin = vi.fn().mockRejectedValue({
      response: {
        status: 401,
        data: {
          detail: 'Email o contraseÃ±a incorrectos'
        }
      }
    })

    const { authService } = await import('@/services/authService')
    authService.login = mockLogin

    renderWithRouter(<LoginForm />)

    await user.type(screen.getByLabelText(/email/i), 'invalid@example.com')
    await user.type(screen.getByLabelText(/contraseÃ±a/i), 'wrongpassword')

    const submitButton = screen.getByRole('button', { name: /iniciar sesiÃ³n/i })
    await user.click(submitButton)

    await waitFor(() => {
      expect(screen.getByText(/credenciales incorrectas/i)).toBeInTheDocument()
    })
  })
})

describe('Sidebar', () => {
  const mockUser = {
    id: 1,
    email: 'test@example.com',
    nombre: 'Test',
    apellido: 'User',
    rol: 'operativo',
    is_active: true
  }

  it('deberÃ­a renderizar el sidebar correctamente', () => {
    renderWithRouter(<Sidebar user={mockUser} />)

    expect(screen.getByText(/clientes/i)).toBeInTheDocument()
    expect(screen.getByText(/prÃ©stamos/i)).toBeInTheDocument()
    expect(screen.getByText(/pagos/i)).toBeInTheDocument()
  })

  it('deberÃ­a mostrar opciones de admin para usuarios admin', () => {
    const adminUser = { ...mockUser, rol: 'administrador' as const }
    renderWithRouter(<Sidebar user={adminUser} />)

    expect(screen.getByText(/configuraciÃ³n/i)).toBeInTheDocument()
    expect(screen.getByText(/usuarios/i)).toBeInTheDocument()
  })

  it('deberÃ­a ocultar opciones de admin para usuarios normales', () => {
    renderWithRouter(<Sidebar user={mockUser} />)

    expect(screen.queryByText(/configuraciÃ³n/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/usuarios/i)).not.toBeInTheDocument()
  })
})

describe('Header', () => {
  const mockUser = {
    id: 1,
    email: 'test@example.com',
    nombre: 'Test',
    apellido: 'User',
    rol: 'operativo',
    is_active: true
  }

  it('deberÃ­a renderizar el header correctamente', () => {
    renderWithRouter(<Header user={mockUser} />)

    expect(screen.getByText(/sistema de prÃ©stamos/i)).toBeInTheDocument()
    expect(screen.getByText(/test user/i)).toBeInTheDocument()
  })

  it('deberÃ­a mostrar botÃ³n de logout', () => {
    renderWithRouter(<Header user={mockUser} />)

    expect(screen.getByRole('button', { name: /cerrar sesiÃ³n/i })).toBeInTheDocument()
  })
})

describe('Footer', () => {
  it('deberÃ­a renderizar el footer correctamente', () => {
    renderWithRouter(<Footer />)

    expect(screen.getByText(/Â© 2025/i)).toBeInTheDocument()
    expect(screen.getByText(/rapicredit/i)).toBeInTheDocument()
  })
})
