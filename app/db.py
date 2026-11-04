"""
Camada de CONEXÃO COM O BANCO.
Lê a URL do Postgres da variável de ambiente DATABASE_URL (definida no
docker-compose.yml localmente e nas Environment Variables do Render) e expõe
a sessão do SQLAlchemy para o resto da app.
"""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://admin_pedido:123@localhost:5433/pedido_db"
)

# Alguns provedores entregam a URL como "postgres://", que o SQLAlchemy 2 não aceita.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# pool_pre_ping testa a conexão antes de usar: o banco na nuvem derruba
# conexões paradas enquanto o serviço "dorme".
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """Dependency do FastAPI: abre uma sessão por requisição e sempre fecha."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Cria as tabelas no banco caso ainda não existam (chamado no startup)."""
    Base.metadata.create_all(bind=engine)
