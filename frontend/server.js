import express from 'express';
import path from 'path';
import { fileURLToPath } from 'url';
import { existsSync, readdirSync, readFileSync } from 'fs';
import { createProxyMiddleware } from 'http-proxy-middleware';
import compression from 'compression';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();

// Health al inicio (antes de CSP, compresion y proxy): Render debe obtener 200 rapido; si /health queda
// despues de middlewares pesados o el dashboard sigue usando GET / (302), el deploy hace timeout.
function sendHealthJson(res) {
  res.status(200).json({
    status: 'healthy',
    service: 'rapicredit-frontend',
    version: '1.0.1',
  });
}
app.get('/health', (_req, res) => sendHealthJson(res));
app.head('/health', (_req, res) => res.status(200).end());
app.get('/healthz', (_req, res) => sendHealthJson(res));
app.head('/healthz', (_req, res) => res.status(200).end());

function collectBootAssetsFromIndex(indexHtml) {
  const assets = new Set();
  if (!indexHtml || typeof indexHtml !== 'string') return [];
  const regex = /(?:src|href)=["']([^"']+)["']/g;
  let match;
  while ((match = regex.exec(indexHtml)) !== null) {
    const candidate = (match[1] || '').trim();
    if (
      candidate.startsWith('/pagos/assets/') ||
      candidate.startsWith('/pagos/pagos-bootstrap.js') ||
      candidate.startsWith('/pagos/pagos-critical.css')
    ) {
      assets.add(candidate);
    }
  }
  return Array.from(assets);
}

/**
 * URL base del backend para el proxy Express (/api/* -> backend).
 * En Render, si no hay ninguna variable de entorno, Node caía en localhost:8000 (no existe en el dyno)
 * y el navegador veía fallos de red en cobros/infopagos.
 */
function normalizeBackendBase(raw) {
  const t = (raw || '').trim();
  if (!t) return '';
  let u = t.replace(/\/$/, '');
  if (!/^https?:\/\//i.test(u)) {
    u = `https://${u.replace(/^\/+/, '')}`;
  }
  try {
    const parsed = new URL(u);
    if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') return '';
    return u.replace(/\/$/, '');
  } catch {
    return '';
  }
}

/** Valor por defecto si falta API en Render (sobrescribible con RENDER_API_FALLBACK_URL). */
const RENDER_KNOWN_FALLBACK_DEFAULT = 'https://pagos-f2qf.onrender.com';

function resolveApiProxyTarget() {
  const candidates = [
    process.env.API_BASE_URL,
    process.env.BACKEND_URL,
    process.env.VITE_API_BASE_URL,
    process.env.VITE_API_URL,
  ];
  for (const raw of candidates) {
    const n = normalizeBackendBase(raw);
    if (n) return { url: n, source: 'env' };
  }
  const onRender =
    process.env.RENDER === 'true' ||
    Boolean((process.env.RENDER_SERVICE_ID || '').trim());
  if (onRender && process.env.DISABLE_RENDER_KNOWN_API_FALLBACK !== '1') {
    const fallbackRaw =
      (process.env.RENDER_API_FALLBACK_URL || '').trim() ||
      RENDER_KNOWN_FALLBACK_DEFAULT;
    const fallback = normalizeBackendBase(fallbackRaw);
    const fb = fallback || normalizeBackendBase(RENDER_KNOWN_FALLBACK_DEFAULT);
    console.warn(
      `[proxy] Render sin API_BASE_URL/BACKEND_URL; usando respaldo ${fb}. ` +
        'Opcional: RENDER_API_FALLBACK_URL, o API_BASE_URL. Desactive con DISABLE_RENDER_KNOWN_API_FALLBACK=1.'
    );
    return { url: fb, source: 'render-fallback' };
  }
  const local = normalizeBackendBase('http://localhost:8000');
  return { url: local || 'http://localhost:8000', source: 'localhost' };
}

const _resolvedApi = resolveApiProxyTarget();
const API_URL = _resolvedApi.url;

/**
 * Starlette/FastAPI suelen enviar Location absoluta al dominio público del API.
 * El cliente llamó a https://rapicredit.../api/...; si recibe 307 hacia pagos-f2qf...,
 * el fetch sigue a otro origen y puede fallar (CORS, POST+redirect). Forzamos ruta relativa /api/...
 */
function locationHeaderSameOriginForProxy(locationHeader, apiBaseUrl) {
  if (!locationHeader || typeof locationHeader !== 'string') return locationHeader;
  const raw = locationHeader.trim();
  if (!raw) return locationHeader;
  try {
    const base = new URL(apiBaseUrl.endsWith('/') ? apiBaseUrl.slice(0, -1) : apiBaseUrl);
    const loc = new URL(raw, base);
    if (loc.origin !== base.origin) return locationHeader;
    return `${loc.pathname}${loc.search}${loc.hash}`;
  } catch {
    return locationHeader;
  }
}

