import { FileText } from 'lucide-react'

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '../../../components/ui/card'

import { Textarea } from '../../../components/ui/textarea'

import type { FormData } from './useCrearCliente'

interface NotasSectionProps {
  formData: FormData

  onInputChange: (field: keyof FormData, value: string) => void
}

export function NotasSection({ formData, onInputChange }: NotasSectionProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <FileText className="h-5 w-5" />
          Notas
        </CardTitle>
      </CardHeader>

      <CardContent className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-700">
            Notas{' '}
            <span className="text-xs text-gray-500">
              (Por defecto: &quot;No hay observacion&quot;)
            </span>
          </label>

          <Textarea
            value={formData.notas}
            onChange={(e: React.ChangeEvent<HTMLTextAreaElement>) =>
              onInputChange('notas', e.target.value)
            }
            placeholder="No hay observacion"
            rows={3}
          />
        </div>
      </CardContent>
    </Card>
  )
}
