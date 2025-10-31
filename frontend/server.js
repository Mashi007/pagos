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
// Capturar TODAS las peticiones a /api (GET, POST, PUT, DELETE, etc.)
if (API_URL) {
  console.log(`➡️  Proxy de /api hacia: ${API_URL}`);
  const proxyMiddleware = createProxyMiddleware({
    target: API_URL,
    changeOrigin: true,
    xfwd: true,
    logLevel: 'debug',
    // NO necesitamos filtro: app.use('/api', ...) ya garantiza que solo rutas /api/* lleguen aquí
    // Express elimina el prefijo /api antes de pasar al middleware, así que pathname será /v1/auth/login
    // IMPORTANTE: Cuando usas app.use('/api', ...), Express elimina /api del path
    // Necesitamos agregarlo de vuelta para que el backend reciba /api/v1/auth/login completo
    // Cuando el proxy recibe /v1/auth/login, lo reescribimos a /api/v1/auth/login
    pathRewrite: (path, req) => {
      // PROBLEMA DETECTADO: path viene con query string incluido en algunos casos
      // Necesitamos extraer solo el path sin query string
      const pathOnly = path.split('?')[0]; // Remover query string si está presente
      
      // Express eliminó /api del path, así que pathOnly es "/v1/clientes"
      // Necesitamos agregar /api de vuelta
      const rewritten = `/api${pathOnly}`;
      
      // Log detallado para debug
      console.log(`🔄 Path rewrite:`);
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
  
  // Wrapper para capturar errores silenciosos
  app.use('/api', (req, res, next) => {
    console.log(`🔄 Proxy middleware ejecutándose para: ${req.method} ${req.path}`);
    try {
      proxyMiddleware(req, res, next);
    } catch (error) {
      console.error(`❌ Error al ejecutar proxy middleware:`, error);
      if (!res.headersSent) {
        res.status(500).json({ error: 'Internal proxy error', message: error.message });
      }
    }
  });
  
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
app.get('*', (req, res) => {
  // Ignorar rutas de API (deberían ser capturadas por el proxy)
  if (req.path.startsWith('/api')) {
    console.warn(`⚠️  Ruta /api no capturada por proxy: ${req.path}`);
    return res.status(404).json({ error: 'API endpoint not found' });
  }
  // El proxy de /api maneja las APIs; aquí solo servimos la SPA
  console.log(`📄 Sirviendo index.html para ruta: ${req.path}`);
  res.sendFile(path.join(__dirname, 'dist', 'index.html'));
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
