import { useState, useEffect } from 'react'
import { Shield } from 'lucide-react'

// Constantes de configuración
const APP_VERSION = '1.0.0'
const LOGO_SIZE = 5
const ICON_SIZE = 3

export function Footer() {
  const currentYear = new Date().getFullYear()
  const [logo, setLogo] = useState<string | null>(null)
  
  // Cargar logo desde localStorage
  useEffect(() => {
    const logoGuardado = localStorage.getItem('logoEmpresa')
    if (logoGuardado) {
      setLogo(logoGuardado)
    }
  }, [])

  return (
    <footer className="bg-white border-t border-gray-200 py-4 px-6">
      <div className="flex flex-col md:flex-row justify-between items-center space-y-2 md:space-y-0">
        {/* Left side - Copyright */}
        <div className="flex items-center space-x-2 text-sm text-gray-600">
          {logo ? (
            <img 
              src={logo} 
              alt="Logo" 
              className={`w-${LOGO_SIZE} h-${LOGO_SIZE} object-contain`}
            />
          ) : (
            <div className={`w-${LOGO_SIZE} h-${LOGO_SIZE} bg-gradient-to-br from-blue-600 to-purple-700 rounded flex items-center justify-center`}>
              <span className="text-white font-bold text-xs">RC</span>
            </div>
          )}
          <span>
            © {currentYear} <strong>RAPICREDIT</strong> - Sistema de Préstamos y Cobranza. Todos los derechos reservados.
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
      <div className="md:hidden mt-2 text-center">
        <span className="text-xs text-gray-500">Realizado por KOHDE</span>
      </div>
    </footer>
  )
}