/** Orígenes extra para connect-src (p. ej. API absoluta en VITE_API_URL). */
function connectSrcExtraOrigins(apiUrl) {
  const out = new Set();
  const raw = (apiUrl || '').trim();
  if (!raw) return out;
  try {
    const parsed = new URL(raw);
    if (parsed.protocol === 'http:' || parsed.protocol === 'https:') {
      out.add(parsed.origin);
    }
  } catch {
    /* ignorar URL inválida */
  }
  return out;
}

function buildContentSecurityPolicy(apiUrl) {
  const connectBits = ["'self'", ...connectSrcExtraOrigins(apiUrl)];
  return [
    "default-src 'self'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
    "object-src 'none'",
    "script-src 'self'",
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data: https: blob:",
    "font-src 'self' data:",
    `connect-src ${connectBits.join(' ')}`,
    "frame-src 'self' blob: data:",
    "worker-src 'self' blob:",
  ].join('; ');
}

// Log de la URL configurada para debug
console.log(`🔍 API_URL (proxy): ${API_URL} [${_resolvedApi.source}]`);
console.log(`🔍 API_BASE_URL (runtime): ${process.env.API_BASE_URL || 'NO SET'}`);
console.log(`🔍 BACKEND_URL (runtime): ${process.env.BACKEND_URL || 'NO SET'}`);
console.log(`🔍 VITE_API_BASE_URL (build-time): ${process.env.VITE_API_BASE_URL || 'NO SET'}`);
console.log(`🔍 VITE_API_URL (build-time): ${process.env.VITE_API_URL || 'NO SET'}`);

// ============================================
// SECURITY HEADERS - OWASP Best Practices
// ============================================
app.disable('x-powered-by');

// Middleware para security headers
app.use((req, res, next) => {
  // Prevenir MIME sniffing
  res.setHeader('X-Content-Type-Options', 'nosniff');

  // Prevenir clickjacking
  res.setHeader('X-Frame-Options', 'DENY');

  // XSS Protection
  res.setHeader('X-XSS-Protection', '1; mode=block');

  // HSTS - Solo en producción
  if (process.env.NODE_ENV === 'production') {
    res.setHeader('Strict-Transport-Security', 'max-age=31536000; includeSubDomains');
  }

  // Content Security Policy (única fuente; sin meta CSP en index.html)
  res.setHeader('Content-Security-Policy', buildContentSecurityPolicy(API_URL));

  // Referrer Policy
  res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');

  // Permissions Policy
  res.setHeader('Permissions-Policy', 'geolocation=(), microphone=(), camera=()');

  next();
});

// ============================================
// COMPRESSION MIDDLEWARE - Gzip para reducir tamaño de respuestas
// ============================================
// Comprimir todas las respuestas (texto, JSON, HTML, CSS, JS)
// Esto reduce ~70% del tamaño de las respuestas, mejorando significativamente el rendimiento
app.use(compression({
  filter: (req, res) => {
    // Comprimir todo excepto si el cliente no lo soporta o ya está comprimido
    if (req.headers['x-no-compression']) {
      return false;
    }
    // Usar el filtro por defecto de compression
    return compression.filter(req, res);
  },
  level: 6, // Nivel de compresión balanceado (1-9, 6 es un buen balance)
  threshold: 1024, // Solo comprimir respuestas mayores a 1KB
}));

// ============================================
// LOGGING MIDDLEWARE - Para debug de peticiones
// ============================================
// Reducir logging en producción para mejorar rendimiento
// En Render, PORT siempre está configurado, así que si PORT existe y NODE_ENV no es 'development', es producción
const isDevelopment = process.env.NODE_ENV === 'development';
const isProduction = process.env.NODE_ENV === 'production' ||
                     (process.env.PORT && process.env.NODE_ENV !== 'development');

// Log de diagnóstico solo al inicio
if (!isDevelopment) {
  console.log(`🔇 Logging reducido en producción (NODE_ENV=${process.env.NODE_ENV || 'undefined'}, PORT=${process.env.PORT || 'undefined'})`);
  console.log(`✅ Compresión gzip activada (threshold: 1KB, level: 6)`);
}

app.use((req, res, next) => {
  // Solo loggear en desarrollo - en producción no loggear nada para mejorar rendimiento
  if (isDevelopment && req.path.startsWith('/api')) {
    console.log(`📥 [${req.method}] Petición API recibida: ${req.path}`);
  }
  // En producción, no loggear nada aquí para reducir overhead
  next();
});

