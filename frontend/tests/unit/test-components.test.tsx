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

  it('debería renderizar el formulario correctamente', () => {
    renderWithRouter(<CrearClienteForm />)
    
    expect(screen.getByLabelText(/cédula/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/nombres/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/apellidos/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/teléfono/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /guardar/i })).toBeInTheDocument()
  })

  it('debería mostrar errores de validación', async () => {
    const user = userEvent.setup()
    renderWithRouter(<CrearClienteForm />)
    
    const submitButton = screen.getByRole('button', { name: /guardar/i })
    await user.click(submitButton)
    
    await waitFor(() => {
      expect(screen.getByText(/cédula es requerida/i)).toBeInTheDocument()
      expect(screen.getByText(/nombres son requeridos/i)).toBeInTheDocument()
    })
  })

  it('debería enviar el formulario con datos válidos', async () => {
    const user = userEvent.setup()
    const mockCreateCliente = vi.fn().mockResolvedValue({ id: 1 })
    
    // Mock del servicio
    const { clienteService } = await import('@/services/clienteService')
    clienteService.createCliente = mockCreateCliente
    
    renderWithRouter(<CrearClienteForm />)
    
    // Llenar formulario
    await user.type(screen.getByLabelText(/cédula/i), 'V12345678')
    await user.type(screen.getByLabelText(/nombres/i), 'Juan')
    await user.type(screen.getByLabelText(/apellidos/i), 'Pérez')
    await user.type(screen.getByLabelText(/teléfono/i), '+58412123456')
    await user.type(screen.getByLabelText(/email/i), 'juan@example.com')
    
    // Enviar formulario
    const submitButton = screen.getByRole('button', { name: /guardar/i })
    await user.click(submitButton)
    
    await waitFor(() => {
      expect(mockCreateCliente).toHaveBeenCalledWith({
        cedula: 'V12345678',
        nombres: 'Juan',
        apellidos: 'Pérez',
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

  it('debería mostrar popup de confirmación para cédula duplicada', async () => {
    const user = userEvent.setup()
    const mockCreateCliente = vi.fn().mockRejectedValue({
      response: {
        status: 503,
        data: {
          detail: 'duplicate key value violates unique constraint - cédula V12345678 already exists'
        }
      }
    })
    
    const { clienteService } = await import('@/services/clienteService')
    clienteService.createCliente = mockCreateCliente
    
    renderWithRouter(<CrearClienteForm />)
    
    // Llenar formulario
    await user.type(screen.getByLabelText(/cédula/i), 'V12345678')
    await user.type(screen.getByLabelText(/nombres/i), 'Juan')
    await user.type(screen.getByLabelText(/apellidos/i), 'Pérez')
    
    // Enviar formulario
    const submitButton = screen.getByRole('button', { name: /guardar/i })
    await user.click(submitButton)
    
    await waitFor(() => {
      expect(screen.getByText(/cédula duplicada/i)).toBeInTheDocument()
      expect(screen.getByText(/¿desea continuar/i)).toBeInTheDocument()
    })
  })
})

describe('ClientesList', () => {
  const mockClientes = [
    {
      id: 1,
      cedula: 'V12345678',
      nombres: 'Juan',
      apellidos: 'Pérez',
      telefono: '+58412123456',
      email: 'juan@example.com',
      estado: 'ACTIVO'
    },
    {
      id: 2,
      cedula: 'V87654321',
      nombres: 'María',
      apellidos: 'González',
      telefono: '+58412987654',
      email: 'maria@example.com',
      estado: 'ACTIVO'
    }
  ]

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('debería renderizar la lista de clientes', async () => {
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
      expect(screen.getByText('Juan Pérez')).toBeInTheDocument()
      expect(screen.getByText('María González')).toBeInTheDocument()
    })
  })

  it('debería mostrar mensaje cuando no hay clientes', async () => {
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

  it('debería filtrar clientes por búsqueda', async () => {
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

  it('debería renderizar el formulario de login', () => {
    renderWithRouter(<LoginForm />)
    
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/contraseña/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /iniciar sesión/i })).toBeInTheDocument()
  })

  it('debería mostrar errores de validación', async () => {
    const user = userEvent.setup()
    renderWithRouter(<LoginForm />)
    
    const submitButton = screen.getByRole('button', { name: /iniciar sesión/i })
    await user.click(submitButton)
    
    await waitFor(() => {
      expect(screen.getByText(/email es requerido/i)).toBeInTheDocument()
      expect(screen.getByText(/contraseña es requerida/i)).toBeInTheDocument()
    })
  })

  it('debería enviar credenciales válidas', async () => {
    const user = userEvent.setup()
    const mockLogin = vi.fn().mockResolvedValue({
      access_token: 'mock-token',
      token_type: 'bearer'
    })
    
    const { authService } = await import('@/services/authService')
    authService.login = mockLogin
    
    renderWithRouter(<LoginForm />)
    
    await user.type(screen.getByLabelText(/email/i), 'test@example.com')
    await user.type(screen.getByLabelText(/contraseña/i), 'password123')
    
    const submitButton = screen.getByRole('button', { name: /iniciar sesión/i })
    await user.click(submitButton)
    
    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'password123'
      })
    })
  })

  it('debería mostrar error de credenciales inválidas', async () => {
    const user = userEvent.setup()
    const mockLogin = vi.fn().mockRejectedValue({
      response: {
        status: 401,
        data: {
          detail: 'Email o contraseña incorrectos'
        }
      }
    })
    
    const { authService } = await import('@/services/authService')
    authService.login = mockLogin
    
    renderWithRouter(<LoginForm />)
    
    await user.type(screen.getByLabelText(/email/i), 'invalid@example.com')
    await user.type(screen.getByLabelText(/contraseña/i), 'wrongpassword')
    
    const submitButton = screen.getByRole('button', { name: /iniciar sesión/i })
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
    is_admin: false,
    is_active: true
  }

  it('debería renderizar el sidebar correctamente', () => {
    renderWithRouter(<Sidebar user={mockUser} />)
    
    expect(screen.getByText(/clientes/i)).toBeInTheDocument()
    expect(screen.getByText(/préstamos/i)).toBeInTheDocument()
    expect(screen.getByText(/pagos/i)).toBeInTheDocument()
  })

  it('debería mostrar opciones de admin para usuarios admin', () => {
    const adminUser = { ...mockUser, is_admin: true }
    renderWithRouter(<Sidebar user={adminUser} />)
    
    expect(screen.getByText(/configuración/i)).toBeInTheDocument()
    expect(screen.getByText(/usuarios/i)).toBeInTheDocument()
  })

  it('debería ocultar opciones de admin para usuarios normales', () => {
    renderWithRouter(<Sidebar user={mockUser} />)
    
    expect(screen.queryByText(/configuración/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/usuarios/i)).not.toBeInTheDocument()
  })
})

describe('Header', () => {
  const mockUser = {
    id: 1,
    email: 'test@example.com',
    nombre: 'Test',
    apellido: 'User',
    is_admin: false,
    is_active: true
  }

  it('debería renderizar el header correctamente', () => {
    renderWithRouter(<Header user={mockUser} />)
    
    expect(screen.getByText(/sistema de préstamos/i)).toBeInTheDocument()
    expect(screen.getByText(/test user/i)).toBeInTheDocument()
  })

  it('debería mostrar botón de logout', () => {
    renderWithRouter(<Header user={mockUser} />)
    
    expect(screen.getByRole('button', { name: /cerrar sesión/i })).toBeInTheDocument()
  })
})

describe('Footer', () => {
  it('debería renderizar el footer correctamente', () => {
    renderWithRouter(<Footer />)
    
    expect(screen.getByText(/© 2025/i)).toBeInTheDocument()
    expect(screen.getByText(/rapicredit/i)).toBeInTheDocument()
  })
})
