// Constantes de configuración

const APP_VERSION = '1.0.0'

export function Footer() {
  const currentYear = new Date().getFullYear()

  return (
    <footer className="border-t border-gray-200 bg-white px-6 py-4">
      <div className="flex flex-col items-center justify-between space-y-2 md:flex-row md:space-y-0">
        {/* Left side - Copyright */}

        <div className="flex items-center space-x-2 text-sm text-gray-600">
          <span>
            © {currentYear} <strong>RAPICREDIT</strong> - Sistema de Préstamos y
            Cobranza. Todos los derechos reservados.
          </span>
        </div>

        {/* Right side - Version and credits */}

        <div className="flex items-center space-x-4 text-sm text-gray-500">
          <span>Versión {APP_VERSION}</span>

          <span className="hidden md:inline">•</span>

          <span>Realizado por KOHDE</span>
        </div>
      </div>

      {/* Additional info for mobile */}

      <div className="mt-2 text-center md:hidden">
        <span className="text-xs text-gray-500">Realizado por KOHDE</span>
      </div>
    </footer>
  )
}
