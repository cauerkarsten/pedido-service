FROM python:3.12-slim

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Só o código da aplicação (tests/ e arquivos de CI ficam fora, ver .dockerignore)
COPY app ./app

# O Render informa a porta pela variável PORT; localmente o padrão é 8000.
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