// Si algo pide /pagos/api/... (base path + API), redirigir a /api/... (el proxy solo escucha en /api).
app.all(/^\/pagos\/api(\/.*)?$/i, (req, res) => {
  const target = req.originalUrl.replace(/^\/pagos\/api/i, '/api') || '/api';
  res.redirect(307, target);
});

// Enlaces o marcadores que duplican el base path (/pagos/pagos/...) rompen express.static
// (busca dist/pagos/...). Colapsar a una sola /pagos/... antes de estáticos y SPA.
app.all(/^\/pagos\/pagos(\/|$|\?)/i, (req, res) => {
  const raw = req.originalUrl || req.url || '/';
  const qs = raw.includes('?') ? `?${raw.split('?').slice(1).join('?')}` : '';
  let pathOnly = raw.split('?')[0] || '/';
  while (pathOnly.startsWith('/pagos/pagos')) {
    pathOnly = `/pagos${pathOnly.slice('/pagos/pagos'.length)}`;
  }
  res.redirect(307, pathOnly + qs);
});

// ============================================
// PROXY /api -> Backend (Render o local)
// ============================================
// IMPORTANTE: Proxy debe ir ANTES de servir archivos estáticos
// Usar app.use('/api', ...) para que Express maneje el routing
// Esto asegura que SOLO rutas /api pasen por el proxy
// Incluye localhost:8000 para pruebas locales del build con backend local
if (API_URL) {
  console.log(`➡️  Proxy de /api hacia: ${API_URL}`);
  const proxyMiddleware = createProxyMiddleware({
    target: API_URL,
    changeOrigin: true,
    xfwd: true,
    logLevel: isDevelopment ? 'info' : 'warn', // Reducir verbosidad en producción
    // CRÍTICO: No seguir redirects (302). Si el backend devuelve 302 (ej. OAuth callback),
    // el navegador debe recibir el 302 y hacer el redirect para que la URL cambie.
    // followRedirects: true haría que el proxy siguiera el redirect y devolviera 200 + HTML,
    // dejando la URL del navegador en /api/.../callback y la SPA en blanco.
    followRedirects: false,
    // IMPORTANTE: Cuando usamos app.use('/api', ...), Express elimina el /api del req.path
    // Ejemplo: /api/v1/clientes -> req.path = /v1/clientes
    // Necesitamos reconstruirlo: /v1/clientes -> /api/v1/clientes
    pathRewrite: (path, req) => {
      // El path que llega ya NO tiene /api (Express lo eliminó cuando usamos app.use('/api', ...))
      // Ejemplo: /api/v1/modelos-vehiculos -> path recibido = /v1/modelos-vehiculos
      // Necesitamos agregar /api de vuelta: /v1/modelos-vehiculos -> /api/v1/modelos-vehiculos
      // EXCEPCIÓN: /health, /health/db y /health/gemini están en la raíz del backend (no bajo /api/v1)
      if (path === '/health' || path === '/health/db' || path === '/v1/health/gemini') {
        return path === '/v1/health/gemini' ? '/health/gemini' : path;
      }
      const rewritten = `/api${path}`;
      // Solo loggear en desarrollo
      if (isDevelopment) {
        console.log(`🔄 Path rewrite: "${path}" -> "${rewritten}"`);
      }
      return rewritten;
    },
    // No cambiar el protocolo
    secure: true,
    onError: (err, req, res) => {
      console.error(`❌ Error en proxy para ${req.method} ${req.originalUrl || req.url}:`, err.message);
      if (!res.headersSent) {
        res.status(502).json({
          error: 'Proxy error',
          message: err.message,
          target: API_URL,
          path: req.path,
          originalUrl: req.originalUrl,
          method: req.method
        });
      }
    },
    onProxyReq: (proxyReq, req, res) => {
      // Este callback se ejecuta DESPUÉS del pathRewrite
      // El proxyReq ya tiene el path reescrito y el query string se preserva automáticamente
      // IMPORTANTE: NO debemos modificar el query string manualmente - http-proxy-middleware lo maneja

      // Solo loggear detalles en desarrollo
      if (isDevelopment) {
        const queryString = proxyReq.path.includes('?') ? proxyReq.path.split('?')[1] : '';
        console.log(`➡️  [${req.method}] Proxying: ${req.path}`);
        console.log(`   Target: ${API_URL}${proxyReq.path}`);
      }

      // Asegurar que los headers se copien correctamente
      const authHeader = req.headers.authorization || req.headers.Authorization;
      if (authHeader) {
        proxyReq.setHeader('Authorization', authHeader);
      }

      // Copiar otros headers importantes
      if (req.headers.cookie) {
        proxyReq.setHeader('Cookie', req.headers.cookie);
      }

      // Timeout saliente hacia el backend: envíos masivos de notificaciones y exportaciones pueden superar 1–3 min.
      // Debe alinearse con TIMEOUT_MS_ENVIO_NOTIFICACIONES_MANUAL (15 min) en notificacionService.ts.
      const p = proxyReq.path || '';
      const isExportReport = p.includes('/exportar/');
      const isNotificacionesLote =
        p.includes('/notificaciones/enviar-caso-manual') ||
        p.includes('/notificaciones/enviar-todas');
      let proxyTimeoutMs = 60000;
      if (isExportReport) {
        proxyTimeoutMs = 180000;
      } else if (isNotificacionesLote) {
        proxyTimeoutMs = 900000;
      }
      proxyReq.setTimeout(proxyTimeoutMs);
    },
    onProxyRes: (proxyRes, req, res) => {
      const status = proxyRes.statusCode;

      const locHdr = proxyRes.headers['location'];
      if (locHdr) {
        const locStr = Array.isArray(locHdr) ? locHdr[0] : locHdr;
        const fixed = locationHeaderSameOriginForProxy(locStr, API_URL);
        if (fixed !== locStr) {
          proxyRes.headers['location'] = fixed;
          if (isDevelopment) {
            console.log(`🔄 Location (proxy): "${locStr}" -> "${fixed}"`);
          }
        }
      }

      // ✅ OPTIMIZACIÓN: Agregar cache headers para respuestas exitosas de GET
      // Esto reduce la carga en el backend para datos que no cambian frecuentemente
      if (status >= 200 && status < 300 && req.method === 'GET') {
        // Identificar endpoints que pueden ser cacheados (req.originalUrl = ruta completa)
        const fullPath = req.originalUrl?.split('?')[0] || req.path || '';
        const cacheableEndpoints = [
          '/api/v1/modelos-vehiculos',
          '/api/v1/concesionarios',
          '/api/v1/analistas',
          '/api/v1/configuracion'
        ];

        const isCacheable = cacheableEndpoints.some(endpoint => fullPath.includes(endpoint));

        if (isCacheable) {
          // Cache por 5 minutos para datos que cambian poco
          res.setHeader('Cache-Control', 'private, max-age=300, stale-while-revalidate=60');
        } else if (fullPath.includes('/api/v1/dashboard') || fullPath.includes('/api/v1/kpis')) {
          // Cache corto (30 segundos) para datos del dashboard que cambian más frecuentemente
          res.setHeader('Cache-Control', 'private, max-age=30, stale-while-revalidate=10');
        } else {
          // No cachear por defecto para otros endpoints (datos dinámicos)
          res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
        }
      }

      // Solo loggear errores en producción, todo en desarrollo
      if (!isDevelopment && status >= 400) {
        const emoji = status >= 400 ? '❌' : '⚠️';
        console.log(`${emoji} [${req.method}] ${status} ${req.path}`);
        if (status === 404) {
          console.error(`   ❌ ERROR 404 - El backend no encontró la ruta: ${API_URL}${proxyRes.req?.path || req.path}`);
        }
      } else if (isDevelopment) {
        const emoji = status >= 200 && status < 300 ? '✅' : status >= 400 ? '❌' : '⚠️';
        console.log(`${emoji} [${req.method}] Proxy response: ${status} para ${req.originalUrl || req.url}`);
      }
    },
    onProxyError: (err, req, res) => {
      console.error(`❌ ERROR en proxy durante la petición: ${err.message}`);
      console.error(`   URL: ${req.originalUrl || req.url}`);
      console.error(`   Target: ${API_URL}`);
      console.error(`   Stack: ${err.stack}`);
      if (!res.headersSent) {
        res.status(502).json({
          error: 'Proxy error',
          message: err.message,
          target: API_URL,
          path: req.path
        });
      }
    }
  });

  // IMPORTANTE: Usar app.use('/api', ...) para que Express maneje el routing
  // Esto asegura que SOLO rutas que empiecen con /api pasen por el proxy
  // Las rutas como /clientes, /assets/*.js, etc. NO pasarán por aquí
  app.use('/api', proxyMiddleware);

  // También registrar explícitamente para debug
  console.log('✅ Proxy middleware registrado para rutas /api/*');
} else {
  console.warn('⚠️  API_URL no configurado. Proxy deshabilitado.');
}

