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
    (msg.includes('text/html') && msg.includes('module'))
  )
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
