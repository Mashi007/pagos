import { useState } from 'react'
import { PrestamosList } from '@/components/prestamos/PrestamosList'
import { DollarSign } from 'lucide-react'

export default function Prestamos() {
  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center gap-3 mb-6">
        <DollarSign className="h-8 w-8 text-blue-600" />
        <h1 className="text-3xl font-bold text-gray-900">Préstamos</h1>
      </div>
      
      <PrestamosList />
    </div>
  )
}