// ============================================
// VALIDACIONES PREVIAS
// ============================================
// Validar que el directorio dist existe antes de configurar el servidor
const distPath = path.join(__dirname, 'dist');
const indexPath = path.join(distPath, 'index.html');

if (!existsSync(distPath)) {
  console.error(`❌ ERROR CRÍTICO: Directorio dist no encontrado en: ${distPath}`);
  console.error('   Asegúrate de que el build se completó correctamente.');
  process.exit(1);
}

if (!existsSync(indexPath)) {
  console.error(`❌ ERROR CRÍTICO: index.html no encontrado en: ${indexPath}`);
  console.error('   Asegúrate de que el build se completó correctamente.');
  process.exit(1);
}

app.get('/health/escaner', (_req, res) => {
  const checks = [];
  const escanerRoute = '/pagos/escaner';
  try {
    const indexHtml = readFileSync(indexPath, 'utf8');
    const assetRefs = collectBootAssetsFromIndex(indexHtml);
    const missingAssets = [];
    for (const ref of assetRefs) {
      const rel = ref.startsWith('/pagos/') ? ref.slice('/pagos/'.length) : ref;
      const localPath = path.join(distPath, rel);
      if (!existsSync(localPath)) {
        missingAssets.push(ref);
      }
    }

    checks.push({
      name: 'spa_index_readable',
      ok: true,
      details: 'index.html cargado correctamente',
    });
    checks.push({
      name: 'escaner_route_configured',
      ok: true,
      details: escanerRoute,
    });
    checks.push({
      name: 'bootstrap_assets_present',
      ok: missingAssets.length === 0,
      details:
        missingAssets.length === 0
          ? `assets verificados: ${assetRefs.length}`
          : `faltantes: ${missingAssets.join(', ')}`,
    });

    const healthy = checks.every((c) => c.ok);
    const body = {
      status: healthy ? 'healthy' : 'degraded',
      service: 'rapicredit-frontend',
      check: 'escaner',
      route: escanerRoute,
      checked_at: new Date().toISOString(),
      checks,
    };
    res.status(healthy ? 200 : 503).json(body);
  } catch (err) {
    res.status(503).json({
      status: 'down',
      service: 'rapicredit-frontend',
      check: 'escaner',
      route: escanerRoute,
      checked_at: new Date().toISOString(),
      checks: [
        {
          name: 'spa_index_readable',
          ok: false,
          details: err?.message || 'error leyendo index.html',
        },
      ],
    });
  }
});
app.head('/health/escaner', (_req, res) => res.status(200).end());

