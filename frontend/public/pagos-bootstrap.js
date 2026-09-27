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

  var CHUNK_RELOAD_KEY = 'rapicredit_missing_chunk_reload_v1'
  // Una sola hard-reload automatica tras deploy; si falla de nuevo, UI de recuperacion.
  var MAX_CHUNK_RELOADS = 1

  function normalizeMsg(msg) {
    if (!msg || typeof msg !== 'string') return ''
    var lower = msg.toLowerCase()
    try {
      if (typeof lower.normalize === 'function') {
        lower = lower.normalize('NFD').replace(/[\u0300-\u036f]/g, '')
      }
    } catch (e) {
      /* ignore */
    }
    // Archivo ASCII: patrones con "?" no matchean "ó"; unificar basura de encoding.
    return lower.replace(/\?/g, '')
  }

  function reloadPage() {
    try {
      var n = Number(sessionStorage.getItem(CHUNK_RELOAD_KEY) || '0')
      if (n >= MAX_CHUNK_RELOADS) {
        originalError.call(
          console,
          '[bootstrap] Chunk ausente tras hard-reload. Mostrando recuperacion (Ctrl+Shift+R si persiste).'
        )
        showChunkRecoveryBanner()
        return
      }
      sessionStorage.setItem(CHUNK_RELOAD_KEY, String(n + 1))
    } catch (e) {
      /* sessionStorage bloqueado */
    }
    originalWarn.call(console, '[bootstrap] Modulo no encontrado (cache desactualizado). Hard-reload...')
    try {
      var u = new URL(window.location.href)
      u.searchParams.set('nocache', String(Date.now()))
      window.location.replace(u.pathname + u.search + u.hash)
    } catch (e2) {
      var base = window.location.href.split('?')[0].split('#')[0]
      window.location.replace(base + '?nocache=' + Date.now())
    }
  }

  /** Si quedara un SW/Workbox de un deploy antiguo, desregistrarlo sin romper la app. */
  function unregisterStaleServiceWorkers() {
    try {
      if (!('serviceWorker' in navigator)) return
      navigator.serviceWorker.getRegistrations().then(function (regs) {
        if (!regs || !regs.length) return
        originalWarn.call(
          console,
          '[bootstrap] Desregistrando ' + String(regs.length) + ' service worker(s) residual(es).'
        )
        for (var i = 0; i < regs.length; i++) {
          try {
            regs[i].unregister()
          } catch (e) {
            /* ignore */
          }
        }
      })
      if (window.caches && typeof window.caches.keys === 'function') {
        window.caches.keys().then(function (keys) {
          for (var j = 0; j < keys.length; j++) {
            try {
              window.caches.delete(keys[j])
            } catch (e2) {
              /* ignore */
            }
          }
        })
      }
    } catch (e) {
      /* ignore */
    }
  }
  unregisterStaleServiceWorkers()

  function showChunkRecoveryBanner() {
    if (document.getElementById('rapicredit-chunk-recovery-banner')) return
    var el = document.createElement('div')
    el.id = 'rapicredit-chunk-recovery-banner'
    el.setAttribute('role', 'alert')
    el.style.cssText =
      'position:fixed;inset:0;z-index:2147483000;display:flex;align-items:center;justify-content:center;padding:16px;background:rgba(15,23,42,.55);'
    el.innerHTML =
      '<div style="max-width:420px;background:#fffbeb;border:1px solid #fcd34d;border-radius:12px;padding:20px;font-family:system-ui,sans-serif;color:#78350f;box-shadow:0 20px 40px rgba(0,0,0,.2)">' +
      '<h2 style="margin:0 0 8px;font-size:18px">Actualizacion pendiente en el navegador</h2>' +
      '<p style="margin:0 0 16px;font-size:14px;line-height:1.45">Los botones pueden dejar de responder si quedo una version antigua de la app. Recargue sin cache.</p>' +
      '<div style="display:flex;gap:8px;flex-wrap:wrap">' +
      '<button type="button" id="rapicredit-chunk-reload-btn" style="padding:8px 14px;border:0;border-radius:8px;background:#b45309;color:#fff;font-weight:600;cursor:pointer">Recargar ahora</button>' +
      '</div></div>'
    document.body.appendChild(el)
    var btn = document.getElementById('rapicredit-chunk-reload-btn')
    if (btn) {
      btn.addEventListener('click', function () {
        try {
          sessionStorage.removeItem(CHUNK_RELOAD_KEY)
        } catch (e) {}
        var u = new URL(window.location.href)
        u.searchParams.set('nocache', String(Date.now()))
        window.location.replace(u.pathname + u.search + u.hash)
      })
    }
  }

  function isAssetChunkUrl(url) {
    if (!url || typeof url !== 'string') return false
    var u = url.toLowerCase()
    if ((u.indexOf('/assets/') !== -1 || u.indexOf('/pagos/assets/') !== -1) && /\.(js|mjs)(\?|#|$)/.test(u)) {
      return true
    }
    // Vite hashed chunk filename even without /assets/ in some reports.
    return /(?:^|\/)[a-z0-9_-]+-[a-z0-9_-]{6,}\.(js|mjs)(\?|#|$)/i.test(u)
  }

  function isStaleChunkExportMismatch(msg) {
    var m = normalizeMsg(msg)
    if (!m) return false
    return (
      m.indexOf("doesn't provide an export named") !== -1 ||
      m.indexOf('does not provide an export named') !== -1 ||
      m.indexOf('missing js chunk') !== -1
    )
  }

  function isDynamicChunkLoadFailure(msg, sourceUrl) {
    var m = normalizeMsg(msg)
    if (isStaleChunkExportMismatch(msg)) return true
    if (!m) {
      // Resource error events often have empty message; rely on failed module URL.
      return isAssetChunkUrl(sourceUrl)
    }
    var mimeHtml =
      (m.indexOf('text/html') !== -1 || m.indexOf('tipo mime') !== -1 || m.indexOf('mime no permitido') !== -1) &&
      (m.indexOf('modulo') !== -1 ||
        m.indexOf('module') !== -1 ||
        m.indexOf('.js') !== -1 ||
        isAssetChunkUrl(sourceUrl))
    return (
      m.indexOf('failed to fetch dynamically imported module') !== -1 ||
      m.indexOf('error loading dynamically imported module') !== -1 ||
      m.indexOf('failed to load module') !== -1 ||
      m.indexOf('ha fallado la carga del modulo') !== -1 ||
      m.indexOf('se bloqueo la carga de un modulo') !== -1 ||
      m.indexOf('failed to load module script') !== -1 ||
      m.indexOf('importing a module script failed') !== -1 ||
      m.indexOf('chunkloaderror') !== -1 ||
      m.indexOf('loading chunk') !== -1 ||
      mimeHtml ||
      (isAssetChunkUrl(sourceUrl) &&
        (m.indexOf('fetch') !== -1 ||
          m.indexOf('load') !== -1 ||
          m.indexOf('carga') !== -1 ||
          m.indexOf('mime') !== -1 ||
          m.indexOf('404') !== -1))
    )
  }

  function isStaleBuildReactInvariant(msg, sourceUrl) {
    var m = normalizeMsg(msg)
    if (!m) return false
    // En produccion, React minifica errores con codigos numericos.
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
      var target = event.target
      var errorMessage = event.message || ''
      var errorSource =
        (event.filename ||
          (target && (target.src || target.href)) ||
          '') ||
        ''
      if (isStaleBuildReactInvariant(errorMessage, errorSource)) {
        reloadPage()
        return
      }
      if (isStaleChunkExportMismatch(errorMessage)) {
        reloadPage()
        return
      }
      var isModuleScript =
        target && target.tagName === 'SCRIPT' && String(target.type || '').toLowerCase() === 'module'
      var isModulePreload =
        target &&
        target.tagName === 'LINK' &&
        String(target.rel || '').toLowerCase() === 'modulepreload'
      // Fallos de <script type=module> / modulepreload suelen llegar sin event.message.
      if (isModuleScript || isModulePreload) {
        var src = (target && (target.src || target.href)) || errorSource
        if (isAssetChunkUrl(src) || isDynamicChunkLoadFailure(errorMessage, src)) {
          reloadPage()
        }
        return
      }
      // Firefox puede reportar MIME text/html en consola sin target SCRIPT/LINK claro.
      if (
        isDynamicChunkLoadFailure(errorMessage, errorSource) &&
        isAssetChunkUrl(errorSource)
      ) {
        reloadPage()
      }
    },
    true
  )

  window.addEventListener(
    'unhandledrejection',
    function (event) {
      var r = event.reason
      var raw =
        (r && (typeof r.message === 'string' ? r.message : r.errMsg || r.msg || String(r))) || ''
      var msg = normalizeMsg(raw)
      var namedChunk =
        (msg.indexOf('comunicaciones-') !== -1 ||
          msg.indexOf('notificaciones-') !== -1 ||
          msg.indexOf('notificacionesrecibos') !== -1 ||
          msg.indexOf('editarrevisionmanual') !== -1 ||
          msg.indexOf('revisionmanual') !== -1 ||
          msg.indexOf('clientes-') !== -1 ||
          msg.indexOf('infopagos') !== -1 ||
          msg.indexOf('cobroshistorico') !== -1 ||
          msg.indexOf('pagosreportados') !== -1 ||
          msg.indexOf('index-') !== -1) &&
        msg.indexOf('.js') !== -1
      var mimeBlocked =
        (msg.indexOf('text/html') !== -1 || msg.indexOf('tipo mime') !== -1 || msg.indexOf('mime no permitido') !== -1) &&
        (msg.indexOf('modulo') !== -1 ||
          msg.indexOf('module') !== -1 ||
          msg.indexOf('/assets/') !== -1 ||
          msg.indexOf('/pagos/assets/') !== -1 ||
          msg.indexOf('.js') !== -1)
      var isChunk =
        isStaleChunkExportMismatch(raw) ||
        isDynamicChunkLoadFailure(raw, '') ||
        msg.indexOf('dynamically imported module') !== -1 ||
        (msg.indexOf('failed to fetch') !== -1 && msg.indexOf('module') !== -1) ||
        (msg.indexOf('error loading') !== -1 && msg.indexOf('module') !== -1) ||
        msg.indexOf('failed to load module') !== -1 ||
        msg.indexOf('se bloqueo la carga de un modulo') !== -1 ||
        msg.indexOf('importing a module script failed') !== -1 ||
        msg.indexOf('chunkloaderror') !== -1 ||
        (msg.indexOf('/assets/') !== -1 && msg.indexOf('.js') !== -1) ||
        (msg.indexOf('/pagos/assets/') !== -1 && msg.indexOf('.js') !== -1) ||
        mimeBlocked ||
        namedChunk
      if (isStaleBuildReactInvariant(raw, '')) {
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

  // Fallback anti-pantalla-infinita: hard-reload una vez; si ya se intento, UI de recuperacion.
  setTimeout(function () {
    var root = document.getElementById('root')
    if (!root) return

    var appReady = window.__RAPICREDIT_APP_READY__ === true || root.getAttribute('data-app-ready') === 'true'
    var loadingNode = root.querySelector('.app-loading-placeholder')
    if (appReady || !loadingNode) return

    originalError.call(
      console,
      '[bootstrap] Arranque excedio el tiempo esperado. Intentando hard-reload / fallback.'
    )

    try {
      var n = Number(sessionStorage.getItem(CHUNK_RELOAD_KEY) || '0')
      if (n < MAX_CHUNK_RELOADS) {
        reloadPage()
        return
      }
    } catch (e) {
      /* sessionStorage bloqueado: seguir a UI */
    }

    root.innerHTML =
      '<div class="app-boot-fallback" role="alert" aria-live="assertive">' +
      '<h2>No se pudo cargar el modulo</h2>' +
      '<p>La pagina tardo demasiado en iniciar. Suele ser cache desactualizado tras un deploy.</p>' +
      '<div class="app-boot-fallback-actions">' +
      '<button type="button" class="app-boot-fallback-primary" id="app-boot-retry">Reintentar</button>' +
      '<button type="button" class="app-boot-fallback-secondary" id="app-boot-reload">Recargar sin cache</button>' +
      '</div>' +
      '</div>'

    var retryBtn = document.getElementById('app-boot-retry')
    if (retryBtn) {
      retryBtn.addEventListener('click', function () {
        try {
          sessionStorage.removeItem(CHUNK_RELOAD_KEY)
        } catch (e2) {}
        reloadPage()
      })
    }

    var reloadBtn = document.getElementById('app-boot-reload')
    if (reloadBtn) {
      reloadBtn.addEventListener('click', function () {
        try {
          sessionStorage.removeItem(CHUNK_RELOAD_KEY)
        } catch (e3) {}
        var u = new URL(window.location.href)
        u.searchParams.set('nocache', String(Date.now()))
        window.location.replace(u.pathname + u.search + u.hash)
      })
    }
  }, 15000)
})()
