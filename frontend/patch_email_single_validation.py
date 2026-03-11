# Un solo camino de validación: quitar validación previa en frontend al guardar.
from pathlib import Path

path = Path("src/components/configuracion/EmailConfig.tsx")
text = path.read_text(encoding="utf-8")

# Remove validarConfiguracion function and its use in handleGuardar
old_block = """  const validarConfiguracion = (): string | null => {
    const validacion = validarConfiguracionGmail({
      smtp_host: config.smtp_host,
      smtp_port: config.smtp_port,
      smtp_user: config.smtp_user,
      smtp_password: config.smtp_password,
      smtp_use_tls: config.smtp_use_tls,
      from_email: config.from_email
    })
    if (!validacion.valido) return validacion.errores.join('. ')
    const tieneImap = !!(config.imap_host?.trim() || config.imap_user?.trim() || config.imap_password?.trim())
    if (tieneImap) {
      const validacionImap = validarConfiguracionImapGmail({
        imap_host: config.imap_host || 'imap.gmail.com',
        imap_port: config.imap_port || '993',
        imap_user: config.imap_user,
        imap_password: config.imap_password,
        imap_use_ssl: config.imap_use_ssl ?? 'true',
      })
      if (!validacionImap.valido) return `IMAP: ${validacionImap.errores.join('. ')}`
    }
    return null
  }

  // Guardar configuración
  const handleGuardar = async () => {
    const error = validarConfiguracion()
    if (error) {
      setErrorValidacion(error)
      toast.error(error)
      return
    }

    setErrorValidacion(null)

    try {"""

new_block = """  // Guardar: validación única en backend (PUT); errores 400 se muestran en toast.
  const handleGuardar = async () => {
    setErrorValidacion(null)

    try {"""

if "validarConfiguracion()" in text and "validarConfiguracionGmail" not in text:
    print("Already patched (no validarConfiguracionGmail)")
elif old_block in text:
    text = text.replace(old_block, new_block, 1)
    print("Replaced validarConfiguracion block")
else:
    # Try with encoding variants
    if "validarConfiguracion = (): string" in text:
        # Find and replace by line ranges or simpler pattern
        import re
        pattern = re.compile(
            r"  const validarConfiguracion = \(\): string \| null => \{[^}]+\}[^}]+\}[^}]+\}[^}]+return null\s+\}\s+// Guardar configurac[ió]i?[A3]*n\s+const handleGuardar = async \(\) => \{\s+const error = validarConfiguracion\(\)\s+if \(error\) \{\s+setErrorValidacion\(error\)\s+toast\.error\(error\)\s+return\s+\}\s+setErrorValidacion\(null\)\s+try \{",
            re.DOTALL,
        )
        if pattern.search(text):
            text = pattern.sub(
                "  // Guardar: validación única en backend (PUT); errores 400 se muestran en toast.\n  const handleGuardar = async () => {\n    setErrorValidacion(null)\n\n    try {",
                text,
                1,
            )
            print("Replaced via regex")
    else:
        print("Block not found; check file encoding")

path.write_text(text, encoding="utf-8")
print("Done.")
