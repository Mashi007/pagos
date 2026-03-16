/**
 * Añade la sección "Servicios disponibles" a EmailCuentasConfig.tsx
 * (toggles para activar/desactivar email por servicio: Cobros, Estado de cuenta, Notificaciones)
 */
const fs = require('fs')
const path = require('path')
const file = path.join(__dirname, '..', 'src', 'components', 'configuracion', 'EmailCuentasConfig.tsx')
let c = fs.readFileSync(file, 'utf8')

if (c.includes('Servicios disponibles')) {
  console.log('Ya existe sección Servicios disponibles')
  process.exit(0)
}

// 1) Añadir ToggleLeft al import de lucide-react
c = c.replace(
  "import { Mail, Save, AlertCircle } from 'lucide-react'",
  "import { Mail, Save, AlertCircle, ToggleLeft } from 'lucide-react'"
)

// 2) Tras setNotifTabCuenta, añadir setServicioActivo y SERVICIOS_DISPONIBLES
const injectHelpers = `  const setNotifTabCuenta = (tabId: string, cuenta: number) => {
    setAsignacion(prev => ({ ...prev, [tabId]: cuenta }))
  }

  const setServicioActivo = (key: keyof EmailCuentasResponse, value: string) => {
    if (!data) return
    setData({ ...data, [key]: value })
  }

  const SERVICIOS_DISPONIBLES: { key: keyof EmailCuentasResponse; label: string; cuenta: number }[] = [
    { key: 'email_activo_cobros', label: 'Cobros (formulario público, recibos)', cuenta: 1 },
    { key: 'email_activo_estado_cuenta', label: 'Estado de cuenta (código y envío PDF)', cuenta: 2 },
    { key: 'email_activo_notificaciones', label: 'Notificaciones (plantillas a clientes)', cuenta: 3 },
  ]`

c = c.replace(
  /  const setNotifTabCuenta = \(tabId: string, cuenta: number\) => \{\s*setAsignacion\(prev => \(\{ \.\.\.prev, \[tabId\]: cuenta \}\)\)\s*\}/,
  injectHelpers
)

// 3) Añadir Card "Servicios disponibles" después del primer Card (descripción) y antes de los 4 bloques de cuentas
const serviciosCard = `
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <ToggleLeft className="h-4 w-4" />
            Servicios disponibles
          </CardTitle>
          <CardDescription>
            Active o desactive el envío de correo por servicio. Cada uno usa la cuenta indicada (Cuenta 1, 2 o 3/4).
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2">
            {SERVICIOS_DISPONIBLES.map(({ key, label, cuenta }) => (
              <div key={key} className="flex items-center justify-between rounded border p-3">
                <div>
                  <p className="text-sm font-medium">{label}</p>
                  <p className="text-xs text-muted-foreground">Cuenta {cuenta}</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={(data?.[key] ?? 'true') === 'true'}
                    onChange={e => setServicioActivo(key, e.target.checked ? 'true' : 'false')}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600" />
                  <span className="ml-2 text-sm">{(data?.[key] ?? 'true') === 'true' ? 'Activo' : 'Inactivo'}</span>
                </label>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {[0, 1, 2, 3].map(i => (`
// Replace the line that starts the 4 account cards with the new card + 4 account cards
c = c.replace(
  /(\s+)<Card className="border-blue-200 bg-blue-50\/50 dark:bg-blue-950\/20">/,
  `$1<Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <ToggleLeft className="h-4 w-4" />
            Servicios disponibles
          </CardTitle>
          <CardDescription>
            Active o desactive el envío de correo por servicio. Cada uno usa la cuenta indicada (Cuenta 1, 2 o 3/4).
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2">
            {SERVICIOS_DISPONIBLES.map(({ key, label, cuenta }) => (
              <div key={key} className="flex items-center justify-between rounded border p-3">
                <div>
                  <p className="text-sm font-medium">{label}</p>
                  <p className="text-xs text-muted-foreground">Cuenta {cuenta}</p>
                </div>
                <label className="relative inline-flex items-center cursor-pointer">
                  <input
                    type="checkbox"
                    checked={(data?.[key] ?? 'true') === 'true'}
                    onChange={e => setServicioActivo(key, e.target.checked ? 'true' : 'false')}
                    className="sr-only peer"
                  />
                  <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-blue-600" />
                  <span className="ml-2 text-sm">{(data?.[key] ?? 'true') === 'true' ? 'Activo' : 'Inactivo'}</span>
                </label>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      $1<Card className="border-blue-200 bg-blue-50/50 dark:bg-blue-950/20">`
)

fs.writeFileSync(file, c)
console.log('Sección Servicios disponibles añadida a EmailCuentasConfig.tsx')
