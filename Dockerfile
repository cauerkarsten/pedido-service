FROM python:3.15-slim

WORKDIR /code

COPY requirements.txt .
# --only-binary: instala só pacotes já compilados (wheels), sem rodar scripts de setup
RUN pip install --no-cache-dir --only-binary :all: -r requirements.txt

# Só o código da aplicação (tests/ e arquivos de CI ficam fora, ver .dockerignore)
COPY app ./app

# Roda sem root dentro do container
RUN useradd --create-home --uid 1000 appuser
USER appuser

# O Render informa a porta pela variável PORT; localmente o padrão é 8000.
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
