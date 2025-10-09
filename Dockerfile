FROM python:3.11-slim

# Variables de entorno para optimización
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copiar requirements e instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY . .

# Crear usuario no-root
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Railway asigna PORT dinámicamente
EXPOSE 8000

# Comando de inicio con migraciones automáticas
CMD ["sh", "-c", "\
    echo '🚀 Iniciando aplicación...' && \
    echo '📊 Ejecutando migraciones...' && \
    alembic upgrade head && \
    echo '✅ Migraciones completadas' && \
    echo '🌐 Iniciando servidor en puerto ${PORT:-8000}...' && \
    uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --log-level info\
"]
