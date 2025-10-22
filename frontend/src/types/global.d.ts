/// <reference types="vite/client" />

// Declaraciones globales simplificadas para React y JSX
declare global {
  namespace React {
    interface ChangeEvent<T = Element> {
      target: T & EventTarget
    }
    
    interface MouseEvent<T = Element> {
      target: T & EventTarget
    }
    
    interface FormEvent<T = Element> {
      target: T & EventTarget
    }
    
    interface DragEvent<T = Element> {
      target: T & EventTarget
    }
    
    interface KeyboardEvent<T = Element> {
      target: T & EventTarget
    }
    
    interface FocusEvent<T = Element> {
      target: T & EventTarget
    }
  }
  
  // Declaraciones globales para React
  namespace React {
    type ReactNode = any
    type ComponentType<P = {}> = (props: P) => any
    type HTMLAttributes<T = Element> = any
    type InputHTMLAttributes<T = Element> = any
    type TextareaHTMLAttributes<T = Element> = any
    type ButtonHTMLAttributes<T = Element> = any
    type ThHTMLAttributes<T = Element> = any
    type TdHTMLAttributes<T = Element> = any
    type ElementRef<T> = any
    type ComponentPropsWithoutRef<T> = any
    type KeyboardEvent<T = Element> = any
    
    // Declaraciones para ErrorBoundary
    class Component<P = {}, S = {}> {
      props: P
      state: S
      setState(state: Partial<S> | ((prevState: S) => Partial<S>)): void
      forceUpdate(): void
    }
    interface ErrorInfo {
      componentStack: string
    }
    
    function forwardRef<T, P = {}>(component: (props: P, ref: React.Ref<T>) => any): any
    function useId(): string
    const StrictMode: any
  }

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

  // Declaraciones globales para hooks de React
  function useState<T>(initialState: T | (() => T)): [T, (value: T | ((prev: T) => T)) => void]
  function useRef<T>(initialValue: T | null): { current: T | null }
  function useEffect(effect: () => void | (() => void), deps?: any[]): void
  function useCallback<T extends (...args: any[]) => any>(callback: T, deps: any[]): T
  function useMemo<T>(factory: () => T, deps: any[]): T
  
  // Declaraciones para lazy loading y Suspense
  function lazy<T>(importFn: () => Promise<{ default: T }>): T
  const Suspense: any

  // Declaraciones globales para eventos
  interface EventTarget {
    value: string
    checked: boolean
  }
}

// Declaraciones para módulos externos - Solo hooks adicionales
declare module 'react' {
  export function useQuery<T = any>(queryKey: any[], queryFn: () => Promise<T>, options?: any): any
  export function useMutation<T = any>(mutationFn: (variables: any) => Promise<T>, options?: any): any
  export function map<T, U>(array: T[], callback: (item: T, index: number) => U): U[]
  export function filter<T>(array: T[], callback: (item: T, index: number) => boolean): T[]
  export function reduce<T, U>(array: T[], callback: (acc: U, item: T, index: number) => U, initial: U): U
  
  // Declaraciones para lazy loading y Suspense
  export function lazy<T>(importFn: () => Promise<{ default: T }>): T
  export const Suspense: any
}

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

// Declaraciones para componentes UI - Solo si no existen los archivos reales
declare module '@/components/ui/badge' {
  interface BadgeProps {
    variant?: 'default' | 'destructive' | 'outline' | 'secondary' | 'success' | 'warning'
    children?: React.ReactNode
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
  }
  export const SearchableSelect: React.FC<SearchableSelectProps>
}