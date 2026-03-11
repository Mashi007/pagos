# -*- coding: utf-8 -*-
"""Add solicitarCodigo and verificarCodigo to estadoCuentaService; update EstadoCuentaPublicoPage flow."""
import os

base = os.path.dirname(os.path.abspath(__file__))

# 1) estadoCuentaService.ts
path_svc = os.path.join(base, "src", "services", "estadoCuentaService.ts")
with open(path_svc, "r", encoding="utf-8") as f:
    c = f.read()

if "SolicitarCodigoResponse" not in c:
    c = c.replace(
        "export interface SolicitarEstadoCuentaResponse {\n  ok: boolean\n  pdf_base64?: string\n  mensaje?: string\n  error?: string\n}",
        """export interface SolicitarEstadoCuentaResponse {
  ok: boolean
  pdf_base64?: string
  mensaje?: string
  error?: string
}

export interface SolicitarCodigoResponse {
  ok: boolean
  mensaje?: string
  error?: string
}

export interface VerificarCodigoResponse {
  ok: boolean
  pdf_base64?: string
  error?: string
}""",
    )

if "solicitarCodigo" not in c:
    c = c.replace(
        "/** Público: solicitar estado de cuenta (genera PDF, envía al email, devuelve PDF en base64). Sin auth. */\nexport async function solicitarEstadoCuenta(cedula: string): Promise<SolicitarEstadoCuentaResponse> {",
        """/** Público: solicitar código por email. Sin auth. Rate limit 5/hora por IP. */
export async function solicitarCodigo(cedula: string): Promise<SolicitarCodigoResponse> {
  const url = `${BASE}/solicitar-codigo`
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cedula: cedula.slice(0, 20).trim() }),
    credentials: 'same-origin',
  })
  if (res.status === 429) {
    return { ok: false, error: 'Ha alcanzado el límite de consultas por hora. Intente más tarde.' }
  }
  const data = await res.json().catch(() => ({}))
  if (!res.ok) return { ok: false, error: (data as SolicitarCodigoResponse).error || `Error ${res.status}.` }
  return data
}

/** Público: verificar código y obtener PDF. Sin auth. Rate limit 15 intentos/15 min por IP. */
export async function verificarCodigo(cedula: string, codigo: string): Promise<VerificarCodigoResponse> {
  const url = `${BASE}/verificar-codigo`
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cedula: cedula.slice(0, 20).trim(), codigo: (codigo || '').trim() }),
    credentials: 'same-origin',
  })
  if (res.status === 429) {
    return { ok: false, error: 'Demasiados intentos. Espere 15 minutos e intente de nuevo.' }
  }
  const data = await res.json().catch(() => ({}))
  if (!res.ok) return { ok: false, error: (data as VerificarCodigoResponse).error || `Error ${res.status}.` }
  return data
}

/** Público: solicitar estado de cuenta (genera PDF, envía al email, devuelve PDF en base64). Sin auth. */
export async function solicitarEstadoCuenta(cedula: string): Promise<SolicitarEstadoCuentaResponse> {""",
    )

with open(path_svc, "w", encoding="utf-8") as f:
    f.write(c)
print("OK: estadoCuentaService.ts")

# 2) EstadoCuentaPublicoPage.tsx - change flow to: step 0 welcome, 1 cedula (solicitarCodigo), 2 enter code (verificarCodigo), 3 PDF
path_page = os.path.join(base, "src", "pages", "EstadoCuentaPublicoPage.tsx")
with open(path_page, "r", encoding="utf-8") as f:
    p = f.read()

# Replace import to add solicitarCodigo and verificarCodigo
if "solicitarCodigo" not in p:
    p = p.replace(
        "import { validarCedulaEstadoCuenta, solicitarEstadoCuenta } from '../services/estadoCuentaService'",
        "import { solicitarCodigo, verificarCodigo } from '../services/estadoCuentaService'",
    )

