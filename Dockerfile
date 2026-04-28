# Usar imagem oficial do Python
FROM python:3.11-slim

# Evitar que o Python gere arquivos .pyc e garantir output em tempo real
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Instalar dependências do sistema para o psycopg2
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Definir diretório de trabalho
WORKDIR /app

# Copiar requirements e instalar dependências
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o restante do código
COPY . .

# Expor a porta que o Flask usará
EXPOSE 5000

# Usar Gunicorn para produção
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:create_app()"]
