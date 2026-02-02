/**
 * Pruebas de Integración - Servicios
 * Testing de servicios y hooks del frontend
 */
import React from 'react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

// Hooks y servicios a probar
import { useAuth } from '@/hooks/useAuth'
import { useClientes } from '@/hooks/useClientes'
import { clienteService } from '@/services/clienteService'
import { authService } from '@/services/authService'

// Mock de fetch global
global.fetch = vi.fn()

// Helper para crear QueryClient de prueba
const createTestQueryClient = () => new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    },
    mutations: {
      retry: false,
    },
  },
})

// Helper para renderizar hooks con QueryClient
const renderHookWithQueryClient = (hook: () => unknown) => {
  const queryClient = createTestQueryClient()
  const wrapper = ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: queryClient }, children)

  return renderHook(hook, { wrapper })
}

describe('useAuth', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('debería inicializar sin usuario autenticado', () => {
    const { result } = renderHookWithQueryClient(() => useAuth())

    expect(result.current.user).toBeNull()
    expect(result.current.isAuthenticated).toBe(false)
    expect(result.current.isLoading).toBe(false)
  })

  it('debería hacer login exitoso', async () => {
    const mockUser = {
      id: 1,
      email: 'test@example.com',
      nombre: 'Test',
      apellido: 'User',
      is_admin: false,
      is_active: true
    }

    const mockResponse = {
      access_token: 'mock-token',
      token_type: 'bearer',
      user: mockUser
    }

    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    } as Response)

    const { result } = renderHookWithQueryClient(() => useAuth())

    await waitFor(async () => {
      await result.current.login('test@example.com', 'password123')
    })

    expect(result.current.user).toEqual(mockUser)
    expect(result.current.isAuthenticated).toBe(true)
    expect(localStorage.getItem('token')).toBe('mock-token')
  })

  it('debería manejar error de login', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: false,
      status: 401,
      json: () => Promise.resolve({ detail: 'Credenciales incorrectas' }),
    } as Response)

    const { result } = renderHookWithQueryClient(() => useAuth())

    await waitFor(async () => {
      try {
        await result.current.login('invalid@example.com', 'wrongpassword')
      } catch (error) {
        expect(error).toBeDefined()
      }
    })

    expect(result.current.user).toBeNull()
    expect(result.current.isAuthenticated).toBe(false)
  })

  it('debería hacer logout correctamente', async () => {
    // Simular usuario autenticado
    localStorage.setItem('token', 'mock-token')

    const { result } = renderHookWithQueryClient(() => useAuth())

    await waitFor(async () => {
      await result.current.logout()
    })

    expect(result.current.user).toBeNull()
    expect(result.current.isAuthenticated).toBe(false)
    expect(localStorage.getItem('token')).toBeNull()
  })
})

describe('useClientes', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('debería cargar lista de clientes', async () => {
    const mockClientes = [
      {
        id: 1,
        cedula: 'V12345678',
        nombres: 'Juan',
        apellidos: 'Pérez',
        telefono: '+58412123456',
        email: 'juan@example.com',
        estado: 'ACTIVO'
      }
    ]

    const mockResponse = {
      data: mockClientes,
      total: 1,
      page: 1,
      per_page: 20,
      total_pages: 1
    }

    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    } as Response)

    const { result } = renderHookWithQueryClient(() => useClientes())

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false)
    })

    expect(result.current.clientes).toEqual(mockClientes)
    expect(result.current.total).toBe(1)
  })

  it('debería crear cliente exitosamente', async () => {
    const mockCliente = {
      id: 1,
      cedula: 'V12345678',
      nombres: 'Juan',
      apellidos: 'Pérez',
      telefono: '+58412123456',
      email: 'juan@example.com',
      estado: 'ACTIVO'
    }

    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockCliente),
    } as Response)

    const { result } = renderHookWithQueryClient(() => useClientes())

    await waitFor(async () => {
      await result.current.createCliente({
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

    expect(result.current.clientes).toContain(mockCliente)
  })

  it('debería actualizar cliente exitosamente', async () => {
    const mockCliente = {
      id: 1,
      cedula: 'V12345678',
      nombres: 'Juan Carlos',
      apellidos: 'Pérez',
      telefono: '+58412123456',
      email: 'juan@example.com',
      estado: 'ACTIVO'
    }

    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockCliente),
    } as Response)

    const { result } = renderHookWithQueryClient(() => useClientes())

    await waitFor(async () => {
      await result.current.updateCliente(1, {
        nombres: 'Juan Carlos'
      })
    })

    expect(result.current.clientes).toContainEqual(
      expect.objectContaining({
        id: 1,
        nombres: 'Juan Carlos'
      })
    )
  })

  it('debería eliminar cliente exitosamente', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ message: 'Cliente eliminado exitosamente' }),
    } as Response)

    const { result } = renderHookWithQueryClient(() => useClientes())

    await waitFor(async () => {
      await result.current.deleteCliente(1)
    })

    expect(result.current.clientes).not.toContainEqual(
      expect.objectContaining({ id: 1 })
    )
  })
})

