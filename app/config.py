import os

ESTOQUE_SERVICE_URL = os.getenv("ESTOQUE_SERVICE_URL", "http://localhost:8002").rstrip("/")

# Tempo máximo (em segundos) esperando o estoque responder. No Render grátis o
# estoque "dorme" sem uso e a primeira requisição pode levar quase um minuto.
ESTOQUE_TIMEOUT = float(os.getenv("ESTOQUE_TIMEOUT", "60"))

# Swagger (/docs e /redoc): ligado por padrão, desligado com ENABLE_DOCS=false.
ENABLE_DOCS = os.getenv("ENABLE_DOCS", "true").lower() in ("1", "true", "yes")
