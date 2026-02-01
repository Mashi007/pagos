/**
 * Servidor simple para servir archivos estáticos en Render
 * Compatible con Web Service de Render
 */
import express from 'express';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 3000;

// Configurar headers para archivos estáticos
app.use(express.static(path.join(__dirname, 'dist'), {
  maxAge: '1d',
  etag: true,
  lastModified: true,
  setHeaders: (res, path) => {
    // Headers específicos para archivos JavaScript y CSS
    if (path.endsWith('.js')) {
      res.setHeader('Content-Type', 'application/javascript; charset=utf-8');
    } else if (path.endsWith('.css')) {
      res.setHeader('Content-Type', 'text/css; charset=utf-8');
    }
  }
}));

// Manejar todas las rutas y servir index.html (para SPA)
// IMPORTANTE: Esta ruta debe ir DESPUÉS de express.static
app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'dist', 'index.html'), {
    headers: {
      'Content-Type': 'text/html; charset=utf-8'
    }
  });
});

app.listen(PORT, () => {
  console.log(`Servidor corriendo en puerto ${PORT}`);
  console.log(`Sirviendo archivos desde: ${path.join(__dirname, 'dist')}`);
  console.log(`Aplicación disponible en: http://localhost:${PORT}`);
});
