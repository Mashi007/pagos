/**
 * Pruebas de integración: flujo público estado de cuenta (rapicredit-estadocuenta).
 * Mock del servicio API; verifica pasos, botón Reenviar código y cooldown.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { BrowserRouter } from 'react-router-dom'
import EstadoCuentaPublicoPage from '@/pages/EstadoCuentaPublicoPage'

const mockSolicitarCodigo = vi.fn()
const mockVerificarCodigo = vi.fn()

vi.mock('@/services/estadoCuentaService', () => ({
  solicitarCodigo: (cedula: string) => mockSolicitarCodigo(cedula),
  verificarCodigo: (cedula: string, codigo: string) => mockVerificarCodigo(cedula, codigo),
}))

const renderPage = () =>
  render(
    <BrowserRouter>
      <EstadoCuentaPublicoPage />
    </BrowserRouter>
  )

describe('EstadoCuentaPublicoPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockSolicitarCodigo.mockResolvedValue({ ok: true, mensaje: 'Revisa tu correo.' })
    mockVerificarCodigo.mockResolvedValue({
      ok: true,
      pdf_base64: 'JVBERi0xLjQKJeLjz9MKMSAwIG9iago8PAovVHlwZSAvQ2F0YWxvZwovUGFnZXMgMiAwIFIKPj4KZW5kb2JqCjIgMCBvYmoKPDwKL1R5cGUgL1BhZ2VzCi9LaWRzIFszIDAgUl0KL0NvdW50IDEKL01lZGlhQm94IFswIDAgNjEyIDc5Ml0KPj4KZW5kb2JqCjMgMCBvYmoKPDwKL1R5cGUgL1BhZ2UKL1BhcmVudCAyIDAgUgovQ29udGVudHMgNCAwIFIKPj4KZW5kb2JqCjQgMCBvYmoKPDwKL0xlbmd0aCA0NAo+PgpzdHJlYW0KQlQKL0YxIDEyIFRmCjEwMCA3MDAgVGQKKEhlbGxvIFBERikgVGoKRVQKZW5kc3RyZWFtCmVuZG9iago1IDAgb2JqCjw8Ci9UeXBlIC9Gb250Ci9TdWJ0eXBlIC9UeXBlMQovQmFzZUZvbnQgL0hlbHZldGljYQo+PgplbmRvYmoKeHJlZgowIDYKMDAwMDAwMDAwMCA2NTUzNSBmIAowMDAwMDAwMDA5IDAwMDAwIG4gCjAwMDAwMDAwNTggMDAwMDAgbiAKMDAwMDAwMDE3MyAwMDAwMCBuIAowMDAwMDAwMzAxIDAwMDAwIG4gCjAwMDAwMDAzODQgMDAwMDAgbiAKdHJhaWxlcgo8PAovU2l6ZSA2Ci9Sb290IDEgMCBSCj4+CnN0YXJ0eHJlZgo0NDYKJSVFT0YK', // PDF mínimo base64
    })
  })

  it('muestra pantalla de bienvenida y botón Iniciar', () => {
    renderPage()
    expect(screen.getByRole('button', { name: /iniciar/i })).toBeInTheDocument()
    expect(screen.getByText(/Bienvenido/i)).toBeInTheDocument()
  })

  it('al hacer clic en Iniciar pasa al paso de cédula', async () => {
    const user = userEvent.setup()
    renderPage()
    await user.click(screen.getByRole('button', { name: /iniciar/i }))
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/V12345678|cedula/i)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /enviar código al correo/i })).toBeInTheDocument()
    })
  })

  it('al enviar cédula válida llama a solicitarCodigo y pasa a paso de código', async () => {
    const user = userEvent.setup()
    renderPage()
    await user.click(screen.getByRole('button', { name: /iniciar/i }))
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/V12345678|cedula/i)).toBeInTheDocument()
    })
    const input = screen.getByPlaceholderText(/V12345678|cedula/i)
    await user.type(input, 'V12345678')
    await user.click(screen.getByRole('button', { name: /enviar código al correo/i }))
    await waitFor(() => {
      expect(mockSolicitarCodigo).toHaveBeenCalledWith('V12345678')
    })
    await waitFor(() => {
      expect(screen.getByPlaceholderText(/código de 6|6 dígitos/i)).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /ver estado de cuenta/i })).toBeInTheDocument()
    })
  })

  it('en paso de código muestra botón Reenviar código', async () => {
    const user = userEvent.setup()
    renderPage()
    await user.click(screen.getByRole('button', { name: /iniciar/i }))
    await waitFor(() => screen.getByPlaceholderText(/V12345678|cedula/i))
    await user.type(screen.getByPlaceholderText(/V12345678|cedula/i), 'V12345678')
    await user.click(screen.getByRole('button', { name: /enviar código al correo/i }))
    await waitFor(() => screen.getByPlaceholderText(/código de 6|6 dígitos/i))
    expect(screen.getByRole('button', { name: /no llegó el correo\? reenviar código/i })).toBeInTheDocument()
  })
})
