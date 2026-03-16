const fs = require('fs')
const path = require('path')
const file = path.join(__dirname, '..', 'src', 'components', 'configuracion', 'tabs', 'ConfigEmailTab.tsx')
let c = fs.readFileSync(file, 'utf8')
const old = `import { EmailConfig } from '../EmailConfig'

export function ConfigEmailTab() {
  return <EmailConfig />
}`
const newContent = `import { EmailCuentasConfig } from '../EmailCuentasConfig'

/** Configuración de correo: 4 cuentas con asignación por servicio. */
export function ConfigEmailTab() {
  return <EmailCuentasConfig />
}`
if (c.includes("EmailCuentasConfig")) {
  console.log("ConfigEmailTab already patched")
} else if (c.includes("EmailConfig")) {
  c = c.replace(old, newContent)
  fs.writeFileSync(file, c)
  console.log("ConfigEmailTab patched to use EmailCuentasConfig")
} else {
  console.log("Pattern not found in ConfigEmailTab")
}
