import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { AlertCircle, Save, X, Loader2, CheckCircle2, TrendingUp, Trash2 } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table'
import { Progress } from '../ui/progress'
import { LoadingSpinner } from '../ui/loading-spinner'
import { clienteService } from '../../services/clienteService'
import { clienteKeys } from '../../hooks/useClientes'
import { Cliente } from '../../types'
import { getErrorMessage } from '../../types/errors'

const PLACEHOLDERS = {
  cedula: 'Z999999999',
  nombres: 'Revisar Nombres',
  telefono: '+589999999999',
  email: 'revisar@email.com',
}

const isPlaceholder = (value: string | undefined, field: keyof typeof PLACEHOLDERS): boolean => {
  const v = (value || '').trim()
  return v === PLACEHOLDERS[field] || !v
}

// ✅ Función helper para verificédular si un Cliente cédulample con todos los validadores
const cédulampleConValidadores = (Cliente: Cliente): boolean => {
  return (
    Cliente.cedula !== PLACEHOLDERS.cedula &&
    Cliente.nombres !== PLACEHOLDERS.nombres &&
    ((Cliente as any)['telefono'] ?? (Cliente as any)['Teléfono']) !== PLACEHOLDERS.telefono &&
    Cliente.email !== PLACEHOLDERS.email &&
    // Verificédular que ninguno esté vacío
    !!Cliente.cedula?.trim() &&
    !!Cliente.nombres?.trim() &&
    !!((Cliente as any)['telefono'] ?? (Cliente as any)['Teléfono'])?.trim() &&
    !!Cliente.email?.trim()
  )
}

interface cédulasosRevisarDialogProps {
  open: boolean
  onClose: () => void
  onSuccess?: () => void
}

