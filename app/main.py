from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy.orm import Session

from app import service
from app.config import ENABLE_DOCS
from app.db import get_db, init_db
from app.estoque_client import EstoqueIndisponivelError
from app.schemas import PedidoCreate, PedidoResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Cria as tabelas no Postgres assim que a aplicação sobe."""
    init_db()
    yield


app = FastAPI(
    title="Pedido Service",
    description="Microsserviço de pedidos. Reserva e estorna itens no estoque-service (Saga).",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if ENABLE_DOCS else None,
    redoc_url="/redoc" if ENABLE_DOCS else None,
    openapi_url="/openapi.json" if ENABLE_DOCS else None,
)

# Métricas no formato do Prometheus em /metrics (requisições, latência, status).
Instrumentator(excluded_handlers=["/metrics"]).instrument(app).expose(
    app, include_in_schema=False
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/pedidos", status_code=201, response_model=PedidoResponse)
def criar_pedido(pedido: PedidoCreate, db: Session = Depends(get_db)):
    """RF01 - Criação de Pedido. Dispara a Saga (reserva no estoque)."""
    return service.criar_pedido(db, pedido.codigo_produto, pedido.quantidade)


@app.get("/pedidos/{pedido_id}", response_model=PedidoResponse)
def obter_pedido(pedido_id: str, db: Session = Depends(get_db)):
    """RF02 - Consulta de Pedido."""
    try:
        return service.consultar_pedido(db, pedido_id)
    except service.PedidoNaoEncontradoError as erro:
        raise HTTPException(status_code=404, detail=str(erro))


@app.put("/pedidos/{pedido_id}/cancelar", response_model=PedidoResponse)
def cancelar_pedido(pedido_id: str, db: Session = Depends(get_db)):
    """RF03 - Cancelamento/Compensação manual."""
    try:
        return service.cancelar_pedido(db, pedido_id)
    except service.PedidoNaoEncontradoError as erro:
        raise HTTPException(status_code=404, detail=str(erro))
    except EstoqueIndisponivelError as erro:
        raise HTTPException(status_code=503, detail=str(erro))
