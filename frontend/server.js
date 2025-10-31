import express from 'express';
import path from 'path';
import { fileURLToPath } from 'url';
import { createProxyMiddleware } from 'http-proxy-middleware';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
// URL del backend - Prioridad: VITE_API_BASE_URL > VITE_API_URL > localhost
const API_URL = process.env.VITE_API_BASE_URL || process.env.VITE_API_URL || 'http://localhost:8000';

// Log de la URL configurada para debug
console.log(`🔍 API_URL configurado: ${API_URL || 'NO CONFIGURADO'}`);
console.log(`🔍 VITE_API_BASE_URL: ${process.env.VITE_API_BASE_URL || 'NO SET'}`);
console.log(`🔍 VITE_API_URL: ${process.env.VITE_API_URL || 'NO SET'}`);

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
  
  // Content Security Policy
  res.setHeader(
    'Content-Security-Policy',
    "default-src 'self'; " +
    "script-src 'self' 'unsafe-inline' 'unsafe-eval'; " +
    "style-src 'self' 'unsafe-inline'; " +
    "img-src 'self' data: https:; " +
    "font-src 'self' data:; " +
    "connect-src 'self' " + API_URL
  );
  
  // Referrer Policy
  res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
  
  // Permissions Policy
  res.setHeader('Permissions-Policy', 'geolocation=(), microphone=(), camera=()');
  
  next();
});

// ============================================
// LOGGING MIDDLEWARE - Para debug de peticiones
// ============================================
app.use((req, res, next) => {
  // Loggear todas las peticiones a /api (POST, GET, etc.)
  if (req.path.startsWith('/api')) {
    console.log(`📥 [${req.method}] Petición API recibida: ${req.path}`);
    console.log(`   originalUrl: ${req.originalUrl || req.url}`);
    console.log(`   headers.host: ${req.headers.host}`);
  }
  next();
});

// ============================================
// PROXY /api -> Backend (Render)
// ============================================
// IMPORTANTE: Proxy debe ir ANTES de servir archivos estáticos
// Capturar SOLO las peticiones a /api (GET, POST, PUT, DELETE, etc.)
if (API_URL) {
  console.log(`➡️  Proxy de /api hacia: ${API_URL}`);
  const proxyMiddleware = createProxyMiddleware({
    target: API_URL,
    changeOrigin: true,
    xfwd: true,
    logLevel: 'debug',
    // Filtrar SOLO rutas que empiecen con /api
    // Las rutas de la SPA (como /clientes) NO deben pasar por aquí
    filter: (pathname, req) => {
      const matches = pathname.startsWith('/api');
      if (matches) {
        console.log(`🔍 Filter: "${pathname}" -> MATCH (proxying)`);
      } else {
        // Log solo para rutas problemáticas (no deberían aparecer muchos)
        if (pathname !== '/favicon.ico' && !pathname.startsWith('/_') && pathname !== '/') {
          console.log(`🔍 Filter: "${pathname}" -> NO MATCH (es ruta de SPA, NO proxying)`);
        }
      }
      return matches;
    },
    // IMPORTANTE: pathRewrite solo se ejecuta si filter devuelve true
    // El path que llega es "/api/v1/clientes", lo mantenemos tal cual
    pathRewrite: (path, req) => {
      // Solo ejecutar si es ruta de API
      if (!path.startsWith('/api')) {
        console.warn(`⚠️  pathRewrite ejecutado para ruta no-API: "${path}"`);
        return path;
      }
      
      // Extraer solo el path sin query string
      const pathOnly = path.split('?')[0];
      
      // Con filter, el path ya incluye /api, así que pathOnly es "/api/v1/clientes"
      // Lo mantenemos tal cual
      const rewritten = pathOnly;
      
      // Log detallado para debug (solo para rutas /api)
      console.log(`🔄 Path rewrite (API):`);
      console.log(`   Path recibido (con query?): "${path}"`);
      console.log(`   Path sin query: "${pathOnly}"`);
      console.log(`   req.url completo: "${req.url}"`);
      console.log(`   req.originalUrl: "${req.originalUrl || req.url}"`);
      console.log(`   Path reescrito: "${rewritten}"`);
      
      return rewritten;
    },
    // Seguir redirects del backend (3xx)
    followRedirects: true,
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
      // El proxyReq ya tiene el path reescrito
      const targetUrl = `${API_URL}${proxyReq.path}`;
      
      console.log(`➡️  [${req.method}] Proxying hacia backend`);
      console.log(`   Request original: ${req.originalUrl || req.url}`);
      console.log(`   req.path: ${req.path}`);
      console.log(`   proxyReq.path (reescrito): ${proxyReq.path}`);
      console.log(`   Target URL completa: ${targetUrl}`);
      
      // Log detallado de headers
      const authHeader = req.headers.authorization || req.headers.Authorization;
      console.log(`   Authorization header: ${authHeader ? 'PRESENTE (' + authHeader.substring(0, 20) + '...)' : 'AUSENTE'}`);
      console.log(`   Todos los headers de auth:`, {
        'authorization': req.headers.authorization,
        'Authorization': req.headers.Authorization,
        'cookie': req.headers.cookie ? 'PRESENTE' : 'AUSENTE'
      });
      
      // Asegurar que los headers se copien correctamente
      if (authHeader) {
        proxyReq.setHeader('Authorization', authHeader);
        console.log(`   ✅ Header Authorization copiado al proxy`);
      } else {
        console.warn(`   ⚠️  NO hay header Authorization - el backend devolverá 401/404`);
      }
      
      // Copiar otros headers importantes
      if (req.headers.cookie) {
        proxyReq.setHeader('Cookie', req.headers.cookie);
      }
    },
    onProxyRes: (proxyRes, req, res) => {
      const status = proxyRes.statusCode;
      const emoji = status >= 200 && status < 300 ? '✅' : status >= 400 ? '❌' : '⚠️';
      console.log(`${emoji} [${req.method}] Proxy response: ${status} para ${req.originalUrl || req.url}`);
    }
  });
  
  // Aplicar a todas las rutas que empiecen con /api
  // IMPORTANTE: Debe ser ANTES de express.static y otros middlewares
  // http-proxy-middleware devuelve un middleware que se puede usar directamente
  
  // IMPORTANTE: Usar el proxy directamente sin prefijo, usando filter para capturar /api/*
  // Esto asegura que los callbacks (onProxyReq, onProxyRes) se ejecuten correctamente
  app.use(proxyMiddleware);
  
  // También registrar explícitamente para debug
  console.log('✅ Proxy middleware registrado para rutas /api/*');
} else {
  console.warn('⚠️  API_URL no configurado. Proxy deshabilitado.');
}

