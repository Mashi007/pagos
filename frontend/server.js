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
// Usar app.use('/api', ...) para que Express maneje el routing
// Esto asegura que SOLO rutas /api pasen por el proxy
if (API_URL) {
  console.log(`➡️  Proxy de /api hacia: ${API_URL}`);
  const proxyMiddleware = createProxyMiddleware({
    target: API_URL,
    changeOrigin: true,
    xfwd: true,
    logLevel: 'info', // Reducir verbosidad
    // IMPORTANTE: Cuando usamos app.use('/api', ...), Express elimina el /api del req.path
    // Ejemplo: /api/v1/clientes -> req.path = /v1/clientes
    // Necesitamos reconstruirlo: /v1/clientes -> /api/v1/clientes
    pathRewrite: (path, req) => {
      // Extraer solo el path sin query string (el path puede venir con ?query)
      const pathOnly = path.split('?')[0];
      // El path que llega ya NO tiene /api (Express lo eliminó)
      // Lo agregamos de vuelta para que el backend reciba /api/v1/...
      const rewritten = `/api${pathOnly}`;
      console.log(`🔄 Path rewrite: "${path}" -> "${rewritten}"`);
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
      // IMPORTANTE: El query string se preserva automáticamente por http-proxy-middleware
      const queryString = req.url.split('?')[1] || '';
      const targetUrl = `${API_URL}${proxyReq.path}${queryString ? '?' + queryString : ''}`;
      
      console.log(`➡️  [${req.method}] Proxying hacia backend`);
      console.log(`   Request original: ${req.originalUrl || req.url}`);
      console.log(`   req.path: ${req.path}`);
      console.log(`   proxyReq.path (reescrito): ${proxyReq.path}`);
      console.log(`   Query string: ${queryString || '(vacío)'}`);
      console.log(`   Target URL completa: ${targetUrl}`);
      
      // Log detallado de headers
      const authHeader = req.headers.authorization || req.headers.Authorization;
      console.log(`   Authorization header: ${authHeader ? 'PRESENTE (' + authHeader.substring(0, 20) + '...)' : 'AUSENTE'}`);
      
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
  
  // IMPORTANTE: Usar app.use('/api', ...) para que Express maneje el routing
  // Esto asegura que SOLO rutas que empiecen con /api pasen por el proxy
  // Las rutas como /clientes, /assets/*.js, etc. NO pasarán por aquí
  app.use('/api', proxyMiddleware);
  
  // También registrar explícitamente para debug
  console.log('✅ Proxy middleware registrado para rutas /api/*');
} else {
  console.warn('⚠️  API_URL no configurado. Proxy deshabilitado.');
}

// Servir archivos estáticos con cache headers (DESPUÉS del proxy)
// IMPORTANTE: Esto debe servir archivos .js, .css, .html, etc. con los MIME types correctos
// Estos archivos son PARTE DE LA SPA (React), NO del backend
const distPath = path.join(__dirname, 'dist');
console.log(`📁 Directorio de archivos estáticos: ${distPath}`);

const staticOptions = {
  maxAge: '1d',
  etag: true,
  lastModified: true,
  setHeaders: (res, filePath) => {
    // Asegurar MIME types correctos para archivos JavaScript
    if (filePath.endsWith('.js')) {
      res.setHeader('Content-Type', 'application/javascript; charset=utf-8');
    }
    // Log cuando se sirve un archivo estático (solo para debugging)
    if (filePath.includes('/assets/')) {
      console.log(`📦 Sirviendo archivo estático: ${filePath}`);
    }
  },
  // Callback cuando no se encuentra el archivo
  fallthrough: true // Continuar al siguiente middleware si el archivo no existe
};

// Middleware para loggear peticiones de archivos estáticos
app.use((req, res, next) => {
  // Solo loggear archivos estáticos (assets, favicon, etc.)
  if (req.path.startsWith('/assets/') || req.path.endsWith('.js') || req.path.endsWith('.css') || req.path.endsWith('.svg')) {
    console.log(`📦 Frontend: Petición de archivo estático recibida: ${req.method} ${req.path}`);
  }
  next();
});

app.use(express.static(distPath, staticOptions));

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
// IMPORTANTE: NO es una página estática - es una SPA que hace peticiones dinámicas al backend
app.get('*', (req, res) => {
  // Solo procesar si NO es una ruta de API
  // Las rutas de API ya fueron manejadas por el proxy
  if (req.path.startsWith('/api')) {
    // Esto no debería pasar si el proxy está funcionando correctamente
    console.warn(`⚠️  Ruta /api no capturada por proxy: ${req.method} ${req.path}`);
    return res.status(404).json({ error: 'API endpoint not found' });
  }
  
  // Si llegamos aquí, express.static NO encontró el archivo
  // Esto puede ser:
  // 1. Una ruta de la SPA (como /clientes, /dashboard) → servir index.html
  // 2. Un archivo estático que no existe → servir index.html también (SPA routing)
  // React Router manejará la ruta en el cliente
  console.log(`📄 Frontend (SPA): Sirviendo index.html para ruta: ${req.method} ${req.path}`);
  const indexPath = path.join(__dirname, 'dist', 'index.html');
  res.sendFile(indexPath, (err) => {
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
