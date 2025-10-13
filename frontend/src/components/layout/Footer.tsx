import React from 'react'
import { Heart, Shield } from 'lucide-react'

export function Footer() {
  const currentYear = new Date().getFullYear()

  return (
    <footer className="bg-white border-t border-gray-200 py-4 px-6">
      <div className="flex flex-col md:flex-row justify-between items-center space-y-2 md:space-y-0">
        {/* Left side - Copyright */}
        <div className="flex items-center space-x-2 text-sm text-gray-600">
          <div className="w-5 h-5 bg-gradient-to-br from-blue-600 to-purple-700 rounded flex items-center justify-center">
            <span className="text-white font-bold text-xs">RC</span>
          </div>
          <span>
            © {currentYear} <strong>RAPICREDIT</strong> - Sistema de Préstamos y Cobranza. Todos los derechos reservados.
          </span>
        </div>

        {/* Right side - Version and credits */}
        <div className="flex items-center space-x-4 text-sm text-gray-500">
          <span>Versión 1.0.0</span>
          <span className="hidden md:inline">•</span>
          <div className="flex items-center space-x-1">
            <span>Hecho con</span>
            <Heart className="h-3 w-3 text-red-500 fill-current" />
            <span>para RAPICREDIT</span>
          </div>
        </div>
      </div>

      {/* Additional info for mobile */}
      <div className="md:hidden mt-2 text-center">
        <div className="flex items-center justify-center space-x-1 text-xs text-gray-500">
          <span>Hecho con</span>
          <Heart className="h-3 w-3 text-red-500 fill-current" />
          <span>para RAPICREDIT</span>
        </div>
      </div>
    </footer>
  )
}
