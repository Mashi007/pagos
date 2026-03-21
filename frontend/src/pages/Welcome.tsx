import { motion } from 'framer-motion'

import { ChevronRight } from 'lucide-react'

import { useNavigate } from 'react-router-dom'

import { Button } from '../components/ui/button'

import { Logo } from '../components/ui/Logo'

export function Welcome() {
  const navigate = useNavigate()

  return (
    <div className="flex min-h-screen flex-col bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50">
      {/* Header */}

      <header className="border-b border-gray-200 bg-white shadow-sm">
        <div className="mx-auto max-w-7xl px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-xl border-2 border-gray-100 bg-white p-2.5 shadow-xl ring-2 ring-gray-50">
              <Logo
                size="md"
                className="contrast-110 brightness-110 drop-shadow-md"
              />
            </div>

            <span className="ml-3 bg-gradient-to-r from-blue-600 to-purple-700 bg-clip-text text-2xl font-bold text-transparent">
              RAPICREDIT
            </span>
          </div>
        </div>
      </header>

      {/* Main Content */}

      <main className="flex flex-1 items-center justify-center px-4 py-12 sm:px-6 lg:px-8">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="mx-auto max-w-4xl text-center"
        >
          {/* Hero Section */}

          <motion.div
            initial={{ scale: 0.9 }}
            animate={{ scale: 1 }}
            transition={{ duration: 0.8, type: 'spring' }}
            className="mb-12"
          >
            <h1 className="mb-6 bg-gradient-to-r from-blue-600 via-purple-600 to-blue-600 bg-clip-text text-5xl font-bold text-transparent sm:text-6xl lg:text-7xl">
              RAPICREDIT
            </h1>

            <p className="mb-4 text-xl font-medium text-gray-600 sm:text-2xl">
              Sistema de Gestión de Préstamos y Cobranzas
            </p>

            <p className="mx-auto mb-12 max-w-2xl text-lg text-gray-500">
              Plataforma integral para la administración eficiente de
              operaciones crediticias, control de pagos y gestión de clientes.
            </p>
          </motion.div>

          {/* CTA Button */}

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5, duration: 0.6 }}
          >
            <Button
              onClick={() => navigate('/login')}
              size="lg"
              className="transform bg-gradient-to-r from-blue-600 to-purple-700 px-8 py-6 text-lg font-semibold text-white shadow-lg transition-all duration-300 hover:scale-105 hover:from-blue-700 hover:to-purple-800 hover:shadow-xl"
            >
              Ingresar al Sistema
              <ChevronRight className="ml-2 h-5 w-5" />
            </Button>
          </motion.div>
        </motion.div>
      </main>

      {/* Footer */}

      <footer className="border-t border-gray-200 bg-white shadow-sm">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <p className="text-center text-sm text-gray-600">
            &copy; {new Date().getFullYear()} Rapicredit. Todos los derechos
            reservados.
          </p>
        </div>
      </footer>
    </div>
  )
}
