// Constantes de configuraciÃ³n
const APP_VERSION = '1.0.0'

export function Footer() {
  const currentYear = new Date().getFullYear()

  return (
    <footer className="bg-white border-t border-gray-200 py-4 px-6">
      <div className="flex flex-col md:flex-row justify-between items-center space-y-2 md:space-y-0">
        {/* Left side - Copyright */}
        <div className="flex items-center space-x-2 text-sm text-gray-600">
          <span>
            Â© {currentYear} <strong>RAPICREDIT</strong> - Sistema de PrÃ©stamos y Cobranza. Todos los derechos reservados.
          </span>
        </div>

        {/* Right side - Version and credits */}
        <div className="flex items-center space-x-4 text-sm text-gray-500">
          <span>VersiÃ³n {APP_VERSION}</span>
          <span className="hidden md:inline">â¢</span>
          <span>Realizado por KOHDE</span>
        </div>
      </div>

      {/* Additional info for mobile */}
      <div className="md:hidden mt-2 text-center">
        <span className="text-xs text-gray-500">Realizado por KOHDE</span>
      </div>
    </footer>
  )
}