console.log(`📁 Directorio de archivos estáticos: ${distPath}`);
console.log(`✅ Validaciones previas completadas`);

// ============================================
// SERVIR ARCHIVOS ESTÁTICOS
// ============================================
// Servir archivos estáticos con cache headers (DESPUÉS del proxy)
// IMPORTANTE: Esto debe servir archivos .js, .css, .html, etc. con los MIME types correctos
// Estos archivos son PARTE DE LA SPA (React), NO del backend

const staticOptions = {
  maxAge: '1d',
  etag: true,
  lastModified: true,
  setHeaders: (res, filePath) => {
    // CRÍTICO: No cachear index.html para evitar 404 en chunks tras un nuevo deploy.
    if (filePath.endsWith('index.html') || path.basename(filePath) === 'index.html') {
      res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
      res.setHeader('Pragma', 'no-cache');
      res.setHeader('Expires', '0');
      return;
    }
    // No cachear el entry JS/CSS (index-*.js, index-*.css) para que tras un deploy se cargue el bundle nuevo
    const basename = path.basename(filePath);
    if (basename.startsWith('index-') && (filePath.endsWith('.js') || filePath.endsWith('.css'))) {
      res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
      res.setHeader('Pragma', 'no-cache');
      res.setHeader('Expires', '0');
      return;
    }
    // No cachear chunks de exportación (exceljs, jspdf) - evita 404 tras deploy cuando el hash cambia
    if (basename.includes('exceljs') || basename.includes('jspdf') || basename.includes('pdf-export')) {
      res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
      res.setHeader('Pragma', 'no-cache');
      res.setHeader('Expires', '0');
      return;
    }
    // Asegurar MIME types correctos para archivos JavaScript
    if (filePath.endsWith('.js')) {
      res.setHeader('Content-Type', 'application/javascript; charset=utf-8');
    }
    // Log cuando se sirve un archivo estático (solo en desarrollo)
    if (isDevelopment && filePath.includes('/assets/')) {
      console.log(`📦 Sirviendo archivo estático: ${filePath}`);
    }
  },
  // Callback cuando no se encuentra el archivo
  fallthrough: true // Continuar al siguiente middleware si el archivo no existe
};

