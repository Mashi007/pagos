# Fix EstadoCuentaPublicoPage.tsx: replace handleValidarCedula with handleSolicitarCodigo + handleVerificarCodigo, add step 2 UI
path = "src/pages/EstadoCuentaPublicoPage.tsx"
with open(path, "r", encoding="utf-8") as f:
    c = f.read()

# 1) Replace step announcements (allow for slight encoding variations)
import re
c = re.sub(
    r"  const stepAnnouncements: Record<number, string> = \{[^}]+\}",
    """  const stepAnnouncements: Record<number, string> = {
    0: 'Pantalla de bienvenida: consulta de estado de cuenta',
    1: 'Ingrese su numero de cedula',
    2: 'Ingrese el codigo enviado a su correo',
    3: 'Estado de cuenta',
  }""",
    c,
    count=1,
)

# 2) Replace entire handleValidarCedula block with handleSolicitarCodigo + handleVerificarCodigo
old_handler = """  const handleValidarCedula = async () => {
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
  }"""

new_handlers = """  const handleSolicitarCodigo = async () => {
    const v = normalizarCedulaParaProcesar(cedula)
    if (!v.valido) {
      showNotification('error', v.error ?? 'Cedula invalida.')
      return
    }
    const cedulaEnviar = v.valorParaEnviar!
    setLoading(true)
    try {
      const res = await solicitarCodigo(cedulaEnviar)
      if (!res.ok) {
        showNotification('error', res.error || 'Error al solicitar codigo.')
        return
      }
      setCedula(cedulaEnviar)
      setMensajeEnvio(res.mensaje ?? 'Si la cedula esta registrada, recibiras un codigo en tu correo.')
      setStep(2)
    } catch (e: unknown) {
      showNotification('error', (e as Error)?.message || 'Error al solicitar codigo.')
    } finally {
      setLoading(false)
    }
  }

  const handleVerificarCodigo = async () => {
    if (!codigo.trim()) {
      showNotification('error', 'Ingrese el codigo recibido por correo.')
      return
    }
    setLoadingPdf(true)
    try {
      const res = await verificarCodigo(cedula, codigo.trim())
      if (!res.ok) {
        showNotification('error', res.error || 'Codigo invalido o expirado.')
        return
      }
      if (res.pdf_base64) {
        setPdfDataUrl(`data:application/pdf;base64,${res.pdf_base64}`)
        setStep(3)
      }
    } catch (e: unknown) {
      showNotification('error', (e as Error)?.message || 'Error al verificar codigo.')
    } finally {
      setLoadingPdf(false)
    }
  }"""

if "handleValidarCedula" in c and "validarCedulaEstadoCuenta" in c:
    c = c.replace(old_handler, new_handlers, 1)
else:
    # Try with escaped chars for encoding
    for old in [
        "const res = await validarCedulaEstadoCuenta(cedulaEnviar)",
        "setNombre(res.nombre ?? '')",
    ]:
        if old in c:
            c = c.replace(
                "const res = await validarCedulaEstadoCuenta(cedulaEnviar)\n      if (!res.ok) {\n        showNotification('error', res.error || 'Cdula no vlida.')\n        return\n      }\n      setCedula(cedulaEnviar)\n      setNombre(res.nombre ?? '')\n      setStep(2)",
                "const res = await solicitarCodigo(cedulaEnviar)\n      if (!res.ok) {\n        showNotification('error', res.error || 'Error al solicitar codigo.')\n        return\n      }\n      setCedula(cedulaEnviar)\n      setMensajeEnvio(res.mensaje ?? 'Si la cedula esta registrada, recibiras un codigo en tu correo.')\n      setStep(2)",
                1,
            )
            break

# Replace handleValidarCedula function name and body in one go - multi-line match
import re
pattern = r"  const handleValidarCedula = async \(\) => \{[^}]*(?:\{[^}]*\}[^}]*)*\}"
if re.search(pattern, c, re.DOTALL):
    c = re.sub(pattern, new_handlers, c, count=1)
elif "handleValidarCedula" in c:
    # Fallback: replace line by line
    lines = c.split("\n")
    out = []
    skip_until = -1
    i = 0
    while i < len(lines):
        if "const handleValidarCedula = async" in lines[i]:
            out.append(new_handlers)
            i += 1
            brace = 0
            while i < len(lines):
                brace += lines[i].count("{") - lines[i].count("}")
                i += 1
                if brace <= 0 and "}" in lines[i-1]:
                    break
            continue
        out.append(lines[i])
        i += 1
    c = "\n".join(out)

