FROM python:3.11-slim

# Variables de entorno para Python
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Instalar dependencias del sistema (optimizado)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copiar solo requirements primero (cache de Docker)
COPY requirements.txt .

# Instalar dependencias Python
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación
COPY . .

# Crear usuario no-root para mayor seguridad
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Railway asigna PORT dinámicamente
EXPOSE 8000

# Script de inicio con migraciones
CMD ["sh", "-c", "\
    echo '🚀 Iniciando aplicación en Railway...' && \
    echo '📊 Ejecutando migraciones de base de datos...' && \
    alembic upgrade head && \
    echo '✅ Migraciones completadas' && \
    echo '🌐 Iniciando servidor en puerto ${PORT:-8000}...' && \
    uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --log-level info\
"]