// ✅ Verificar que los archivos de assets existen antes de servir
const assetsPath = path.join(distPath, 'assets');
if (existsSync(assetsPath)) {
  const assetFiles = readdirSync(assetsPath);
  console.log(`✅ Directorio assets encontrado: ${assetsPath}`);
  console.log(`📦 Total de archivos en assets: ${assetFiles.length}`);
  // Log los primeros 10 archivos para debugging
  if (assetFiles.length > 0) {
    console.log(`📦 Primeros archivos: ${assetFiles.slice(0, 10).join(', ')}`);
  }
} else {
  console.error(`❌ Directorio assets NO encontrado: ${assetsPath}`);
  console.error(`❌ Esto causará que los módulos JavaScript no se carguen correctamente`);
}

// Base path para frontend: https://rapicredit.onrender.com/pagos
const FRONTEND_BASE = '/pagos';

// Middleware para loggear peticiones de archivos estáticos
app.use((req, res, next) => {
  // Solo loggear en desarrollo - en producción estos logs son ruido
  if (isDevelopment && (req.path.startsWith(FRONTEND_BASE + '/assets/') || req.path.endsWith('.js') || req.path.endsWith('.css') || req.path.endsWith('.svg'))) {
    console.log(`📦 Frontend: Petición de archivo estático recibida: ${req.method} ${req.path}`);
  }
  next();
});

// Servir estáticos bajo /pagos (index.html, /pagos/assets/*, etc.)
app.use(FRONTEND_BASE, express.static(distPath, staticOptions));

// Redirigir raíz a /pagos (frontend en https://rapicredit.onrender.com/pagos)
// Si el health check del panel sigue en "/" (por defecto), devolver 200 para no bloquear deploy (302 no cuenta como sano).
app.get('/', (req, res) => {
  const ua = (req.headers['user-agent'] || '').toLowerCase();
  if (ua.includes('render') || ua.includes('healthcheck') || ua.includes('kube-probe')) {
    return sendHealthJson(res);
  }
  res.redirect(302, FRONTEND_BASE + (req.url !== '/' ? req.url : ''));
});

// Si el navegador pide /assets/* (sin /pagos), redirigir a /pagos/assets/* para evitar MIME type error
// (p. ej. caché con index.html antiguo que usaba base '/' o script con src="/assets/...")
app.get('/assets/*', (req, res) => {
  const subpath = req.path.slice('/assets'.length) || '/';
  res.redirect(302, FRONTEND_BASE + '/assets' + subpath + (req.originalUrl?.includes('?') ? '?' + req.originalUrl.split('?')[1] : ''));
});

// Favicon: redirigir favicon.svg (antiguo) a logos/rAPI.png para no 404 ni servir archivo viejo
app.get('/favicon.svg', (req, res) => res.redirect(302, FRONTEND_BASE + '/logos/rAPI.png'));
app.get(FRONTEND_BASE + '/favicon.svg', (req, res) => res.redirect(302, FRONTEND_BASE + '/logos/rAPI.png'));

// /logos/* sin base: redirigir a /pagos/logos/* (evita 404 cuando BASE_URL no se aplica)
app.get(/^\/logos\//, (req, res) => {
  const subpath = req.path.slice(6); // '/logos'.length
  res.redirect(302, FRONTEND_BASE + '/logos' + subpath + (req.originalUrl?.includes('?') ? '?' + req.originalUrl.split('?')[1] : ''));
});

// Activar frontend en https://rapicredit.onrender.com/reportes -> redirigir a /pagos/reportes
const qs = (req) => (req.originalUrl && req.originalUrl.includes('?') ? req.originalUrl.slice(req.originalUrl.indexOf('?')) : '');
app.get('/reportes', (req, res) => {
  res.redirect(302, FRONTEND_BASE + '/reportes' + qs(req));
});
app.get('/reportes/*', (req, res) => {
  const subpath = req.path.slice('/reportes'.length);
  res.redirect(302, FRONTEND_BASE + '/reportes' + subpath + qs(req));
});

// Ruta pública: estado de cuenta sin base -> redirigir a /pagos/rapicredit-estadocuenta
app.get('/rapicredit-estadocuenta', (req, res) => {
  res.redirect(302, FRONTEND_BASE + '/rapicredit-estadocuenta' + qs(req));
});
app.get('/rapicredit-estadocuenta/*', (req, res) => {
  const subpath = req.path.slice('/rapicredit-estadocuenta'.length);
  res.redirect(302, FRONTEND_BASE + '/rapicredit-estadocuenta' + subpath + qs(req));
});

