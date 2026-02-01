/**
 * Servidor simple para servir archivos estáticos en Render
 * Compatible con Web Service de Render
 */
import express from 'express';
import path from 'path';
import { fileURLToPath } from 'url';
import fs from 'fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 3000;

// Verificar que el directorio dist existe
const distPath = path.join(__dirname, 'dist');
if (!fs.existsSync(distPath)) {
  console.error(`ERROR: El directorio 'dist' no existe en ${distPath}`);
  console.error('Asegúrate de ejecutar "npm run build" antes de iniciar el servidor');
  process.exit(1);
}

// Middleware para logging de requests
app.use((req, res, next) => {
  console.log(`${new Date().toISOString()} - ${req.method} ${req.path}`);
  next();
});

// Configurar headers de seguridad
app.use((req, res, next) => {
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('X-XSS-Protection', '1; mode=block');
  next();
});

// Configurar headers para archivos estáticos
app.use(express.static(distPath, {
  maxAge: '1d',
  etag: true,
  lastModified: true,
  setHeaders: (res, filePath) => {
    // Headers específicos para archivos JavaScript y CSS
    if (filePath.endsWith('.js')) {
      res.setHeader('Content-Type', 'application/javascript; charset=utf-8');
      res.setHeader('Cache-Control', 'public, max-age=86400'); // 1 día
    } else if (filePath.endsWith('.css')) {
      res.setHeader('Content-Type', 'text/css; charset=utf-8');
      res.setHeader('Cache-Control', 'public, max-age=86400'); // 1 día
    } else if (filePath.endsWith('.html')) {
      res.setHeader('Cache-Control', 'no-cache, no-store, must-revalidate');
    }
  }
}));

// Health check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({ 
    status: 'ok', 
    timestamp: new Date().toISOString(),
    distExists: fs.existsSync(distPath)
  });
});

// Manejar todas las rutas y servir index.html (para SPA)
// IMPORTANTE: Esta ruta debe ir DESPUÉS de express.static
app.get('*', (req, res) => {
  const indexPath = path.join(distPath, 'index.html');
  
  if (!fs.existsSync(indexPath)) {
    console.error(`ERROR: index.html no encontrado en ${indexPath}`);
    res.status(500).send(`
      <html>
        <head><title>Error - Archivo no encontrado</title></head>
        <body>
          <h1>Error 500</h1>
          <p>El archivo index.html no se encontró en el directorio dist.</p>
          <p>Por favor, ejecuta "npm run build" para generar los archivos de producción.</p>
          <p>Ruta esperada: ${indexPath}</p>
        </body>
      </html>
    `);
    return;
  }
  
  res.sendFile(indexPath, {
    headers: {
      'Content-Type': 'text/html; charset=utf-8',
      'Cache-Control': 'no-cache, no-store, must-revalidate'
    }
  }, (err) => {
    if (err) {
      console.error(`Error enviando index.html: ${err.message}`);
      res.status(500).send(`
        <html>
          <head><title>Error</title></head>
          <body>
            <h1>Error 500</h1>
            <p>Error al servir el archivo: ${err.message}</p>
          </body>
        </html>
      `);
    }
  });
});

// Manejo de errores
app.use((err, req, res, next) => {
  console.error(`Error en servidor: ${err.message}`);
  console.error(err.stack);
  res.status(500).json({ 
    error: 'Error interno del servidor',
    message: process.env.NODE_ENV === 'development' ? err.message : undefined
  });
});

app.listen(PORT, () => {
  console.log(`========================================`);
  console.log(`🚀 Servidor iniciado correctamente`);
  console.log(`📦 Puerto: ${PORT}`);
  console.log(`📁 Directorio dist: ${distPath}`);
  console.log(`✅ Dist existe: ${fs.existsSync(distPath)}`);
  console.log(`🌐 Aplicación disponible en: http://localhost:${PORT}`);
  console.log(`💚 Health check: http://localhost:${PORT}/health`);
  console.log(`========================================`);
  
  // Verificar archivos importantes
  const indexPath = path.join(distPath, 'index.html');
  if (fs.existsSync(indexPath)) {
    console.log(`✅ index.html encontrado`);
  } else {
    console.error(`❌ ERROR: index.html NO encontrado en ${indexPath}`);
  }
});
