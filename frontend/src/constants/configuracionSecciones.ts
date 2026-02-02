import type { ComponentType } from 'react'
import {
  Globe,
  Wrench,
  Bell,
  Mail,
  MessageSquare,
  FileText,
  Calendar,
  Database,
  DollarSign,
  Brain,
  CheckSquare,
  Building,
  Users,
  Car,
} from 'lucide-react'

/** Tipo para iconos Lucide (componente que acepta props SVG) */
type IconComponent = ComponentType<{ className?: string; size?: number }>

export interface SeccionItem {
  id: string
  nombre: string
  icono: IconComponent
  href?: string
}

export interface SeccionConSubmenu {
  id: string
  nombre: string
  icono: IconComponent
  submenu: true
  items: SeccionItem[]
}

export type SeccionConfig = SeccionItem | SeccionConSubmenu

export const SECCIONES_CONFIGURACION: SeccionConfig[] = [
  { id: 'general', nombre: 'General', icono: Globe },
  {
    id: 'herramientas',
    nombre: 'Herramientas',
    icono: Wrench,
    submenu: true,
    items: [
      { id: 'notificaciones', nombre: 'Notificaciones', icono: Bell },
      { id: 'emailConfig', nombre: 'Configuración Email', icono: Mail },
      { id: 'whatsappConfig', nombre: 'Configuración WhatsApp', icono: MessageSquare },
      { id: 'plantillas', nombre: 'Plantillas', icono: FileText, href: '/herramientas/plantillas' },
      { id: 'scheduler', nombre: 'Programador', icono: Calendar, href: '/scheduler' },
      { id: 'programador', nombre: 'Programador (Config)', icono: Calendar },
      { id: 'auditoria', nombre: 'Auditoría', icono: FileText },
    ],
  },
  { id: 'baseDatos', nombre: 'Base de Datos', icono: Database },
  { id: 'facturacion', nombre: 'Facturación', icono: DollarSign },
  { id: 'inteligenciaArtificial', nombre: 'Inteligencia Artificial', icono: Brain },
  { id: 'validadores', nombre: 'Validadores', icono: CheckSquare },
  { id: 'concesionarios', nombre: 'Concesionarios', icono: Building },
  { id: 'analistas', nombre: 'Asesores', icono: Users },
  { id: 'modelosVehiculos', nombre: 'Modelos de Vehículos', icono: Car },
  { id: 'usuarios', nombre: 'Usuarios', icono: Users },
]

export const NOMBRES_SECCION_ESPECIAL: Record<string, { nombre: string; icono: IconComponent }> = {
  emailConfig: { nombre: 'Configuración Email', icono: Mail },
  whatsappConfig: { nombre: 'Configuración WhatsApp', icono: MessageSquare },
  aiConfig: { nombre: 'Configuración AI', icono: Brain },
}

export function findSeccionById(
  secciones: SeccionConfig[],
  id: string
): SeccionItem | null {
  for (const s of secciones) {
    if ('submenu' in s && s.submenu && s.items) {
      const found = s.items.find((i) => i.id === id)
      if (found) return found
    }
    if ((s as SeccionItem).id === id) return s as SeccionItem
  }
  return null
}