// Servir archivos estáticos con cache headers (DESPUÉS del proxy)
app.use(express.static(path.join(__dirname, 'dist'), {
  maxAge: '1d',
  etag: true,
  lastModified: true
}));

// Health check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({
    status: 'healthy',
    timestamp: new Date().toISOString(),
    service: 'rapicredit-frontend',
    version: '1.0.1'
  });
});

// Manejar SPA routing - todas las rutas sirven index.html (el proxy ya atendió /api/*)
// IMPORTANTE: Esto debe ir DESPUÉS del proxy y express.static
// Solo maneja rutas que NO son archivos estáticos ni APIs
// Usar app.use para capturar TODOS los métodos HTTP, no solo GET
app.use((req, res, next) => {
  // Solo procesar si NO es una ruta de API
  // Las rutas de API ya fueron manejadas por el proxy
  if (req.path.startsWith('/api')) {
    // Esto no debería pasar si el proxy está funcionando correctamente
    console.warn(`⚠️  Ruta /api no capturada por proxy: ${req.method} ${req.path}`);
    return res.status(404).json({ error: 'API endpoint not found' });
  }
  
  // Ignorar archivos estáticos (favicon, assets, etc.) - ya fueron servidos por express.static
  // Si express.static no encontró el archivo, llegamos aquí
  // Esto significa que es una ruta de la SPA (como /clientes, /dashboard, etc.)
  // React Router se encargará de manejar la ruta en el cliente
  console.log(`📄 Sirviendo index.html para ruta de SPA: ${req.method} ${req.path}`);
  res.sendFile(path.join(__dirname, 'dist', 'index.html'), (err) => {
    if (err) {
      console.error(`❌ Error sirviendo index.html para ${req.method} ${req.path}:`, err);
      if (!res.headersSent) {
        res.status(404).send('Página no encontrada');
      }
    }
  });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, '0.0.0.0', () => {
  console.log('🚀 ==========================================');
  console.log('🚀 Servidor SPA rapicredit-frontend iniciado');
  console.log('🚀 ==========================================');
  console.log(`📡 Puerto: ${PORT}`);
  console.log(`📁 Directorio: ${path.join(__dirname, 'dist')}`);
  console.log(`🌍 Entorno: ${process.env.NODE_ENV || 'development'}`);
  console.log(`🔗 API URL: ${API_URL || 'No configurado'}`);
  console.log('✅ Servidor listo para recibir requests');
});
