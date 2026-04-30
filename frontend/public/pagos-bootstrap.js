/**
 * Bootstrap temprano: suprime avisos ruidosos de CSS del navegador, recuperaci?n de chunks tras deploy,
 * y marca styles-loaded en #root. Archivo est?tico para permitir script-src estricto (sin inline).
 */
;(function () {
  'use strict'

  var originalWarn = console.warn
  var originalError = console.error
  var originalInfo = console.info

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
      'selector inv?lido',
      'regla ignorada',
      'propiedad desconocida',
      'declaraci?n rechazada',
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
      'error de an?lisis css',
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

  /** Axios en 502: el interceptor ya reintenta y la UI muestra toast; el objeto Error en consola duplica ruido. */
  function isGenericAxios502Message(args) {
    var msg = getMessage(args)
    if (!msg || typeof msg !== 'string') return false
    var m = msg.toLowerCase()
    if (m.indexOf('502') === -1) return false
    if (m.indexOf('request failed with status code 502') !== -1) return true
    if (m.indexOf('status code 502') !== -1 && m.indexOf('axios') !== -1) return true
    return false
  }

  /** No silenciar logs marcados del producto (env, proxy, api). */
  function isReservedInfoPrefix(msg) {
    if (!msg || typeof msg !== 'string') return false
    var t = msg.trim()
    return /^\[(env|proxy|apiclient|bootstrap|api)\]/i.test(t)
  }

  console.info = function () {
    var msg = getMessage(arguments)
    if (isReservedInfoPrefix(msg)) {
      return originalInfo.apply(console, arguments)
    }
    if (shouldSuppress(msg)) return
    originalInfo.apply(console, arguments)
  }

  console.warn = function () {
    if (shouldSuppress(getMessage(arguments))) return
    originalWarn.apply(console, arguments)
  }
  console.error = function () {
    var msg = getMessage(arguments)
    if (shouldSuppress(msg)) return
    if (isGenericAxios502Message(arguments)) {
      originalWarn.call(
        console,
        '[api] 502 Bad Gateway: suele ser proxy o API en Render arrancando; la app reintenta y puede mostrar un aviso. Revise API_BASE_URL/BACKEND_URL en el servicio Node si persiste.'
      )
      return
    }
    originalError.apply(console, arguments)
  }

  var reloadAttempted = false
  function reloadPage() {
    if (reloadAttempted) return
    reloadAttempted = true
    originalWarn.call(console, 'M?dulo no encontrado (cache desactualizado). Recargando...')
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
      (m.indexOf('m?dulo') !== -1 ||
        m.indexOf('modulo') !== -1 ||
        m.indexOf('module') !== -1 ||
        m.indexOf('.js') !== -1 ||
        isAssetChunkUrl(sourceUrl))
    return (
      m.indexOf('failed to fetch dynamically imported module') !== -1 ||
      m.indexOf('error loading dynamically imported module') !== -1 ||
      m.indexOf('failed to load module') !== -1 ||
      m.indexOf('ha fallado la carga del m?dulo') !== -1 ||
      m.indexOf('se bloque? la carga de un m?dulo') !== -1 ||
      m.indexOf('failed to load module script') !== -1 ||
      mimeHtml ||
      (isAssetChunkUrl(sourceUrl) &&
        (m.indexOf('fetch') !== -1 || m.indexOf('load') !== -1 || m.indexOf('carga') !== -1 || m.indexOf('mime') !== -1))
    )
  }

  function isStaleBuildReactInvariant(msg, sourceUrl) {
    if (!msg || typeof msg !== 'string') return false
    var m = msg.toLowerCase()
    // En producci?n, React minifica errores con c?digos num?ricos.
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
      '[bootstrap] Detectada API cross-origin (pagos-f2qf) desde rapicredit. Recargando para recuperar configuraci?n same-origin.'
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
        (msg.indexOf('m?dulo') !== -1 ||
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
        msg.indexOf('se bloque? la carga de un m?dulo') !== -1 ||
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
  // mostramos UI de recuperaci?n en vez de dejar "Cargando..." permanente.
  setTimeout(function () {
    var root = document.getElementById('root')
    if (!root) return

    var appReady = window.__RAPICREDIT_APP_READY__ === true || root.getAttribute('data-app-ready') === 'true'
    var loadingNode = root.querySelector('.app-loading-placeholder')
    if (appReady || !loadingNode) return

    originalError.call(
      console,
      '[bootstrap] Arranque excedi? el tiempo esperado. Mostrando fallback de recuperaci?n.'
    )

    root.innerHTML =
      '<div class="app-boot-fallback" role="alert" aria-live="assertive">' +
      '<h2>No se pudo cargar el m?dulo</h2>' +
      '<p>La p?gina tard? demasiado en iniciar. Puede ser cach? desactualizado o conexi?n inestable.</p>' +
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
