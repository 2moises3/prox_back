# ============================================
# PROXVEL Backend - Dockerfile
# Imagen base: Python 3.12 slim
# ============================================

FROM python:3.12-slim

# Evitar prompts interactivos durante la instalación
ENV DEBIAN_FRONTEND=noninteractive

# Instalar dependencias del sistema necesarias para psycopg2
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpq-dev gcc && \
    rm -rf /var/lib/apt/lists/*

# Definir directorio de trabajo
WORKDIR /app

# Copiar requirements primero para aprovechar la caché de capas
COPY requirements.txt .

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el proyecto
COPY . .

# Crear directorios necesarios si no existen
RUN mkdir -p app/data app/exports

# Exponer el puerto del backend
EXPOSE 8000

# Comando de inicio
CMD ["python", "run.py"]