# Replace step flow: remove validar + auto solicitarEstadoCuenta; add step 2 for code, step 3 for PDF
# Current: step 0 welcome, 1 cedula (validar -> step 2), 2 PDF (useEffect solicitarEstadoCuenta)
# New: step 0 welcome, 1 cedula (solicitarCodigo -> step 2), 2 code (verificarCodigo -> step 3), 3 PDF
old_step_announcements = "const stepAnnouncements: Record<number, string> = {\n    0: 'Pantalla de bienvenida: consulta de estado de cuenta',\n    1: 'Ingrese su nmero de cdula',\n    2: 'Estado de cuenta',\n  }"
# Use generic step names to avoid encoding issues
p = p.replace(
    "const [step, setStep] = useState(0)\n  const [cedula, setCedula] = useState('')\n  const [nombre, setNombre] = useState('')\n  const [loading, setLoading] = useState(false)\n  const [loadingPdf, setLoadingPdf] = useState(false)\n  const [pdfDataUrl, setPdfDataUrl] = useState<string | null>(null)\n  const [mensajeEnvio, setMensajeEnvio] = useState('')\n  const [notification, setNotification] = useState<NotificationState>(null)",
    "const [step, setStep] = useState(0)\n  const [cedula, setCedula] = useState('')\n  const [codigo, setCodigo] = useState('')\n  const [loading, setLoading] = useState(false)\n  const [loadingPdf, setLoadingPdf] = useState(false)\n  const [pdfDataUrl, setPdfDataUrl] = useState<string | null>(null)\n  const [mensajeEnvio, setMensajeEnvio] = useState('')\n  const [notification, setNotification] = useState<NotificationState>(null)",
)

p = p.replace(
    "  const resetForm = (irAStep: number) => {\n    setCedula('')\n    setNombre('')\n    setPdfDataUrl(null)\n    setMensajeEnvio('')\n    setStep(irAStep)\n  }",
    "  const resetForm = (irAStep: number) => {\n    setCedula('')\n    setCodigo('')\n    setPdfDataUrl(null)\n    setMensajeEnvio('')\n    setStep(irAStep)\n  }",
)

# Replace handleValidarCedula to call solicitarCodigo and go to step 2 (enter code)
p = p.replace(
    """  const handleValidarCedula = async () => {
    const v = normalizarCedulaParaProcesar(cedula)
    if (!v.valido) {
      showNotification('error', v.error ?? 'Cdula invlida.')
      return
    }
    const cedulaEnviar = v.valorParaEnviar!
    setLoading(true)
    try {
      const res = await validarCedulaEstadoCuenta(cedulaEnviar)
      if (!res.ok) {
        showNotification('error', res.error || 'Cdula no vlida.')
        return
      }
      setCedula(cedulaEnviar)
      setNombre(res.nombre ?? '')
      setStep(2)
    } catch (e: unknown) {
      showNotification('error', (e as Error)?.message || 'Error al validar cdula.')
    } finally {
      setLoading(false)
    }
  }""",
    """  const handleSolicitarCodigo = async () => {
    const v = normalizarCedulaParaProcesar(cedula)
    if (!v.valido) {
      showNotification('error', v.error ?? 'Cédula inválida.')
      return
    }
    const cedulaEnviar = v.valorParaEnviar!
    setLoading(true)
    try {
      const res = await solicitarCodigo(cedulaEnviar)
      if (!res.ok) {
        showNotification('error', res.error || 'Error al solicitar código.')
        return
      }
      setCedula(cedulaEnviar)
      setMensajeEnvio(res.mensaje ?? 'Si la cédula está registrada, recibirás un código en tu correo.')
      setStep(2)
    } catch (e: unknown) {
      showNotification('error', (e as Error)?.message || 'Error al solicitar código.')
    } finally {
      setLoading(false)
    }
  }

  const handleVerificarCodigo = async () => {
    if (!codigo.trim()) {
      showNotification('error', 'Ingrese el código recibido por correo.')
      return
    }
    setLoadingPdf(true)
    try {
      const res = await verificarCodigo(cedula, codigo.trim())
      if (!res.ok) {
        showNotification('error', res.error || 'Código inválido o expirado.')
        return
      }
      if (res.pdf_base64) {
        setPdfDataUrl(`data:application/pdf;base64,${res.pdf_base64}`)
        setStep(3)
      }
    } catch (e: unknown) {
      showNotification('error', (e as Error)?.message || 'Error al verificar código.')
    } finally {
      setLoadingPdf(false)
    }
  }""",
)

# Remove the useEffect that auto-calls solicitarEstadoCuenta when step===2
p = p.replace(
    """  // En step 2: al montar o al llegar, solicitar PDF y mostrarlo (cedula ya normalizada en step 1)
  useEffect(() => {
    if (step !== 2 || !cedula.trim() || loadingPdf || pdfDataUrl) return
    if (!CEDULA_REGEX.test(cedula)) return

    setLoadingPdf(true)
    solicitarEstadoCuenta(cedula)
      .then((res) => {
        if (!res.ok) {
          showNotification('error', res.error || 'Error al generar estado de cuenta.')
          return
        }
        setMensajeEnvio(res.mensaje ?? 'Se ha enviado una copia al correo registrado.')
        if (res.pdf_base64) {
          setPdfDataUrl(`data:application/pdf;base64,${res.pdf_base64}`)
        }
      })
      .catch((e) => {
        showNotification('error', (e as Error)?.message || 'Error al generar estado de cuenta.')
      })
      .finally(() => setLoadingPdf(false))
  }, [step, cedula, loadingPdf, pdfDataUrl])""",
    "",
)

