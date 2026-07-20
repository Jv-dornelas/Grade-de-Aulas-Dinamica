# Imagem base oficial do Python
FROM python:3.11-slim

# Evita arquivos .pyc e força logs em tempo real no terminal
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Pasta de trabalho dentro do container
WORKDIR /app

# Copia e instala as dependências
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do projeto
COPY . /app/

# Porta do Django
EXPOSE 8000

# Comando inicial do container
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]