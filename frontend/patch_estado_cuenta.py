# Patch EstadoCuentaPublicoPage: add validarCedulaEstadoCuenta before solicitarCodigo
path = "src/pages/EstadoCuentaPublicoPage.tsx"
with open(path, "r", encoding="utf-8") as f:
    content = f.read()

# 1) Add validarCedulaEstadoCuenta to import
content = content.replace(
    "import { solicitarCodigo, verificarCodigo } from '../services/estadoCuentaService'",
    "import { validarCedulaEstadoCuenta, solicitarCodigo, verificarCodigo } from '../services/estadoCuentaService'",
)

# 2) In handleSolicitarCodigo: validate first, then solicitarCodigo
old_block = """  const handleSolicitarCodigo = async () => {
    const v = normalizarCedulaParaProcesar(cedula)
    if (!v.valido) {
      showNotification('error', v.error ?? 'CAcdula invAlida.')
      return
    }
    const cedulaEnviar = v.valorParaEnviar!
    setLoading(true)
    try {
      const res = await solicitarCodigo(cedulaEnviar)
      if (!res.ok) {
        showNotification('error', res.error || 'CAcdula no vAlida.')
        return
      }"""

new_block = """  const handleSolicitarCodigo = async () => {
    const v = normalizarCedulaParaProcesar(cedula)
    if (!v.valido) {
      showNotification('error', v.error ?? 'Cédula inválida.')
      return
    }
    const cedulaEnviar = v.valorParaEnviar!
    setLoading(true)
    try {
      const validacion = await validarCedulaEstadoCuenta(cedulaEnviar)
      if (!validacion.ok) {
        showNotification('error', validacion.error || 'Cédula no válida.')
        return
      }
      const res = await solicitarCodigo(cedulaEnviar)
      if (!res.ok) {
        showNotification('error', res.error || 'No se pudo enviar el código.')
        return
      }"""

# Try with mojibake version too (A for í)
old_alt = old_block.replace("invAlida", "inválida").replace("no vAlida", "no válida")
if old_block in content:
    content = content.replace(old_block, new_block, 1)
    print("Patched (original)")
elif old_alt in content:
    content = content.replace(old_alt, new_block, 1)
    print("Patched (alt)")
else:
    # Minimal: just add validation call after setLoading
    import re
    content = re.sub(
        r"(import \{ )(solicitarCodigo, verificarCodigo)( \} from)",
        r"\1validarCedulaEstadoCuenta, \2\3",
        content,
    )
    content = re.sub(
        r"(setLoading\(true\)\s+try \{\s+)(const res = await solicitarCodigo)",
        r"\1const validacion = await validarCedulaEstadoCuenta(cedulaEnviar)\n      if (!validacion.ok) {\n        showNotification('error', validacion.error || 'Cédula no válida.')\n        return\n      }\n      \2",
        content,
        1,
    )
    print("Patched (regex)")

with open(path, "w", encoding="utf-8") as f:
    f.write(content)
print("OK")