// Ruta pública: reporte de pagos sin base -> redirigir a /pagos/rapicredit-reporte-pagos
app.get('/rapicredit-reporte-pagos', (req, res) => {
  res.redirect(302, FRONTEND_BASE + '/rapicredit-reporte-pagos' + qs(req));
});
app.get('/rapicredit-reporte-pagos/*', (req, res) => {
  const subpath = req.path.slice('/rapicredit-reporte-pagos'.length);
  res.redirect(302, FRONTEND_BASE + '/rapicredit-reporte-pagos' + subpath + qs(req));
});

// /prestamos sin base -> redirigir a /pagos/prestamos (evita 404 al abrir o compartir /prestamos)
app.get('/prestamos', (req, res) => {
  res.redirect(302, FRONTEND_BASE + '/prestamos' + qs(req));
});
app.get('/prestamos/*', (req, res) => {
  const subpath = req.path.slice('/prestamos'.length);
  res.redirect(302, FRONTEND_BASE + '/prestamos' + subpath + qs(req));
});

// Rutas SPA sin base: redirigir a /pagos/... para que Render sirva correctamente (ej. /chat-ai -> /pagos/chat-ai)
app.get('/chat-ai', (req, res) => {
  res.redirect(302, FRONTEND_BASE + '/chat-ai' + qs(req));
});