# Update step announcements for 4 steps
p = p.replace(
    "  const stepAnnouncements: Record<number, string> = {\n    0: 'Pantalla de bienvenida: consulta de estado de cuenta',\n    1: 'Ingrese su nmero de cdula',\n    2: 'Estado de cuenta',\n  }",
    "  const stepAnnouncements: Record<number, string> = {\n    0: 'Pantalla de bienvenida: consulta de estado de cuenta',\n    1: 'Ingrese su número de cédula',\n    2: 'Ingrese el código enviado a su correo',\n    3: 'Estado de cuenta',\n  }",
)

# Step 1: change button to handleSolicitarCodigo and label
p = p.replace(
    "                <Button className=\"flex-1\" onClick={handleValidarCedula} disabled={loading}>\n                  {loading ? 'Verificando...' : 'Continuar'}\n                </Button>",
    "                <Button className=\"flex-1\" onClick={handleSolicitarCodigo} disabled={loading}>\n                  {loading ? 'Enviando código...' : 'Enviar código al correo'}\n                </Button>",
)

# Add step 2 UI: enter code (between step 1 and current "Paso 2" which becomes step 3)
# Current "Paso 2: Bienvenida con nombre + PDF" becomes step 3. We need to add step 2: enter code.
p = p.replace(
    "  // Paso 2: Bienvenida con nombre + PDF + mensaje de envo al email\n  return (",
    "  // Paso 2: Ingresar código\n  if (step === 2) {\n    return (\n      <div className=\"min-h-screen bg-slate-50 flex flex-col items-center justify-center p-4\">\n        <div role=\"status\" aria-live=\"polite\" aria-atomic=\"true\" className=\"sr-only\">{stepAnnouncement}</div>\n        <div className=\"w-full max-w-md flex flex-col items-center gap-3\">\n          <NotificationBanner notification={notification} onDismiss={dismissNotification} />\n          <Card className=\"w-full max-w-md\">\n            <CardHeader>\n              <CardTitle>Verificación por correo</CardTitle>\n              <p className=\"text-sm text-gray-600\">{mensajeEnvio || 'Revisa tu correo e ingresa el código de 6 dígitos.'}</p>\n            </CardHeader>\n            <CardContent className=\"space-y-4\">\n              <Input\n                placeholder=\"Código de 6 dígitos\"\n                value={codigo}\n                onChange={(e) => setCodigo(e.target.value.replace(/\\D/g, '').slice(0, 6))}\n                onKeyDown={(e) => e.key === 'Enter' && handleVerificarCodigo()}\n                maxLength={6}\n              />\n              <div className=\"flex gap-2\">\n                <Button variant=\"outline\" className=\"flex-1\" onClick={() => setStep(1)}>Atrás</Button>\n                <Button className=\"flex-1\" onClick={handleVerificarCodigo} disabled={loadingPdf}>\n                  {loadingPdf ? 'Verificando...' : 'Ver estado de cuenta'}\n                </Button>\n              </div>\n            </CardContent>\n          </Card>\n        </div>\n      </div>\n    )\n  }\n\n  // Paso 3: PDF\n  return (",
)

# Step 3 (ex step 2): change title and remove "Bienvenido, nombre" -> "Estado de cuenta"
p = p.replace(
    "            <CardTitle>Bienvenido, {nombre || 'Cliente'}</CardTitle>",
    "            <CardTitle>Estado de cuenta</CardTitle>",
)

# Fix reset buttons: "Consultar otra cédula" should go to step 1 (cedula), "Termina" to step 0
p = p.replace(
    "              <Button variant=\"outline\" className=\"flex-1\" onClick={() => resetForm(0)}>\n                Termina\n              </Button>\n              <Button className=\"flex-1 bg-[#1e3a5f] hover:bg-[#152a47]\" onClick={() => resetForm(1)}>\n                Consultar otra cdula\n              </Button>",
    "              <Button variant=\"outline\" className=\"flex-1\" onClick={() => resetForm(0)}>Termina</Button>\n              <Button className=\"flex-1 bg-[#1e3a5f] hover:bg-[#152a47]\" onClick={() => resetForm(1)}>Consultar otra cédula</Button>",
)

with open(path_page, "w", encoding="utf-8") as f:
    f.write(p)
print("OK: EstadoCuentaPublicoPage.tsx")
