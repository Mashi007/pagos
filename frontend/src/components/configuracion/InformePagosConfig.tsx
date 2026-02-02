import { useState, useEffect } from 'react'
import { FileText, Save, Eye, EyeOff, CheckCircle, AlertCircle } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Textarea } from '../../components/ui/textarea'
import { toast } from 'sonner'
import { apiClient } from '../../services/api'

export interface InformePagosConfigData {
  google_drive_folder_id?: string
  google_credentials_json?: string
  google_sheets_id?: string
  destinatarios_informe_emails?: string
  horarios_envio?: Array<{ hour: number; minute: number }>
}

export function InformePagosConfig() {
  const [config, setConfig] = useState<InformePagosConfigData>({})
  const [guardando, setGuardando] = useState(false)
  const [mostrarCredenciales, setMostrarCredenciales] = useState(false)
  const [credencialesEdit, setCredencialesEdit] = useState('')

  useEffect(() => {
    cargarConfiguracion()
  }, [])

  const cargarConfiguracion = async () => {
    try {
      const data = await apiClient.get<InformePagosConfigData>(
        '/api/v1/configuracion/informe-pagos/configuracion'
      )
      setConfig(data)
      if (data.google_credentials_json && data.google_credentials_json !== '***') {
        setCredencialesEdit(data.google_credentials_json)
      }
    } catch (error) {
      console.error('Error cargando configuración informe pagos:', error)
      toast.error('Error cargando configuración')
    }
  }

  const handleChange = (campo: keyof InformePagosConfigData, valor: string | undefined) => {
    setConfig((prev) => ({ ...prev, [campo]: valor }))
  }

  const handleGuardar = async () => {
    try {
      setGuardando(true)
      const payload: InformePagosConfigData = {
        ...config,
        google_drive_folder_id: config.google_drive_folder_id || undefined,
        google_sheets_id: config.google_sheets_id || undefined,
        destinatarios_informe_emails: config.destinatarios_informe_emails || undefined,
      }
      if (credencialesEdit && credencialesEdit.trim() && credencialesEdit !== '***') {
        payload.google_credentials_json = credencialesEdit.trim()
      }
      await apiClient.put('/api/v1/configuracion/informe-pagos/configuracion', payload)
      toast.success('Configuración informe pagos guardada')
      await cargarConfiguracion()
    } catch (error: any) {
      console.error('Error guardando:', error)
      toast.error(error?.response?.data?.detail || 'Error guardando configuración')
    } finally {
      setGuardando(false)
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5 text-blue-600" />
            Informe de pagos (Google Drive, Sheets, OCR)
          </CardTitle>
          <CardDescription>
            Configuración para el flujo de cobranza por WhatsApp: imágenes de papeletas se suben a Google Drive,
            se extraen datos con OCR (Google Vision) y se digitalizan en Google Sheets. A las 6:00, 13:00 y 16:30
            (America/Caracas) se envía un email con el link a la hoja.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <label className="text-sm font-medium block mb-2">ID carpeta Google Drive</label>
            <Input
              placeholder="Ej: 1ABC..."
              value={config.google_drive_folder_id ?? ''}
              onChange={(e) => handleChange('google_drive_folder_id', e.target.value)}
            />
            <p className="text-xs text-gray-500 mt-1">
              ID de la carpeta donde se guardan las imágenes de papeletas (desde la URL de la carpeta).
            </p>
          </div>
          <div>
            <label className="text-sm font-medium block mb-2">Credenciales Google (cuenta de servicio JSON)</label>
            <div className="flex gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => setMostrarCredenciales(!mostrarCredenciales)}
              >
                {mostrarCredenciales ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </Button>
              <Textarea
                placeholder='{"type":"service_account",...}'
                value={config.google_credentials_json === '***' ? credencialesEdit : (credencialesEdit || config.google_credentials_json ?? '')}
                onChange={(e) => setCredencialesEdit(e.target.value)}
                className="font-mono text-xs min-h-[120px]"
                rows={6}
              />
            </div>
            <p className="text-xs text-gray-500 mt-1">
              JSON de la cuenta de servicio (Drive + Sheets + Vision API). No se muestra después de guardar; usa *** para no sobrescribir.
            </p>
          </div>
          <div>
            <label className="text-sm font-medium block mb-2">ID Google Sheet</label>
            <Input
              placeholder="Ej: 1ABC... (desde la URL de la hoja)"
              value={config.google_sheets_id ?? ''}
              onChange={(e) => handleChange('google_sheets_id', e.target.value)}
            />
          </div>
          <div>
            <label className="text-sm font-medium block mb-2">Destinatarios del informe (emails)</label>
            <Input
              placeholder="email1@ejemplo.com, email2@ejemplo.com"
              value={config.destinatarios_informe_emails ?? ''}
              onChange={(e) => handleChange('destinatarios_informe_emails', e.target.value)}
            />
            <p className="text-xs text-gray-500 mt-1">
              Emails que reciben el link a la hoja a las 6:00, 13:00 y 16:30 (America/Caracas).
            </p>
          </div>
          <Button onClick={handleGuardar} disabled={guardando}>
            {guardando ? (
              'Guardando...'
            ) : (
              <>
                <Save className="h-4 w-4 mr-2" />
                Guardar configuración
              </>
            )}
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
