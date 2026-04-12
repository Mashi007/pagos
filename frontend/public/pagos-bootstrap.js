/**
 * Bootstrap temprano: suprime avisos ruidosos de CSS del navegador, recuperación de chunks tras deploy,
 * y marca styles-loaded en #root. Archivo estático para permitir script-src estricto (sin inline).
 */
;(function () {
  'use strict'

  var originalWarn = console.warn
  var originalError = console.error

  function getMessage(args) {
    var arr = Array.prototype.slice.call(args)
    return arr
      .map(function (arg) {
        if (arg != null && typeof arg === 'object' && typeof arg.message === 'string') {
          return arg.message
        }
        if (arg != null && typeof arg === 'object' && typeof arg.defaultMessage === 'string') {
          return arg.defaultMessage
        }
        return typeof arg === 'string'
          ? arg
          : arg && typeof arg.toString === 'function'
            ? arg.toString()
            : String(arg)
      })
      .join(' ')
  }

  function shouldSuppress(message) {
    if (!message || typeof message !== 'string') return false
    var lowerMessage = message.toLowerCase()
    if (lowerMessage.indexOf('reglas ignoradas') !== -1 && lowerMessage.indexOf('selector') !== -1) {
      return true
    }

    var patterns = [
      'juego de reglas ignoradas',
      'reglas ignoradas',
      'debido a un mal selector',
      'mal selector',
      'selector inválido',
      'regla ignorada',
      'propiedad desconocida',
      'declaración rechazada',
      'ignored due to bad selector',
      'ignored debido a un mal selector',
      'ignored due to malformed selector',
      'bad selector',
      'malformed selector',
      'ruleset ignored',
      'invalid selector',
      'unknown property',
      'declaration dropped',
      '.css:',
      'index-',
      'webkit-text-size-adjust',
      'moz-text-size-adjust',
      'text-size-adjust',
      '-moz-osx-font-smoothing',
      'css parsing error',
      'error de análisis css',
      'after\\:left-\\[',
      'after\\:top-\\[',
      'placeholder\\:text-',
      'menu:',
      'ignoradas debido',
      'juego de reglas ignoradas debido a un mal selector',
    ]

    for (var i = 0; i < patterns.length; i++) {
      if (lowerMessage.includes(patterns[i])) return true
    }

    var cssFilePattern = /(index-[a-z0-9]+\.css|menu|\.css):\d+:\d+/i
    if (
      cssFilePattern.test(message) &&
      (lowerMessage.includes('ignored') ||
        lowerMessage.includes('ignoradas') ||
        lowerMessage.includes('bad selector') ||
        lowerMessage.includes('mal selector') ||
        lowerMessage.includes('malformed') ||
        lowerMessage.includes('debido') ||
        lowerMessage.includes('juego de reglas'))
    ) {
      return true
    }

    if (
      (lowerMessage.includes('.css:') ||
        lowerMessage.includes('index-') ||
        lowerMessage.includes('menu:')) &&
      (lowerMessage.includes('ignored') ||
        lowerMessage.includes('ignoradas') ||
        lowerMessage.includes('bad selector') ||
        lowerMessage.includes('mal selector') ||
        lowerMessage.includes('malformed') ||
        lowerMessage.includes('debido'))
    ) {
      return true
    }

    if (
      lowerMessage.includes('juego de reglas') &&
      lowerMessage.includes('ignoradas') &&
      (lowerMessage.includes('debido') || lowerMessage.includes('mal selector'))
    ) {
      return true
    }

    if (
      (lowerMessage.includes('ignoradas') || lowerMessage.includes('ignored')) &&
      (lowerMessage.includes('selector') ||
        lowerMessage.includes('mal selector') ||
        lowerMessage.includes('bad selector')) &&
      (lowerMessage.includes('.css') || lowerMessage.includes('index-') || cssFilePattern.test(message))
    ) {
      return true
    }

    return false
  }

  console.warn = function () {
    if (shouldSuppress(getMessage(arguments))) return
    originalWarn.apply(console, arguments)
  }
  console.error = function () {
    if (shouldSuppress(getMessage(arguments))) return
    originalError.apply(console, arguments)
  }

  var reloadAttempted = false
  function reloadPage() {
    if (reloadAttempted) return
    reloadAttempted = true
    originalWarn.call(console, 'Módulo no encontrado (cache desactualizado). Recargando...')
    var base = window.location.href.split('?')[0].split('#')[0]
    window.location.replace(base + '?nocache=' + Date.now())
  }

  window.addEventListener(
    'error',
    function (event) {
      if (event.target && event.target.tagName === 'SCRIPT' && event.target.type === 'module') {
        var errorMessage = (event.message || '').toLowerCase()
        var errorSource = (event.filename || event.target.src || '').toLowerCase()
        if (
          errorMessage.includes('failed to fetch dynamically imported module') ||
          errorMessage.includes('error loading dynamically imported module') ||
          errorMessage.includes('failed to load module') ||
          errorMessage.includes('ha fallado la carga del módulo') ||
          errorMessage.includes('failed to load module script') ||
          (errorSource.includes('/assets/') && errorSource.includes('.js'))
        ) {
          reloadPage()
        }
      }
    },
    true
  )

  window.addEventListener(
    'unhandledrejection',
    function (event) {
      var r = event.reason
      var msg =
        (r && (typeof r.message === 'string' ? r.message : r.errMsg || r.msg || String(r))) || ''
      msg = msg.toLowerCase()
      var namedChunk =
        (msg.indexOf('comunicaciones-') !== -1 ||
          msg.indexOf('notificaciones-') !== -1 ||
          msg.indexOf('clientes-') !== -1) &&
        msg.indexOf('.js') !== -1
      var isChunk =
        msg.indexOf('dynamically imported module') !== -1 ||
        (msg.indexOf('failed to fetch') !== -1 && msg.indexOf('module') !== -1) ||
        (msg.indexOf('error loading') !== -1 && msg.indexOf('module') !== -1) ||
        msg.indexOf('failed to load module') !== -1 ||
        (msg.indexOf('/assets/') !== -1 && msg.indexOf('.js') !== -1) ||
        namedChunk
      if (isChunk) {
        event.preventDefault()
        event.stopPropagation()
        reloadPage()
      }
    },
    true
  )

  function checkStylesLoaded() {
    var root = document.getElementById('root')
    if (!root) return
    requestAnimationFrame(function () {
      requestAnimationFrame(function () {
        var computedStyle = window.getComputedStyle(root)
        if (computedStyle && computedStyle.fontFamily) {
          root.classList.add('styles-loaded')
        } else {
          setTimeout(checkStylesLoaded, 50)
        }
      })
    })
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', checkStylesLoaded)
  } else {
    checkStylesLoaded()
  }

  setTimeout(function () {
    var root = document.getElementById('root')
    if (root) root.classList.add('styles-loaded')
  }, 2000)
})()
