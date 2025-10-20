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

// Declaraciones JSX para resolver errores de tipos
declare global {
  namespace JSX {
    interface IntrinsicElements {
      [elemName: string]: any
    }
  }
}
