import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { AlertCircle, Save, X, Loader2, CheckCircle2 } from 'lucide-react'
import { useQueryClient } from '@tanstack/react-query'
import { Button } from '../ui/button'
import { Input } from '../ui/input'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table'
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

// ✅ Función helper para verificar si un cliente cumple con todos los validadores
const cumpleConValidadores = (cliente: Cliente): boolean => {
  return (
    cliente.cedula !== PLACEHOLDERS.cedula &&
    cliente.nombres !== PLACEHOLDERS.nombres &&
    cliente.telefono !== PLACEHOLDERS.telefono &&
    cliente.email !== PLACEHOLDERS.email &&
    // Verificar que ninguno esté vacío
    !!cliente.cedula?.trim() &&
    !!cliente.nombres?.trim() &&
    !!cliente.telefono?.trim() &&
    !!cliente.email?.trim()
  )
}

interface CasosRevisarDialogProps {
  open: boolean
  onClose: () => void
  onSuccess?: () => void
}

export function CasosRevisarDialog({ open, onClose, onSuccess }: CasosRevisarDialogProps) {
  const [clientes, setClientes] = useState<Cliente[]>([])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState<number | 'all' | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [edited, setEdited] = useState<Record<number, Partial<Cliente>>>({})
  const [rowErrors, setRowErrors] = useState<Record<number, string>>({})
  const queryClient = useQueryClient()

  const loadCasos = useCallback(async () => {
    if (!open) return
    setLoading(true)
    setError(null)
    setEdited({})
    setRowErrors({})
    try {
      const res = await clienteService.getCasosARevisar(1, 200)
      setClientes(res.data || [])
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
        telefono: payload.telefono ?? c.telefono,
        email: payload.email ?? c.email,
      }
      
      // Realizar actualización
      const result = await clienteService.updateCliente(String(c.id), updateData)
      
      // ✅ Invalidar cache de React Query para reflejar cambios
      queryClient.invalidateQueries({ queryKey: clienteKeys.lists() })
      queryClient.invalidateQueries({ queryKey: clienteKeys.detail(String(c.id)) })
      queryClient.invalidateQueries({
        queryKey: ['clientes', 'search'],
        exact: false
      })
      
      // Limpiar ediciones locales
      setEdited(prev => {
        const next = { ...prev }
        delete next[c.id]
        return next
      })
      
      // ✅ Verificar si el cliente cumple con los validadores
      // Remover SOLO si no tiene más valores placeholder
      const clienteActualizado = result
      
      if (cumpleConValidadores(clienteActualizado)) {
        // Cliente cumple validadores: remover de la lista
        setClientes(prev => prev.filter(x => x.id !== c.id))
      } else {
        // Cliente aún tiene placeholders: mantener en lista pero actualizar datos
        setClientes(prev => prev.map(x => x.id === c.id ? clienteActualizado : x))
      }
      
      onSuccess?.()
    } catch (e) {
      const msg = getErrorMessage(e)
      setRowErrors(prev => ({ ...prev, [c.id]: msg }))
    } finally {
      setSaving(null)
    }
  }

  const saveAll = async () => {
    const toSave = clientes.filter(c => hasChanges(c))
    if (!toSave.length) return
    setSaving('all')
    setRowErrors({})
    let ok = 0
    const errs: Record<number, string> = {}
    const updatedClientes: Map<number, Cliente> = new Map()
    
    for (const c of toSave) {
      try {
        const payload = edited[c.id] || {}
        const updateData = {
          cedula: payload.cedula ?? c.cedula,
          nombres: payload.nombres ?? c.nombres,
          telefono: payload.telefono ?? c.telefono,
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
    }
    
    // ✅ Invalidar cache de React Query después de guardar todos
    queryClient.invalidateQueries({ queryKey: clienteKeys.lists() })
    queryClient.invalidateQueries({
      queryKey: ['clientes', 'search'],
      exact: false
    })
    
    setRowErrors(errs)
    if (ok) {
      // ✅ Remover clientes que cumplieron validadores, mantener los que no
      setClientes(prev => 
        prev.filter(c => {
          // Si no fue actualizado sin error, mantener en lista
          if (!updatedClientes.has(c.id) || errs[c.id]) {
            return true
          }
          
          // Si fue actualizado, verificar si cumple validadores
          const clienteActualizado = updatedClientes.get(c.id)!
          
          // Mantener si NO cumple, remover si cumple
          return !cumpleConValidadores(clienteActualizado)
        })
        // Actualizar clientes que aún tienen placeholders
        .map(c => updatedClientes.get(c.id) || c)
      )
      onSuccess?.()
    }
    setSaving(null)
  }

  const anyChanged = clientes.some(c => hasChanges(c))

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
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          className="bg-white rounded-lg shadow-xl max-w-5xl w-full mx-4 max-h-[90vh] overflow-hidden flex flex-col"
        >
          <div className="flex items-center justify-between p-4 border-b">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-6 h-6 text-amber-600" />
              <h2 className="text-xl font-semibold">Casos a revisar</h2>
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

            {!loading && clientes.length === 0 && !error && (
              <div className="text-center py-12 text-gray-500">
                No hay casos a revisar. Todos los clientes cumplen correctamente con los validadores.
              </div>
            )}

            {!loading && clientes.length > 0 && (
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
                      {clientes.map(c => (
                        <TableRow key={c.id}>
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
                              value={getValue(c, 'telefono')}
                              onChange={e => updateField(c.id, 'telefono', e.target.value)}
                              placeholder={PLACEHOLDERS.telefono}
                              className={isPlaceholder(getValue(c, 'telefono'), 'telefono') ? 'border-amber-300 bg-amber-50/50' : ''}
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
                              <div className="text-xs text-red-600 mb-1 truncate max-w-[200px]" title={rowErrors[c.id]}>
                                {rowErrors[c.id]}
                              </div>
                            )}
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => saveOne(c)}
                              disabled={!hasChanges(c) || saving !== null}
                            >
                              {saving === c.id ? (
                                <Loader2 className="w-4 h-4 animate-spin" />
                              ) : (
                                <>
                                  <Save className="w-4 h-4 mr-1" />
                                  Guardar
                                </>
                              )}
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </>
            )}
          </div>

          {!loading && clientes.length > 0 && (
            <div className="flex items-center justify-between p-4 border-t bg-gray-50">
              <span className="text-sm text-gray-600">
                {clientes.length} caso(s) a revisar
              </span>
              <div className="flex gap-2">
                <Button variant="outline" onClick={onClose}>
                  Cerrar
                </Button>
                <Button
                  onClick={saveAll}
                  disabled={!anyChanged || saving !== null}
                >
                  {saving === 'all' ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Guardando...
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="w-4 h-4 mr-2" />
                      Guardar todos
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
