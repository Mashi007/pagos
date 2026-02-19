import { useState, useEffect } from 'react'
import { notificacionService, type NotificacionPlantilla } from '../../services/notificacionService'
import { emailConfigService } from '../../services/notificacionService'
import { Button } from '../../components/ui/button'
import { Input } from '../../components/ui/input'
import { Textarea } from '../../components/ui/textarea'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../../components/ui/card'
import { Badge } from '../../components/ui/badge'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select'
import { toast } from 'sonner'
import { Save, Mail, Eye } from 'lucide-react'

interface EditorPlantillaHTMLProps {
  plantilla?: NotificacionPlantilla | null
  onGuardado?: (plantilla: NotificacionPlantilla) => void
}

export function EditorPlantillaHTML({ plantilla, onGuardado }: EditorPlantillaHTMLProps) {
  const [id, setId] = useState<number | null>(plantilla?.id ?? null)
  const [nombre, setNombre] = useState(plantilla?.nombre ?? '')
  const [descripcion, setDescripcion] = useState(plantilla?.descripcion ?? '')
  const [tipo, setTipo] = useState(plantilla?.tipo ?? '')
  const [asunto, setAsunto] = useState(plantilla?.asunto ?? '')
  const [cuerpoHTML, setCuerpoHTML] = useState(plantilla?.cuerpo ?? '')
  const [guardando, setGuardando] = useState(false)
  const [enviandoPrueba, setEnviandoPrueba] = useState(false)
  const [emailPrueba, setEmailPrueba] = useState('')
  const [mostrarPreview, setMostrarPreview] = useState(true)

  // Tipos disponibles
  const tiposPorCategoria = {
    antes: [
      { valor: 'PAGO_5_DIAS_ANTES', label: '5 días antes' },
      { valor: 'PAGO_3_DIAS_ANTES', label: '3 días antes' },
      { valor: 'PAGO_1_DIA_ANTES', label: '1 día antes' },
    ],
    diaPago: [
      { valor: 'PAGO_DIA_0', label: 'Día de pago' },
    ],
    retraso: [
      { valor: 'PAGO_1_DIA_ATRASADO', label: '1 día de retraso' },
      { valor: 'PAGO_3_DIAS_ATRASADO', label: '3 días de retraso' },
      { valor: 'PAGO_5_DIAS_ATRASADO', label: '5 días de retraso' },
    ],
  }

  const allTipos = Object.values(tiposPorCategoria).flat()

  const handleGuardar = async () => {
    if (!nombre.trim()) {
      toast.error('El nombre es requerido')
      return
    }
    if (!tipo) {
      toast.error('Selecciona un tipo')
      return
    }
    if (!asunto.trim()) {
      toast.error('El asunto es requerido')
      return
    }
    if (!cuerpoHTML.trim()) {
      toast.error('El contenido HTML es requerido')
      return
    }

    setGuardando(true)
    try {
      const payload: any = {
        nombre: nombre.trim(),
        descripcion: descripcion.trim() || null,
        tipo,
        asunto: asunto.trim(),
        cuerpo: cuerpoHTML.trim(),
        activa: true,
        zona_horaria: 'America/Caracas',
      }

      let resultado
      if (id) {
        resultado = await notificacionService.actualizarPlantilla(id, payload)
        toast.success('Plantilla actualizada correctamente')
      } else {
        resultado = await notificacionService.crearPlantilla(payload)
        toast.success('Plantilla creada correctamente')
        setId(resultado.id)
      }

      if (onGuardado) {
        onGuardado(resultado)
      }
    } catch (error: any) {
      toast.error(error?.message || 'Error al guardar la plantilla')
    } finally {
      setGuardando(false)
    }
  }

  const handleEnviarPrueba = async () => {
    if (!emailPrueba.trim() || !emailPrueba.includes('@')) {
      toast.error('Ingresa un email válido')
      return
    }

    setEnviandoPrueba(true)
    try {
      await emailConfigService.probarConfiguracionEmail(
        emailPrueba.trim(),
        asunto.trim() || 'Prueba de plantilla',
        cuerpoHTML.trim(),
        undefined
      )
      toast.success(`Email de prueba enviado a ${emailPrueba}`)
      setEmailPrueba('')
    } catch (error: any) {
      toast.error(error?.message || 'Error al enviar email de prueba')
    } finally {
      setEnviandoPrueba(false)
    }
  }

  return (
    <div className="space-y-4">
      {/* Información General */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            {/* <FileText className="h-5 w-5" /> */}
            Información de la Plantilla
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium text-gray-700">Nombre</label>
              <Input
                placeholder="Ej: Recordatorio de pago"
                value={nombre}
                onChange={(e) => setNombre(e.target.value)}
                className="mt-1"
              />
            </div>
            <div>
              <label className="text-sm font-medium text-gray-700">Tipo</label>
              <Select value={tipo} onValueChange={setTipo}>
                <SelectTrigger className="mt-1">
                  <SelectValue placeholder="Selecciona un tipo" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__default__">Selecciona un tipo</SelectItem>
                  {Object.entries(tiposPorCategoria).map(([categoria, tipos]) => (
                    <div key={categoria}>
                      {tipos.map((t) => (
                        <SelectItem key={t.valor} value={t.valor}>
                          {t.label}
                        </SelectItem>
                      ))}
                    </div>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700">Descripción (opcional)</label>
            <Textarea
              placeholder="Describe el propósito de esta plantilla"
              value={descripcion}
              onChange={(e) => setDescripcion(e.target.value)}
              className="mt-1 h-20"
            />
          </div>

          <div>
            <label className="text-sm font-medium text-gray-700">Asunto del Email</label>
            <Input
              placeholder="Ej: Tu pago vence en 5 días"
              value={asunto}
              onChange={(e) => setAsunto(e.target.value)}
              className="mt-1"
            />
          </div>
        </CardContent>
      </Card>

      {/* Editor HTML y Preview */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            Contenido HTML
          </CardTitle>
          <CardDescription>
            Ingresa el código HTML del email. Puedes usar variables como {'{'} nombre {'}'}, {'{'} monto {'}'}, {'{'} dias_atraso {'}'}, etc.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-2 mb-4">
            <Button
              size="sm"
              variant={mostrarPreview ? 'default' : 'outline'}
              onClick={() => setMostrarPreview(true)}
              className="flex items-center gap-2"
            >
              <Eye className="h-4 w-4" />
              Preview
            </Button>
            <Button
              size="sm"
              variant={!mostrarPreview ? 'default' : 'outline'}
              onClick={() => setMostrarPreview(false)}
              className="flex items-center gap-2"
            >
              HTML
            </Button>
          </div>

          {/* Editor HTML */}
          {!mostrarPreview && (
            <div className="space-y-2">
              <Textarea
                placeholder="<html>&#10;  <body>&#10;    <p>Hola {'{'}nombre{'}'},</p>&#10;    <p>Tu pago de ${'{'}monto{'}'} vence en {'{'}dias_atraso{'}'} días.</p>&#10;  </body>&#10;</html>"
                value={cuerpoHTML}
                onChange={(e) => setCuerpoHTML(e.target.value)}
                className="font-mono text-sm h-96 bg-slate-50"
              />
              <p className="text-xs text-gray-500">
                <strong>Tip:</strong> Usa variables entre llaves como {'{'}nombre{'}'}, {'{'}cedula{'}'}, {'{'}monto{'}'}, {'{'}dias_atraso{'}'}, {'{'}numero_cuota{'}'}, {'{'}fecha_vencimiento{'}'}
              </p>
            </div>
          )}

          {/* Preview HTML */}
          {mostrarPreview && (
            <div className="bg-white border border-gray-200 rounded-lg p-6 min-h-96">
              <div
                className="prose prose-sm max-w-none"
                dangerouslySetInnerHTML={{
                  __html: cuerpoHTML || '<p style="color: #999; text-align: center;">El preview aparecerá aquí...</p>',
                }}
              />
            </div>
          )}
        </CardContent>
      </Card>

      {/* Enviar Prueba */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mail className="h-5 w-5" />
            Enviar Email de Prueba
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex gap-2">
            <Input
              type="email"
              placeholder="correo@ejemplo.com"
              value={emailPrueba}
              onChange={(e) => setEmailPrueba(e.target.value)}
              className="flex-1"
            />
            <Button
              onClick={handleEnviarPrueba}
              disabled={enviandoPrueba}
              className="bg-blue-600 hover:bg-blue-700"
            >
              {enviandoPrueba ? 'Enviando...' : 'Enviar'}
            </Button>
          </div>
          <p className="text-xs text-gray-500">
            Se enviará un email con el asunto y contenido HTML que ingresaste. Las variables se mostrarán de forma literal.
          </p>
        </CardContent>
      </Card>

      {/* Botones de Acción */}
      <div className="flex gap-2 justify-end">
        <Button
          onClick={handleGuardar}
          disabled={guardando}
          className="bg-green-600 hover:bg-green-700 flex items-center gap-2"
        >
          <Save className="h-4 w-4" />
          {guardando ? 'Guardando...' : id ? 'Actualizar Plantilla' : 'Crear Plantilla'}
        </Button>
      </div>
    </div>
  )
}