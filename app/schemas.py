from pydantic import BaseModel

from app.enums import StatusPedido


class PedidoCreate(BaseModel):
    codigo_produto: str
    quantidade: int


class PedidoResponse(BaseModel):
    """Schema de saída: converte o objeto ORM (PedidoORM) em JSON."""

    id: str
    codigo_produto: str
    quantidade: int
    status: StatusPedido

    model_config = {"from_attributes": True}
