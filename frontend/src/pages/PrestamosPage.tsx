import { useState } from 'react'
import { motion } from 'framer-motion'
import { DollarSign } from 'lucide-react'
import { PrestamosKPIs } from '@/components/prestamos/PrestamosKPIs'
import { PrestamosList } from '@/components/prestamos/PrestamosList'
import { CrearPrestamoForm } from '@/components/prestamos/CrearPrestamoForm'

export function PrestamosPage() {
  const [showForm, setShowForm] = useState(false)
  const [editingPrestamo, setEditingPrestamo] = useState<any>(null)

  const handleSuccess = () => {
    setShowForm(false)
    setEditingPrestamo(null)
  }

  const handleCancel = () => {
    setShowForm(false)
    setEditingPrestamo(null)
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center">
            <DollarSign className="mr-3 h-8 w-8" />
            Préstamos
          </h1>
          <p className="text-muted-foreground">
            Gestión completa de préstamos y financiamientos
          </p>
        </div>
      </div>

      {/* KPIs */}
      <PrestamosKPIs />

      {/* Lista de Préstamos */}
      <PrestamosList />

      {/* Formulario Modal */}
      {showForm && (
        <CrearPrestamoForm
          prestamo={editingPrestamo}
          onSuccess={handleSuccess}
          onCancel={handleCancel}
        />
      )}
    </motion.div>
  )
}