// SPA fallback solo para /pagos y /pagos/* (el proxy ya atendió /api/*)
// Incluye /pagos/chat-ai, /pagos/dashboard, etc.: cualquier ruta que no sea archivo estático recibe index.html
// Sirve index.html reescribiendo /assets/ -> /pagos/assets/ para evitar 302 cuando el build no aplica base
function sendSpaIndex(req, res) {
  res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
  res.setHeader('Pragma', 'no-cache');
  res.setHeader('Expires', '0');
  if (isDevelopment) {
    console.log(`📄 Frontend (SPA): Sirviendo index.html para ruta: ${req.method} ${req.path}`);
  }
  try {
    let html = readFileSync(indexPath, 'utf8');
    // <base href="/pagos/"> para que rutas relativas (ej. assets/xxx.js) se resuelvan bien en /pagos/chat-ai
    const baseTag = `<base href="${FRONTEND_BASE}/">`;
    if (!html.includes('<base ')) {
      html = html.replace(/<head[^>]*>/, (m) => m + baseTag);
    }
    // Si el HTML sigue con script de dev (/src/main.tsx), sustituir por el entry real para que cargue la app
    if (html.includes('/src/main.tsx') || html.includes('/src/main.jsx')) {
      const entryJs = (existsSync(assetsPath) && readdirSync(assetsPath).find((f) => f.startsWith('index-') && f.endsWith('.js'))) || null;
      if (entryJs) {
        html = html
          .replace(/src="[^"]*\/src\/main\.(tsx|jsx)"/, `src="${FRONTEND_BASE}/assets/${entryJs}"`)
          .replace(/src='[^']*\/src\/main\.(tsx|jsx)'/, `src='${FRONTEND_BASE}/assets/${entryJs}'`);
      }
    }
    // Siempre corregir rutas sin base: "/assets/ -> /pagos/assets/ para evitar 302 (build puede no aplicar base)
    // Incluir comillas simples por si el build emite src='/assets/...'
    html = html
      .replace(/src="\/assets\//g, `src="${FRONTEND_BASE}/assets/`)
      .replace(/href="\/assets\//g, `href="${FRONTEND_BASE}/assets/`)
      .replace(/src='\/assets\//g, `src='${FRONTEND_BASE}/assets/`)
      .replace(/href='\/assets\//g, `href='${FRONTEND_BASE}/assets/`);
    res.type('html').send(html);
  } catch (err) {
    console.error(`❌ Error sirviendo index.html para ${req.method} ${req.path}:`, err);
    if (!res.headersSent) {
      res.status(404).send('Página no encontrada');
    }
  }
}
app.get(FRONTEND_BASE, sendSpaIndex);
app.get(FRONTEND_BASE + '/*', (req, res, next) => {
  // No servir index.html para rutas que parecen archivos estáticos (assets)
  const subPath = req.path.slice(FRONTEND_BASE.length) || '/';
  if (subPath.startsWith('/assets/')) {
    const filePath = path.join(distPath, subPath);
    if (existsSync(filePath)) {
      if (subPath.endsWith('.js')) res.setHeader('Content-Type', 'application/javascript; charset=utf-8');
      else if (subPath.endsWith('.css')) res.setHeader('Content-Type', 'text/css');
      return res.sendFile(filePath);
    }
  }
  const staticFileExtensions = ['.js', '.css', '.svg', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.woff', '.woff2', '.ttf', '.eot'];
  if (staticFileExtensions.some(ext => req.path.endsWith(ext))) {
    return res.status(404).send('Not Found');
  }
  // Cualquier otra ruta bajo /pagos (ej. /pagos/dashboard, /pagos/configuracion) recibe index.html para SPA
  res.status(200);
  sendSpaIndex(req, res);
});

// ============================================
// INICIALIZACIÓN DEL SERVIDOR
// ============================================
const PORT = process.env.PORT || 3000;

// Validar que PORT está configurado
if (!process.env.PORT) {
  console.warn(`⚠️  PORT no configurado, usando puerto por defecto: ${PORT}`);
} else {
  console.log(`✅ PORT configurado: ${PORT}`);
}

// Iniciar servidor con manejo de errores
let server;

try {
  // Validar que el directorio dist existe antes de iniciar
  if (!existsSync(distPath)) {
    console.error(`❌ ERROR CRÍTICO: Directorio dist no encontrado: ${distPath}`);
    console.error('   El build debe completarse antes de iniciar el servidor.');
    process.exit(1);
  }

  if (!existsSync(indexPath)) {
    console.error(`❌ ERROR CRÍTICO: index.html no encontrado: ${indexPath}`);
    console.error('   El build debe completarse antes de iniciar el servidor.');
    process.exit(1);
  }

  server = app.listen(PORT, '0.0.0.0', () => {
    // Logs de inicio consolidados (sin duplicación)
    const startTime = new Date().toISOString();
    console.log('🚀 ==========================================');
    console.log('🚀 Servidor SPA rapicredit-frontend iniciado');
    console.log('🚀 ==========================================');
    console.log(`📡 Puerto: ${PORT}`);
    console.log(`📁 Directorio: ${distPath}`);
    console.log(`🌍 Entorno: ${process.env.NODE_ENV || 'development'}`);
    console.log(`🔗 API URL: ${API_URL || 'No configurado'}`);
    console.log(`✅ Health check disponible en: http://0.0.0.0:${PORT}/health`);
    console.log(`⏰ Hora de inicio: ${startTime}`);
    console.log('✅ Servidor listo para recibir requests');
    
    // Guardar tiempo de inicio para diagnóstico
    process.env.SERVER_START_TIME = startTime;
  });

  // Manejar errores del servidor
  server.on('error', (err) => {
    console.error('❌ ERROR al iniciar servidor:', err);
    console.error(`   Código: ${err.code}`);
    console.error(`   Mensaje: ${err.message}`);
    if (err.code === 'EADDRINUSE') {
      console.error(`   Puerto ${PORT} ya está en uso`);
    }
    process.exit(1);
  });

  // Health check para Render - solo loguear si hay problema
  server.on('listening', () => {
    const address = server.address();
    if (!address) {
      console.warn('⚠️  No se pudo obtener la dirección del servidor');
    }
    // No duplicar logs de inicio - ya se loguearon en el callback de listen()
  });

  // Manejar cierre graceful del servidor
  // OPTIMIZADO: Timeout para evitar que el servidor se cuelgue esperando conexiones
  const gracefulShutdown = (signal) => {
    const shutdownTime = new Date().toISOString();
    const startTime = process.env.SERVER_START_TIME || 'desconocido';
    const uptime = process.uptime();
    
    console.log(`📴 ${signal} recibido, cerrando servidor gracefully...`);
    console.log(`⏰ Hora de cierre: ${shutdownTime}`);
    console.log(`⏱️  Tiempo de ejecución: ${Math.round(uptime)} segundos (${Math.round(uptime / 60)} minutos)`);
    console.log(`📅 Inicio del servidor: ${startTime}`);
    
    if (server) {
      // Cerrar el servidor con timeout de 10 segundos
      server.close(() => {
        console.log('✅ Servidor cerrado correctamente');
        process.exit(0);
      });

      // Forzar cierre después de 10 segundos si aún hay conexiones activas
      setTimeout(() => {
        console.warn('⚠️  Timeout alcanzado, forzando cierre del servidor...');
        process.exit(1);
      }, 10000);
    } else {
      process.exit(0);
    }
  };

  process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
  process.on('SIGINT', () => gracefulShutdown('SIGINT'));
} catch (error) {
  console.error('❌ ERROR CRÍTICO al crear servidor:', error);
  console.error('   Tipo:', error.constructor.name);
  console.error('   Mensaje:', error.message);
  console.error('   Stack:', error.stack);
  process.exit(1);
}

// Manejar errores no capturados
process.on('uncaughtException', (err) => {
  console.error('❌ ERROR no capturado:', err);
  console.error('Stack trace:', err.stack);
  process.exit(1);
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('❌ PROMESA RECHAZADA NO MANEJADA:', reason);
  if (reason instanceof Error) {
    console.error('Stack trace:', reason.stack);
  }
  process.exit(1);
});
