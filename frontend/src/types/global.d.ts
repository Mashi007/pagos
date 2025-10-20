// Declaraciones globales para resolver errores de TypeScript
declare global {
  // React hooks
  const useState: <T>(initialState: T | (() => T)) => [T, (value: T | ((prev: T) => T)) => void]
  const useRef: <T>(initialValue: T) => { current: T }
  const useEffect: (effect: () => void | (() => void), deps?: any[]) => void
  
  // React namespace
  namespace React {
    type ReactNode = any
    type ReactElement = any
    type ComponentType<P = {}> = (props: P) => ReactElement | null
    type FC<P = {}> = ComponentType<P>
    
    interface ChangeEvent<T = Element> {
      target: T
    }
    
    interface DragEvent<T = Element> {
      preventDefault(): void
      dataTransfer: DataTransfer
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
}

declare module 'xlsx' {
  export const read: any
  export const utils: any
}

declare module '@tanstack/react-query' {
  export const useQueryClient: any
}

declare module 'react' {
  export function useState<T>(initialState: T | (() => T)): [T, (value: T | ((prev: T) => T)) => void]
  export function useRef<T>(initialValue: T): { current: T }
  export function useEffect(effect: () => void | (() => void), deps?: any[]): void
  
  export type ReactNode = any
  export type ReactElement = any
  export type ComponentType<P = {}> = (props: P) => ReactElement | null
  export type FC<P = {}> = ComponentType<P>
  
  export interface ChangeEvent<T = Element> {
    target: T
  }
  
  export interface DragEvent<T = Element> {
    preventDefault(): void
    dataTransfer: DataTransfer
  }
}

// Declaraciones para componentes UI
declare module '@/components/ui/badge' {
  interface BadgeProps {
    children?: React.ReactNode
    variant?: 'default' | 'secondary' | 'destructive' | 'outline' | 'success' | 'warning'
    className?: string
  }
  export const Badge: React.FC<BadgeProps>
}

declare module '@/components/ui/searchable-select' {
  interface SearchableSelectProps {
    options: Array<{ value: string; label: string }>
    value: string
    onChange: (value: string) => void
    placeholder?: string
    className?: string
    disabled?: boolean
  }
  export const SearchableSelect: React.FC<SearchableSelectProps>
}

export {}