# 3) onKeyDown handleValidarCedula -> handleSolicitarCodigo
c = c.replace("handleValidarCedula()", "handleSolicitarCodigo()")

# 4) Add step 2 UI before "Paso 2: Bienvenida con nombre + PDF"
if "Paso 2: Ingresar codigo" not in c and "step === 2" not in c:
    c = c.replace(
        "  // Paso 2: Bienvenida con nombre + PDF + mensaje de env",
        "  // Paso 2: Ingresar codigo\n  if (step === 2) {\n    return (\n      <div className=\"min-h-screen bg-slate-50 flex flex-col items-center justify-center p-4\">\n        <div role=\"status\" aria-live=\"polite\" aria-atomic=\"true\" className=\"sr-only\">{stepAnnouncement}</div>\n        <div className=\"w-full max-w-md flex flex-col items-center gap-3\">\n          <NotificationBanner notification={notification} onDismiss={dismissNotification} />\n          <Card className=\"w-full max-w-md\">\n            <CardHeader>\n              <CardTitle>Verificacion por correo</CardTitle>\n              <p className=\"text-sm text-gray-600\">{mensajeEnvio || 'Revisa tu correo e ingresa el codigo de 6 digitos.'}</p>\n            </CardHeader>\n            <CardContent className=\"space-y-4\">\n              <Input\n                placeholder=\"Codigo de 6 digitos\"\n                value={codigo}\n                onChange={(e) => setCodigo(e.target.value.replace(/\\\\D/g, '').slice(0, 6))}\n                onKeyDown={(e) => e.key === 'Enter' && handleVerificarCodigo()}\n                maxLength={6}\n              />\n              <div className=\"flex gap-2\">\n                <Button variant=\"outline\" className=\"flex-1\" onClick={() => setStep(1)}>Atras</Button>\n                <Button className=\"flex-1\" onClick={handleVerificarCodigo} disabled={loadingPdf}>\n                  {loadingPdf ? 'Verificando...' : 'Ver estado de cuenta'}\n                </Button>\n              </div>\n            </CardContent>\n          </Card>\n        </div>\n      </div>\n    )\n  }\n\n  // Paso 3: PDF\n  return (",
        1,
    )
# If the above replace key is different (encoding)
if "step === 2" not in c:
    c = c.replace(
        "  // Paso 2: Bienvenida con nombre + PDF + mensaje de envo al email\n  return (",
        "  // Paso 2: Ingresar codigo\n  if (step === 2) {\n    return (\n      <div className=\"min-h-screen bg-slate-50 flex flex-col items-center justify-center p-4\">\n        <div role=\"status\" aria-live=\"polite\" aria-atomic=\"true\" className=\"sr-only\">{stepAnnouncement}</div>\n        <div className=\"w-full max-w-md flex flex-col items-center gap-3\">\n          <NotificationBanner notification={notification} onDismiss={dismissNotification} />\n          <Card className=\"w-full max-w-md\">\n            <CardHeader>\n              <CardTitle>Verificacion por correo</CardTitle>\n              <p className=\"text-sm text-gray-600\">{mensajeEnvio || 'Revisa tu correo e ingresa el codigo de 6 digitos.'}</p>\n            </CardHeader>\n            <CardContent className=\"space-y-4\">\n              <Input\n                placeholder=\"Codigo de 6 digitos\"\n                value={codigo}\n                onChange={(e) => setCodigo(e.target.value.replace(/\\D/g, '').slice(0, 6))}\n                onKeyDown={(e) => e.key === 'Enter' && handleVerificarCodigo()}\n                maxLength={6}\n              />\n              <div className=\"flex gap-2\">\n                <Button variant=\"outline\" className=\"flex-1\" onClick={() => setStep(1)}>Atras</Button>\n                <Button className=\"flex-1\" onClick={handleVerificarCodigo} disabled={loadingPdf}>\n                  {loadingPdf ? 'Verificando...' : 'Ver estado de cuenta'}\n                </Button>\n              </div>\n            </CardContent>\n          </Card>\n        </div>\n      </div>\n    )\n  }\n\n  // Paso 3: PDF\n  return (",
        1,
    )

with open(path, "w", encoding="utf-8") as f:
    f.write(c)
print("OK")