describe('clienteService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('debería hacer petición GET para obtener clientes', async () => {
    const mockResponse = {
      data: [],
      total: 0,
      page: 1,
      per_page: 20
    }

    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    } as Response)

    const result = await clienteService.getClientes()

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/clientes'),
      expect.objectContaining({
        method: 'GET',
        headers: expect.objectContaining({
          'Content-Type': 'application/json'
        })
      })
    )

    expect(result).toEqual(mockResponse)
  })

  it('debería hacer petición POST para crear cliente', async () => {
    const mockCliente = {
      cedula: 'V12345678',
      nombres: 'Juan',
      apellidos: 'Pérez',
      telefono: '+58412123456',
      email: 'juan@example.com',
      estado: 'ACTIVO'
    }

    const mockResponse = { id: 1, ...mockCliente }

    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    } as Response)

    const result = await clienteService.createCliente(mockCliente)

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/clientes'),
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          'Content-Type': 'application/json'
        }),
        body: JSON.stringify(mockCliente)
      })
    )

    expect(result).toEqual(mockResponse)
  })

  it('debería manejar errores de API', async () => {
    vi.mocked(fetch).mockResolvedValueOnce({
      ok: false,
      status: 400,
      json: () => Promise.resolve({ detail: 'Error de validación' }),
    } as Response)

    await expect(clienteService.createCliente({})).rejects.toThrow()
  })
})

describe('authService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
  })

  it('debería hacer login exitoso', async () => {
    const mockResponse = {
      access_token: 'mock-token',
      token_type: 'bearer',
      user: {
        id: 1,
        email: 'test@example.com',
        nombre: 'Test',
        apellido: 'User'
      }
    }

    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockResponse),
    } as Response)

    const result = await authService.login('test@example.com', 'password123')

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/auth/login'),
      expect.objectContaining({
        method: 'POST',
        headers: expect.objectContaining({
          'Content-Type': 'application/x-www-form-urlencoded'
        }),
        body: 'username=test%40example.com&password=password123'
      })
    )

    expect(result).toEqual(mockResponse)
    expect(localStorage.getItem('token')).toBe('mock-token')
  })

  it('debería hacer logout correctamente', async () => {
    localStorage.setItem('token', 'mock-token')

    await authService.logout()

    expect(localStorage.getItem('token')).toBeNull()
  })

  it('debería obtener usuario actual', async () => {
    const mockUser = {
      id: 1,
      email: 'test@example.com',
      nombre: 'Test',
      apellido: 'User',
      is_admin: false,
      is_active: true
    }

    localStorage.setItem('token', 'mock-token')

    vi.mocked(fetch).mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve(mockUser),
    } as Response)

    const result = await authService.getCurrentUser()

    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/v1/auth/me'),
      expect.objectContaining({
        method: 'GET',
        headers: expect.objectContaining({
          'Authorization': 'Bearer mock-token'
        })
      })
    )

    expect(result).toEqual(mockUser)
  })
})