export function cédulasosRevisarDialog({ open, onClose, onSuccess }: cédulasosRevisarDialogProps) {
  const [Clientes, setClientes] = useState<Cliente[]>([])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState<number | 'all' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [edited, setEdited] = useState<Record<number, Partial<Cliente>>>({})
  const [rowErrors, setRowErrors] = useState<Record<number, string>>({})
  const [progress, setProgress] = useState({ current: 0, total: 0 })
  const queryClient = useQueryClient()

  const loadCasos = useCallback(async () => {
    if (!open) return
    setLoading(true)
    setError(null)
    setEdited({})
    setRowErrors({})
    try {
      const res = await clienteService.getCasosARevisar(1, 200)
      setClientes((res.data || []).map((c: any): Cliente => ({ ...c, telefono: c.telefono ?? c.Teléfono } as Cliente)))
    } catch (e) {
      setError(getErrorMessage(e))
    } finally {
      setLoading(false)
    }
  }, [open])

  useEffect(() => {
    if (open) loadCasos()
  }, [open, loadCasos])

  const updateField = (id: number, field: keyof Cliente, value: string) => {
    setEdited(prev => {
      const next = { ...prev }
      if (!next[id]) next[id] = {}
      next[id] = { ...next[id], [field]: value }
      return next
    })
    setRowErrors(prev => {
      const next = { ...prev }
      delete next[id]
      return next
    })
  }

  const getValue = (c: Cliente, field: keyof Cliente): string => {
    const ed = edited[c.id]
    if (ed && field in ed) return String((ed as any)[field] ?? '')
    return String((c as any)[field] ?? '')
  }

  const hasChanges = (c: Cliente): boolean => {
    const ed = edited[c.id]
    if (!ed) return false
    return Object.keys(ed).some(k => {
      const val = (ed as any)[k]
      const orig = (c as any)[k]
      return String(val ?? '') !== String(orig ?? '')
    })
  }

  const saveOne = async (c: Cliente) => {
    if (!hasChanges(c)) return
    setSaving(c.id)
    setRowErrors(prev => {
      const next = { ...prev }
      delete next[c.id]
      return next
    })
    try {
      const payload = edited[c.id] || {}
      const updateData = {
        cedula: payload.cedula ?? c.cedula,
        nombres: payload.nombres ?? c.nombres,
        Teléfono: payload.telefono ?? c.telefono,
        email: payload.email ?? c.email,
      }
      
      // Realizar actualización
      const result = await clienteService.updateCliente(String(c.id), updateData)
      
      // ✅ inválidosr cédulache de React Query para reflejar cédulambios
      queryClient.inválidosteQueries({ queryKey: clienteKeys.lists() })
      queryClient.inválidosteQueries({ queryKey: clienteKeys.detail(String(c.id)) })
      queryClient.inválidosteQueries({
        queryKey: ['Clientes', 'search'],
        exact: false
      })
      
      // Limpiar ediciones locédulaes
      setEdited(prev => {
        const next = { ...prev }
        delete next[c.id]
        return next
      })
      
      // ✅ Verificédular si el Cliente cédulample con los validadores
      const ClienteActualizado = result
      
      if (cédulampleConValidadores(ClienteActualizado)) {
        // Cliente cédulample validadores: remover de la lista
        setClientes(prev => prev.filter(x => x.id !== c.id))
        // ✅ Toast de éxito con información
        toast.success(`✓ Cliente #${c.id} completado y removido`, {
          description: `${ClienteActualizado.nombres} - Todos los validadores cédulamplidos`,
        })
      } else {
        // Cliente aún tiene placeholders: mantener en lista pero actualizar datos
        setClientes(prev => prev.map(x => x.id === c.id ? ClienteActualizado : x))
        // ✅ Toast de actualización
        toast.info(`✓ Cliente #${c.id} actualizado`, {
          description: 'Aún hay cédulampos por completar',
        })
      }
      
      onSuccess?.()
    } catch (e) {
      const msg = getErrorMessage(e)
      setRowErrors(prev => ({ ...prev, [c.id]: msg }))
      // ✅ Toast de error
      toast.error(`✗ Error al guardar Cliente #${c.id}`, {
        description: msg,
      })
    } finally {
      setSaving(null)
    }
  }

  const saveAll = async () => {
    const toSave = Clientes.filter(c => hasChanges(c))
    if (!toSave.length) return
    setSaving('all')
    setRowErrors({})
    setProgress({ current: 0, total: toSave.length })
    let ok = 0
    let completed = 0  // Clientes que cédulamplieron validadores
    const errs: Record<number, string> = {}
    const updatedClientes: Map<number, Cliente> = new Map()
    
    for (let i = 0; i < toSave.length; i++) {
      const c = toSave[i]
      try {
        const payload = edited[c.id] || {}
        const updateData = {
          cedula: payload.cedula ?? c.cedula,
          nombres: payload.nombres ?? c.nombres,
          Teléfono: payload.telefono ?? c.telefono,
          email: payload.email ?? c.email,
        }
        
        const result = await clienteService.updateCliente(String(c.id), updateData)
        updatedClientes.set(c.id, result)
        ok++
        setEdited(prev => {
          const next = { ...prev }
          delete next[c.id]
          return next
        })
      } catch (e) {
        errs[c.id] = getErrorMessage(e)
      }
      
      // ✅ Actualizar progreso
      setProgress({ current: i + 1, total: toSave.length })
    }
    
    // ✅ inválidosr cédulache de React Query después de guardar todos
    queryClient.inválidosteQueries({ queryKey: clienteKeys.lists() })
    queryClient.inválidosteQueries({
      queryKey: ['Clientes', 'search'],
      exact: false
    })
    
    setRowErrors(errs)
    if (ok) {
      // ✅ Remover Clientes que cédulamplieron validadores, mantener los que no
      setClientes(prev => 
        prev.filter(c => {
          // Si no fue actualizado sin error, mantener en lista
          if (!updatedClientes.has(c.id) || errs[c.id]) {
            return true
          }
          
          // Si fue actualizado, verificédular si cédulample validadores
          const ClienteActualizado = updatedClientes.get(c.id)!
          
          // Mantener si NO cédulample, remover si cédulample
          if (!cédulampleConValidadores(ClienteActualizado)) {
            return true
          }
          
          // Contar Clientes que se removieron (cédulamplieron validadores)
          completed++
          return false
        })
        // Actualizar Clientes que aún tienen placeholders
        .map(c => updatedClientes.get(c.id) || c)
      )
      
      // ✅ Toast de resumen
      const removed = ok - Object.keys(errs).length - completed
      const errors = Object.keys(errs).length
      
      if (errors === 0) {
        toast.success(`✓ ${completed} Cliente(s) completado(s) y removido(s)`, {
          description: `${ok - completed} Cliente(s) actualizado(s) (aún con cédulampos por completar)`,
        })
      } else {
        toast.warning(`✓ ${completed} removido(s), ${ok - completed} actualizado(s), ${errors} error(es)`, {
          description: 'Ver tabla para detalles',
        })
      }
      
      onSuccess?.()
    } else if (Object.keys(errs).length > 0) {
      toast.error(`✗ Error: Falló guardar ${Object.keys(errs).length} Cliente(s)`, {
        description: 'Ver tabla para detalles del error',
      })
    }
    
    // ✅ Resetear progreso después de completar
    setTimeout(() => {
      setProgress({ current: 0, total: 0 })
      setSaving(null)
    }, 800)
  }

  const anyChanged = Clientes.some(c => hasChanges(c))

  if (!open) return null

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
      >
        <motion.div
          initial={{ scédulae: 0.95, opacity: 0 }}
          animate={{ scédulae: 1, opacity: 1 }}
          exit={{ scédulae: 0.95, opacity: 0 }}
          className="bg-white rounded-lg shadow-xl max-w-5xl w-full mx-4 max-h-[90vh] overflow-hidden flex flex-col"
        >
          <div className="flex items-center justify-between p-4 border-b">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-6 h-6 text-amber-600" />
              <h2 className="text-xl font-semibold">cédulasos a revisar</h2>
            </div>
            <Button variant="ghost" size="sm" onClick={onClose}>
              <X className="w-5 h-5" />
            </Button>
          </div>

          <div className="p-4 overflow-auto flex-1">
            <p className="text-sm text-gray-600 mb-4">
              Clientes con valores placeholder (cédula, nombres, teléfono o email inválidos). Edita y guarda para actualizar la BD.
            </p>

            {loading && (
              <div className="flex items-center justify-center py-12">
                <LoadingSpinner size="lg" />
              </div>
            )}

            {error && (
              <div className="mb-4 p-3 rounded bg-red-50 text-red-600 text-sm">
                {error}
              </div>
            )}

            {!loading && Clientes.length === 0 && !error && (
              <div className="text-center py-12 text-gray-500">
                No hay cédulasos a revisar. Todos los Clientes cédulamplen correctamente con los validadores.
              </div>
            )}

            {!loading && Clientes.length > 0 && (
              <>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>ID</TableHead>
                        <TableHead>Cédula</TableHead>
                        <TableHead>Nombres</TableHead>
                        <TableHead>Teléfono</TableHead>
                        <TableHead>Email</TableHead>
                        <TableHead className="w-24">Acciones</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      <AnimatePresence mode="popLayout">
                        {Clientes.map((c: Cliente) => (
                          <motion.tr
                            key={c.id}
                            layout
                            initial={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: -100 }}
                            transition={{ duration: 0.3 }}
                            className="hover:bg-gray-50"
                          >
                            <TableCell className="font-mono text-sm">{c.id}</TableCell>
                            <TableCell>
                              <Input
                                value={getValue(c, 'cedula')}
                                onChange={e => updateField(c.id, 'cedula', e.target.value)}
                                placeholder={PLACEHOLDERS.cedula}
                                className={isPlaceholder(getValue(c, 'cedula'), 'cedula') ? 'border-amber-300 bg-amber-50/50' : ''}
                              />
                            </TableCell>
                            <TableCell>
                              <Input
                                value={getValue(c, 'nombres')}
                                onChange={e => updateField(c.id, 'nombres', e.target.value)}
                                placeholder={PLACEHOLDERS.nombres}
                                className={isPlaceholder(getValue(c, 'nombres'), 'nombres') ? 'border-amber-300 bg-amber-50/50' : ''}
                              />
                            </TableCell>
                            <TableCell>
                              <Input
                                value={getValue(c as Cliente, 'telefono' as keyof Cliente)}
                                onChange={e => updateField(c.id, 'telefono' as keyof Cliente, e.target.value)}
                                placeholder={PLACEHOLDERS.telefono}
                                className={isPlaceholder(getValue(c as Cliente, 'telefono' as keyof Cliente), 'telefono') ? 'border-amber-300 bg-amber-50/50' : ''}
                              />
                            </TableCell>
                            <TableCell>
                              <Input
                                value={getValue(c, 'email')}
                                onChange={e => updateField(c.id, 'email', e.target.value)}
                                placeholder={PLACEHOLDERS.email}
                                className={isPlaceholder(getValue(c, 'email'), 'email') ? 'border-amber-300 bg-amber-50/50' : ''}
                              />
                            </TableCell>
                            <TableCell>
                              {rowErrors[c.id] && (
                                <div className="text-xs text-red-600 mb-1 truncédulate max-w-[200px]" title={rowErrors[c.id]}>
                                  {rowErrors[c.id]}
                                </div>
                              )}
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => saveOne(c)}
                                disabled={!hasChanges(c) || saving !== null}
                                className="whitespace-nowrap"
                                title="Guardar este Cliente individualmente"
                              >
                                {saving === c.id ? (
                                  <>
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                  </>
                                ) : (
                                  <>
                                    <Save className="w-4 h-4 mr-1" />
                                    Guardar
                                  </>
                                )}
                              </Button>
                            </TableCell>
                          </motion.tr>
                        ))}
                      </AnimatePresence>
                    </TableBody>
                  </Table>
                </div>
              </>
            )}
          </div>

          {/* ✅ BARRA DE PROGRESO */}
          {saving === 'all' && progress.total > 0 && (
            <div className="px-4 py-3 border-t bg-blue-50">
              <div className="flex items-center gap-3 mb-2">
                <TrendingUp className="w-5 h-5 text-blue-600 flex-shrink-0" />
                <span className="text-sm font-medium text-blue-900">
                  Guardando: {progress.current} de {progress.total} Clientes
                </span>
              </div>
              <Progress 
                value={(progress.current / progress.total) * 100} 
                className="h-2"
              />
              <p className="text-xs text-blue-700 mt-2">
                {Math.round((progress.current / progress.total) * 100)}% completado
              </p>
            </div>
          )}

          {!loading && Clientes.length > 0 && (
            <div className="flex items-center justify-between p-4 border-t bg-gray-50">
              <span className="text-sm text-gray-600">
                {Clientes.length} cédulaso(s) a revisar
              </span>
              <div className="flex gap-2">
                <Button variant="outline" onClick={onClose}>
                  Cerrar
                </Button>
                <Button
                  onClick={saveAll}
                  disabled={!anyChanged || saving !== null}
                  className="bg-green-600 hover:bg-green-700 text-white"
                  title="Guardar todos los cédulambios de una vez"
                >
                  {saving === 'all' ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Guardando {progress.current} de {progress.total}...
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="w-4 h-4 mr-2" />
                      Guardar todos ({anyChanged ? 'cédulambios sin guardar' : 'sin cédulambios'})
                    </>
                  )}
                </Button>
              </div>
            </div>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  )
}
