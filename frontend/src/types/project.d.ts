// Declaraciones para resolver tipos implícitos
declare global {
  // Tipos para eventos comunes
  interface EventTarget {
    value: string
    checked: boolean
  }
  
  // Tipos para parámetros comunes
  type EventHandler = (e: React.ChangeEvent<HTMLInputElement>) => void
  type DragEventHandler = (e: React.DragEvent<HTMLDivElement>) => void
  type ClickEventHandler = (e: React.MouseEvent<HTMLButtonElement>) => void
  type FormEventHandler = (e: React.FormEvent<HTMLFormElement>) => void
  type ChangeEventHandler = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => void
  
  // Tipos para funciones de callback comunes
  type SetStateFunction<T> = (value: T | ((prev: T) => T)) => void
  type FilterFunction<T> = (item: T) => boolean
  type MapFunction<T, U> = (item: T) => U
  
  // Tipos para parámetros de eventos implícitos
  type EventParameter = React.ChangeEvent<HTMLInputElement> | React.MouseEvent<HTMLButtonElement> | React.FormEvent<HTMLFormElement>
}

// Declaraciones para tipos específicos del proyecto
declare global {
  interface Cliente {
    id: number
    cedula: string
    nombres: string
    apellidos: string
    telefono: string
    email: string
    direccion: string
    fecha_nacimiento: string
    ocupacion: string
    modelo_vehiculo: string
    concesionario: string
    analista: string
    total_financiamiento: number
    cuota_inicial: number
    numero_amortizaciones: number
    modalidad_pago: string
    fecha_entrega: string
    estado: string
    activo: boolean
    notas: string
  }
  
  interface Usuario {
    id: number
    email: string
    nombre: string
    apellido: string
    cargo?: string
    is_admin: boolean
    is_active: boolean
    created_at: string
    updated_at?: string
    last_login?: string
  }
  
  interface Validator {
    id: number
    nombre: string
    tipo: string
    activo: boolean
    configuracion: any
  }
}

export {}
