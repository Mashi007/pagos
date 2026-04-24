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
    // Firefox a veces concatena mensaje + " index-XXXX.css:linea:col" en un solo string.
    if (/reglas?\s+ignoradas/i.test(message) && /mal\s+selector|bad\s+selector|malformed\s+selector/i.test(message)) {
      return true
    }
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
      'moz-column-gap',
      'column-gap',
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

  function isAssetChunkUrl(url) {
    if (!url || typeof url !== 'string') return false
    var u = url.toLowerCase()
    return (u.indexOf('/assets/') !== -1 || u.indexOf('/pagos/assets/') !== -1) && u.indexOf('.js') !== -1
  }

  function isDynamicChunkLoadFailure(msg, sourceUrl) {
    if (!msg || typeof msg !== 'string') return false
    var m = msg.toLowerCase()
    var mimeHtml =
      (m.indexOf('text/html') !== -1 || m.indexOf('tipo mime') !== -1 || m.indexOf('mime no permitido') !== -1) &&
      (m.indexOf('módulo') !== -1 ||
        m.indexOf('modulo') !== -1 ||
        m.indexOf('module') !== -1 ||
        m.indexOf('.js') !== -1 ||
        isAssetChunkUrl(sourceUrl))
    return (
      m.indexOf('failed to fetch dynamically imported module') !== -1 ||
      m.indexOf('error loading dynamically imported module') !== -1 ||
      m.indexOf('failed to load module') !== -1 ||
      m.indexOf('ha fallado la carga del módulo') !== -1 ||
      m.indexOf('se bloqueó la carga de un módulo') !== -1 ||
      m.indexOf('failed to load module script') !== -1 ||
      mimeHtml ||
      (isAssetChunkUrl(sourceUrl) &&
        (m.indexOf('fetch') !== -1 || m.indexOf('load') !== -1 || m.indexOf('carga') !== -1 || m.indexOf('mime') !== -1))
    )
  }

  function isStaleBuildReactInvariant(msg, sourceUrl) {
    if (!msg || typeof msg !== 'string') return false
    var m = msg.toLowerCase()
    // En producción, React minifica errores con códigos numéricos.
    // Cuando hay mezcla de bundles viejos/nuevos tras deploy, puede dispararse al bootstrap.
    var isKnownInvariant =
      m.indexOf('minified react error #306') !== -1 ||
      m.indexOf('invariant=306') !== -1
    if (!isKnownInvariant) return false
    return (
      isAssetChunkUrl(sourceUrl) ||
      m.indexOf('/assets/') !== -1 ||
      m.indexOf('/pagos/assets/') !== -1
    )
  }

  function isRapiCreditHost() {
    var h = (window.location && window.location.hostname) || ''
    return h === 'rapicredit.onrender.com'
  }

  function isCrossApiFallbackUrl(rawUrl) {
    if (!rawUrl || typeof rawUrl !== 'string') return false
    return rawUrl.toLowerCase().indexOf('https://pagos-f2qf.onrender.com/') === 0
  }

  function maybeRecoverCrossOriginApi(targetUrl) {
    if (!isRapiCreditHost()) return
    if (!isCrossApiFallbackUrl(targetUrl)) return
    originalWarn.call(
      console,
      '[bootstrap] Detectada API cross-origin (pagos-f2qf) desde rapicredit. Recargando para recuperar configuración same-origin.'
    )
    reloadPage()
  }

  ;(function patchFetchForCrossOriginRecovery() {
    if (typeof window.fetch !== 'function') return
    var originalFetch = window.fetch.bind(window)
    window.fetch = function (input, init) {
      var url = ''
      if (typeof input === 'string') {
        url = input
      } else if (input && typeof input.url === 'string') {
        url = input.url
      }
      maybeRecoverCrossOriginApi(url)
      return originalFetch(input, init)
    }
  })()

  ;(function patchXhrForCrossOriginRecovery() {
    if (!window.XMLHttpRequest || !window.XMLHttpRequest.prototype) return
    var xhrProto = window.XMLHttpRequest.prototype
    var originalOpen = xhrProto.open
    xhrProto.open = function (method, url) {
      if (typeof url === 'string') {
        maybeRecoverCrossOriginApi(url)
      }
      return originalOpen.apply(this, arguments)
    }
  })()

  window.addEventListener(
    'error',
    function (event) {
      var errorMessage = event.message || ''
      var errorSource = (event.filename || (event.target && event.target.src) || '') || ''
      if (isStaleBuildReactInvariant(errorMessage, errorSource)) {
        reloadPage()
        return
      }
      if (event.target && event.target.tagName === 'SCRIPT' && event.target.type === 'module') {
        if (isDynamicChunkLoadFailure(errorMessage, errorSource)) {
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
          msg.indexOf('clientes-') !== -1 ||
          msg.indexOf('infopagos') !== -1 ||
          msg.indexOf('cobroshistorico') !== -1 ||
          msg.indexOf('pagosreportados') !== -1) &&
        msg.indexOf('.js') !== -1
      var mimeBlocked =
        (msg.indexOf('text/html') !== -1 || msg.indexOf('tipo mime') !== -1 || msg.indexOf('mime no permitido') !== -1) &&
        (msg.indexOf('módulo') !== -1 ||
          msg.indexOf('modulo') !== -1 ||
          msg.indexOf('module') !== -1 ||
          msg.indexOf('/assets/') !== -1 ||
          msg.indexOf('/pagos/assets/') !== -1 ||
          msg.indexOf('.js') !== -1)
      var isChunk =
        msg.indexOf('dynamically imported module') !== -1 ||
        (msg.indexOf('failed to fetch') !== -1 && msg.indexOf('module') !== -1) ||
        (msg.indexOf('error loading') !== -1 && msg.indexOf('module') !== -1) ||
        msg.indexOf('failed to load module') !== -1 ||
        msg.indexOf('se bloqueó la carga de un módulo') !== -1 ||
        (msg.indexOf('/assets/') !== -1 && msg.indexOf('.js') !== -1) ||
        (msg.indexOf('/pagos/assets/') !== -1 && msg.indexOf('.js') !== -1) ||
        mimeBlocked ||
        namedChunk
      if (isStaleBuildReactInvariant(msg, '')) {
        event.preventDefault()
        event.stopPropagation()
        reloadPage()
        return
      }
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

  // Fallback anti-pantalla-infinita: si el shell sigue igual tras el timeout,
  // mostramos UI de recuperación en vez de dejar "Cargando..." permanente.
  setTimeout(function () {
    var root = document.getElementById('root')
    if (!root) return

    var appReady = window.__RAPICREDIT_APP_READY__ === true || root.getAttribute('data-app-ready') === 'true'
    var loadingNode = root.querySelector('.app-loading-placeholder')
    if (appReady || !loadingNode) return

    originalError.call(
      console,
      '[bootstrap] Arranque excedió el tiempo esperado. Mostrando fallback de recuperación.'
    )

    root.innerHTML =
      '<div class="app-boot-fallback" role="alert" aria-live="assertive">' +
      '<h2>No se pudo cargar el módulo</h2>' +
      '<p>La página tardó demasiado en iniciar. Puede ser caché desactualizado o conexión inestable.</p>' +
      '<div class="app-boot-fallback-actions">' +
      '<button type="button" class="app-boot-fallback-primary" id="app-boot-retry">Reintentar</button>' +
      '<button type="button" class="app-boot-fallback-secondary" id="app-boot-reload">Recargar</button>' +
      '</div>' +
      '</div>'

    var retryBtn = document.getElementById('app-boot-retry')
    if (retryBtn) {
      retryBtn.addEventListener('click', function () {
        reloadPage()
      })
    }

    var reloadBtn = document.getElementById('app-boot-reload')
    if (reloadBtn) {
      reloadBtn.addEventListener('click', function () {
        window.location.reload()
      })
    }
  }, 15000)
})()
