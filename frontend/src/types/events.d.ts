// Declaraciones específicas para resolver parámetros implícitos de eventos
declare global {
  // Tipos para parámetros de eventos que comúnmente causan errores implícitos
  type EventParameter = 
    | React.ChangeEvent<HTMLInputElement>
    | React.MouseEvent<HTMLButtonElement>
    | React.FormEvent<HTMLFormElement>
    | React.ChangeEvent<HTMLSelectElement>
    | React.ChangeEvent<HTMLTextAreaElement>
    | React.DragEvent<HTMLDivElement>
    | React.KeyboardEvent<HTMLInputElement>
    | React.FocusEvent<HTMLInputElement>
  
  // Tipos para funciones de callback comunes
  type EventCallback = (e: EventParameter) => void
  type ChangeCallback = (e: React.ChangeEvent<HTMLInputElement>) => void
  type ClickCallback = (e: React.MouseEvent<HTMLButtonElement>) => void
  type FormCallback = (e: React.FormEvent<HTMLFormElement>) => void
  
  // Tipos para parámetros de funciones comunes
  type FilterCallback<T> = (item: T) => boolean
  type MapCallback<T, U> = (item: T) => U
  type SortCallback<T> = (a: T, b: T) => number
  
  // Tipos para parámetros de estado
  type StateSetter<T> = (value: T | ((prev: T) => T)) => void
  type StateCallback<T> = (prev: T) => T
}

// Declaraciones para módulos que pueden causar problemas de tipos
declare module 'react' {
  export function useState<T>(initialState: T | (() => T)): [T, (value: T | ((prev: T) => T)) => void]
  export function useRef<T>(initialValue: T): { current: T }
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
}

export {}
