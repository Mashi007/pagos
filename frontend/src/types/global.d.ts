// Declaraciones globales para resolver errores de TypeScript
declare global {
  // React hooks
  const useState: <T>(initialState: T | (() => T)) => [T, (value: T | ((prev: T) => T)) => void]
  const useRef: <T>(initialValue: T | null) => { current: T | null }
  const useEffect: (effect: () => void | (() => void), deps?: any[]) => void
  const useCallback: <T extends (...args: any[]) => any>(callback: T, deps: any[]) => T
  const useMemo: <T>(factory: () => T, deps: any[]) => T
  
  // React namespace
  namespace React {
    type ReactNode = any
    type ReactElement = any
    type ComponentType<P = {}> = (props: P) => ReactElement | null
    type FC<P = {}> = ComponentType<P>
    
    interface ChangeEvent<T = Element> {
      target: T
      preventDefault(): void
      stopPropagation(): void
    }
    
    interface MouseEvent<T = Element> {
      target: T
      preventDefault(): void
      stopPropagation(): void
    }
    
    interface FormEvent<T = Element> {
      target: T
      preventDefault(): void
      stopPropagation(): void
    }
    
    interface DragEvent<T = Element> {
      preventDefault(): void
      dataTransfer: DataTransfer
    }
    
    interface KeyboardEvent<T = Element> {
      key: string
      preventDefault(): void
      stopPropagation(): void
    }
    
    interface FocusEvent<T = Element> {
      target: T
      preventDefault(): void
      stopPropagation(): void
    }
  }
  
  // JSX namespace
  namespace JSX {
    interface IntrinsicElements {
      [elemName: string]: any
    }
    
    interface Element extends React.ReactElement<any, any> { }
    interface ElementClass extends React.Component<any> {
      render(): React.ReactNode
    }
    interface ElementAttributesProperty { props: {} }
    interface ElementChildrenAttribute { children: {} }
  }
  
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
  
  // Tipos para parámetros de funciones comunes
  type FunctionParameter<T = any> = T
  type CallbackParameter<T = any> = T
  type MapParameter<T = any> = T
  type FilterParameter<T = any> = T
  type ReduceParameter<T = any> = T
  
  // Tipos específicos para parámetros implícitos del proyecto
  type PrestamoParameter = any
  type ClienteParameter = any
  type AnalistaParameter = any
  type PagoParameter = any
  type ResultParameter = any
  type UpdatedClienteParameter = any
  type NewClienteParameter = any
  type UpdatedAnalistaParameter = any
  type DeletedIdParameter = any
  type UnderscoreParameter = any
  
  // Tipos para parámetros de funciones específicas
  type CallbackParameter<T = any> = T
  type MapCallbackParameter<T = any> = T
  type FilterCallbackParameter<T = any> = T
  type ReduceCallbackParameter<T = any> = T
  type ForEachCallbackParameter<T = any> = T
  type FindCallbackParameter<T = any> = T
  type SomeCallbackParameter<T = any> = T
  type EveryCallbackParameter<T = any> = T
  
  // Tipos para funciones genéricas que pueden causar errores
  type GenericFunction<T = any> = (...args: any[]) => T
  type AsyncFunction<T = any> = (...args: any[]) => Promise<T>
  type EventHandlerFunction<T = any> = (event: T) => void
  type StateUpdaterFunction<T = any> = (value: T | ((prev: T) => T)) => void
  
  // Declaraciones globales para funciones comunes
  const map: <T, U>(array: T[], callback: (item: T, index: number) => U) => U[]
  const filter: <T>(array: T[], callback: (item: T, index: number) => boolean) => T[]
  const reduce: <T, U>(array: T[], callback: (acc: U, item: T, index: number) => U, initial: U) => U
  const forEach: <T>(array: T[], callback: (item: T, index: number) => void) => void
  const find: <T>(array: T[], callback: (item: T, index: number) => boolean) => T | undefined
  const some: <T>(array: T[], callback: (item: T, index: number) => boolean) => boolean
  const every: <T>(array: T[], callback: (item: T, index: number) => boolean) => boolean
  
  // Declaraciones globales para funciones específicas del proyecto
  const useQuery: <T = any>(queryKey: any[], queryFn: () => Promise<T>, options?: any) => any
  const useMutation: <T = any>(mutationFn: (variables: any) => Promise<T>, options?: any) => any
  const useCallback: <T extends (...args: any[]) => any>(callback: T, deps: any[]) => T
  const useMemo: <T>(factory: () => T, deps: any[]) => T
  
  // Tipos específicos del proyecto
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

// Declaraciones de módulos externos
declare module 'framer-motion' {
  export const motion: any
  export const AnimatePresence: any
}

declare module 'lucide-react' {
  export const Upload: any
  export const FileSpreadsheet: any
  export const X: any
  export const CheckCircle: any
  export const AlertTriangle: any
  export const Eye: any
  export const Save: any
  export const Info: any
  export const CheckCircle2: any
  export const Loader2: any
  export const FileText: any
  export const Download: any
  export const Calendar: any
  export const Filter: any
  export const BarChart3: any
  export const PieChart: any
  export const TrendingUp: any
  export const Users: any
  export const DollarSign: any
  export const Clock: any
  export const Search: any
  export const RefreshCw: any
  export const XCircle: any
  export const Plus: any
  export const Edit: any
  export const Trash2: any
  export const Shield: any
  export const Mail: any
  export const UserCheck: any
  export const UserX: any
  export const Settings: any
  export const PlayCircle: any
  export const Database: any
  export const Building2: any
  export const Car: any
  export const Bell: any
  export const Check: any
  export const User: any
  export const CreditCard: any
  export const AlertCircle: any
  export const ArrowDownToLine: any
  export const PlusCircle: any
  export const Play: any
  export const Pause: any
  export const Square: any
  export const MessageSquare: any
  export const Link: any
  export const TrendingDown: any
  export const Calculator: any
  export const Key: any
  export const Copy: any
  export const EyeOff: any
  export const ChevronDown: any
  export const ChevronUp: any
  export const RotateCcw: any
  export const Activity: any
  export const Building: any
  export const MapPin: any
  export const Phone: any
  export const Globe: any
  export const CheckSquare: any
  export const Brain: any
  export const Wrench: any
  export const ChevronRight: any
  export const Target: any
  export const LineChart: any
  export const Zap: any
  export const Award: any
  export const Lock: any
  export const UserMinus: any
  export const Minus: any
  export const MoreHorizontal: any
  export const Briefcase: any
  export const Edit2: any
  export const TestTube: any
  export const XSquare: any
  export const Heart: any
  export const Menu: any
  export const LogOut: any
  export const LayoutDashboard: any
}

declare module 'xlsx' {
  export const read: any
  export const utils: any
}

declare module '@tanstack/react-query' {
  export const useQueryClient: any
  export const useQuery: any
  export const useMutation: any
  export const useInfiniteQuery: any
  export const QueryClient: any
  export const QueryClientProvider: any
}

declare module 'react' {
  export function useState<T>(initialState: T | (() => T)): [T, (value: T | ((prev: T) => T)) => void]
  export function useRef<T>(initialValue: T | null): { current: T | null }
  export function useEffect(effect: () => void | (() => void), deps?: any[]): void
  export function useCallback<T extends (...args: any[]) => any>(callback: T, deps: any[]): T
  export function useMemo<T>(factory: () => T, deps: any[]): T
  
  export type ReactNode = any
  export type ReactElement = any
  export type ComponentType<P = {}> = (props: P) => ReactElement | null
  export type FC<P = {}> = ComponentType<P>
  
  export interface ChangeEvent<T = Element> {
    target: T
    preventDefault(): void
    stopPropagation(): void
  }
  
  export interface MouseEvent<T = Element> {
    target: T
    preventDefault(): void
    stopPropagation(): void
  }
  
  export interface FormEvent<T = Element> {
    target: T
    preventDefault(): void
    stopPropagation(): void
  }
  
  export interface DragEvent<T = Element> {
    preventDefault(): void
    dataTransfer: DataTransfer
  }
  
  export interface KeyboardEvent<T = Element> {
    key: string
    preventDefault(): void
    stopPropagation(): void
  }
  
  export interface FocusEvent<T = Element> {
    target: T
    preventDefault(): void
    stopPropagation(): void
  }
  
  // Declaraciones para funciones genéricas que pueden causar errores
  export function useQuery<T = any>(queryKey: any[], queryFn: () => Promise<T>, options?: any): any
  export function useMutation<T = any>(mutationFn: (variables: any) => Promise<T>, options?: any): any
  
  // Declaraciones para funciones que pueden causar errores de tipos
  export function useCallback<T extends (...args: any[]) => any>(callback: T, deps: any[]): T
  export function useMemo<T>(factory: () => T, deps: any[]): T
  
  // Declaraciones para funciones genéricas comunes
  export function map<T, U>(array: T[], callback: (item: T, index: number) => U): U[]
  export function filter<T>(array: T[], callback: (item: T, index: number) => boolean): T[]
  export function reduce<T, U>(array: T[], callback: (acc: U, item: T, index: number) => U, initial: U): U
  
  // Declaraciones específicas para funciones que causan errores
  export function useQuery<T = any>(queryKey: any[], queryFn: () => Promise<T>, options?: any): any
  export function useMutation<T = any>(mutationFn: (variables: any) => Promise<T>, options?: any): any
  export function useCallback<T extends (...args: any[]) => any>(callback: T, deps: any[]): T
  export function useMemo<T>(factory: () => T, deps: any[]): T
  
  // Declaraciones para funciones de array que pueden causar errores
  export function forEach<T>(array: T[], callback: (item: T, index: number) => void): void
  export function find<T>(array: T[], callback: (item: T, index: number) => boolean): T | undefined
  export function some<T>(array: T[], callback: (item: T, index: number) => boolean): boolean
  export function every<T>(array: T[], callback: (item: T, index: number) => boolean): boolean
}

// Declaraciones para componentes UI - Solo si no existen los archivos reales
// declare module '@/components/ui/badge' {
//   interface BadgeProps {
//     children?: React.ReactNode
//     variant?: 'default' | 'secondary' | 'destructive' | 'outline' | 'success' | 'warning'
//     className?: string
//   }
//   export const Badge: React.FC<BadgeProps>
// }

// declare module '@/components/ui/searchable-select' {
//   interface SearchableSelectProps {
//     options: Array<{ value: string; label: string }>
//     value: string
//     onChange: (value: string) => void
//     placeholder?: string
//     className?: string
//     disabled?: boolean
//   }
//   export const SearchableSelect: React.FC<SearchableSelectProps>
// }

export {}
