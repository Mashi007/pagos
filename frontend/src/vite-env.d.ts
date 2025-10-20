/// <reference types="vite/client" />
/// <reference types="react" />
/// <reference types="react-dom" />

interface ImportMetaEnv {
  readonly VITE_API_URL: string
  readonly VITE_NODE_ENV: string
  readonly VITE_APP_NAME: string
  readonly VITE_APP_VERSION: string
  readonly VITE_ENABLE_NOTIFICATIONS: string
  readonly VITE_ENABLE_REPORTS: string
  readonly VITE_ENABLE_CONCILIATION: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}

// Declaraciones globales para React y JSX
declare global {
  namespace React {
    // Declarar hooks de React
    function useState<T>(initialState: T | (() => T)): [T, (value: T | ((prev: T) => T)) => void]
    function useRef<T>(initialValue: T): { current: T }
    function useEffect(effect: () => void | (() => void), deps?: any[]): void
    
    // Declarar tipos básicos
    type ReactNode = any
    type ReactElement = any
    type ComponentType<P = {}> = (props: P) => ReactElement | null
    type FC<P = {}> = ComponentType<P>
    
    // Declarar eventos
    interface ChangeEvent<T = Element> {
      target: T
    }
    
    interface DragEvent<T = Element> {
      preventDefault(): void
      dataTransfer: DataTransfer
    }
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
}

declare module 'xlsx' {
  export const read: any
  export const utils: any
}

declare module '@tanstack/react-query' {
  export const useQueryClient: any
}
