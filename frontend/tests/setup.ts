/**
 * Setup de Testing - Frontend
 * Configuración común para todas las pruebas
 */
import { expect, afterEach, vi, beforeEach } from 'vitest'
import { cleanup } from '@testing-library/react'
import * as matchers from '@testing-library/jest-dom/matchers'

expect.extend(matchers)

afterEach(() => {
  cleanup()
})

const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
}

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
})

const sessionStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
}

Object.defineProperty(window, 'sessionStorage', {
  value: sessionStorageMock,
})

global.fetch = vi.fn()

/** Simula viewport ancho (px) para media queries de Tailwind / useIsMobile. */
function mediaQueryMatches(query: string, viewportWidth = 1280): boolean {
  if (query.includes('prefers-reduced-motion')) return false
  const min = query.match(/min-width:\s*(\d+)/)
  if (min) return viewportWidth >= parseInt(min[1], 10)
  const max = query.match(/max-width:\s*(\d+)/)
  if (max) return viewportWidth <= parseInt(max[1], 10)
  return false
}

const matchMediaMock = vi.fn().mockImplementation((query: string) => ({
  matches: mediaQueryMatches(query, 1280),
  media: query,
  onchange: null,
  addListener: vi.fn(),
  removeListener: vi.fn(),
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  dispatchEvent: vi.fn(),
}))

Object.defineProperty(globalThis, 'matchMedia', {
  writable: true,
  configurable: true,
  value: matchMediaMock,
})

Object.defineProperty(window, 'location', {
  value: {
    href: 'http://localhost:3000',
    origin: 'http://localhost:3000',
    pathname: '/',
    search: '',
    hash: '',
    reload: vi.fn(),
    assign: vi.fn(),
    replace: vi.fn(),
  },
  writable: true,
})

window.scrollTo = vi.fn()

global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}))

global.IntersectionObserver = class IntersectionObserver {
  observe = vi.fn()
  unobserve = vi.fn()
  disconnect = vi.fn()
  takeRecords = () => []
  constructor(
    _cb: IntersectionObserverCallback,
    _opts?: IntersectionObserverInit
  ) {}
}

const originalConsoleError = console.error
const originalConsoleWarn = console.warn

beforeEach(() => {
  console.error = (...args) => {
    if (
      typeof args[0] === 'string' &&
      args[0].includes('Warning: ReactDOM.render is no longer supported')
    ) {
      return
    }
    originalConsoleError.call(console, ...args)
  }

  console.warn = (...args) => {
    if (
      typeof args[0] === 'string' &&
      (args[0].includes('componentWillReceiveProps') ||
        args[0].includes('componentWillMount'))
    ) {
      return
    }
    originalConsoleWarn.call(console, ...args)
  }
})

afterEach(() => {
  console.error = originalConsoleError
  console.warn = originalConsoleWarn
})
