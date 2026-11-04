import uuid

from sqlalchemy.orm import Session

from app import estoque_client
from app.enums import StatusPedido
from app.estoque_client import EstoqueIndisponivelError
from app.models import PedidoORM


class PedidoNaoEncontradoError(Exception):
    pass


def criar_pedido(db: Session, codigo_produto: str, quantidade: int) -> PedidoORM:
    pedido_id = str(uuid.uuid4())
    pedido = PedidoORM(
        id=pedido_id,
        codigo_produto=codigo_produto,
        quantidade=quantidade,
        status=StatusPedido.PENDENTE.value,
    )
    db.add(pedido)
    db.commit()
    db.refresh(pedido)

    # T1 da Saga: tenta reservar no estoque-service via HTTP.
    # Se o estoque não responder, o pedido é cancelado em vez de ficar PENDENTE.
    try:
        resposta = estoque_client.reservar_no_estoque(codigo_produto, quantidade)
        reservado = resposta.status_code == 200
    except EstoqueIndisponivelError:
        reservado = False

    pedido.status = (
        StatusPedido.CONFIRMADO.value if reservado else StatusPedido.CANCELADO.value
    )
    db.commit()
    db.refresh(pedido)
    return pedido


def consultar_pedido(db: Session, pedido_id: str) -> PedidoORM:
    pedido = db.get(PedidoORM, pedido_id)
    if pedido is None:
        raise PedidoNaoEncontradoError(f"Pedido {pedido_id} não encontrado")
    return pedido


def cancelar_pedido(db: Session, pedido_id: str) -> PedidoORM:
    pedido = consultar_pedido(db, pedido_id)

    if pedido.status == StatusPedido.CONFIRMADO.value:
        # C1 da Saga: compensação, desfaz a reserva feita no estoque-service.
        # Se o estoque não responder, a exceção sobe e o pedido continua
        # CONFIRMADO, para o cancelamento poder ser tentado de novo.
        estoque_client.estornar_no_estoque(pedido.codigo_produto, pedido.quantidade)

    pedido.status = StatusPedido.CANCELADO.value
    db.commit()
    db.refresh(pedido)
    return pedido
