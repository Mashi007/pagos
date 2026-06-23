import { Component, type ErrorInfo, type ReactNode } from 'react'

import { RouteChunkError } from './RouteChunkError'

type Props = {
  children: ReactNode
}

type State = {
  error: Error | null
}

function isChunkLoadError(err: Error | null): boolean {
  const msg = (err?.message || '').toLowerCase()
  return (
    msg.includes('dynamically imported module') ||
    msg.includes('failed to fetch dynamically imported module') ||
    msg.includes('error loading dynamically imported module') ||
    msg.includes('failed to load module') ||
    msg.includes('missing js chunk') ||
    msg.includes('mime no permitido') ||
    msg.includes('tipo mime') ||
    (msg.includes('text/html') && msg.includes('module'))
  )
}

const CHUNK_RELOAD_KEY = 'rapicredit_missing_chunk_reload_v1'
const CHUNK_RELOAD_MAX = 5

export function tryAutoReloadForChunkError(): boolean {
  try {
    const n = Number(sessionStorage.getItem(CHUNK_RELOAD_KEY) || '0')
    if (n >= CHUNK_RELOAD_MAX) return false
    sessionStorage.setItem(CHUNK_RELOAD_KEY, String(n + 1))
    const u = new URL(window.location.href)
    u.searchParams.set('nocache', String(Date.now()))
    window.location.replace(`${u.pathname}${u.search}${u.hash}`)
    return true
  } catch {
    return false
  }
}

export class RouteErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    if (isChunkLoadError(error)) {
      console.warn(
        '[route] Chunk load error:',
        error.message,
        info.componentStack
      )
      if (tryAutoReloadForChunkError()) return
      return
    }
    console.error('[route] Render error:', error, info.componentStack)
  }

  private reset = () => {
    this.setState({ error: null })
  }

  render() {
    const { error } = this.state
    if (error) {
      return <RouteChunkError error={error} reset={this.reset} />
    }
    return this.props.children
  }
}
