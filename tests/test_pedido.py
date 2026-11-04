from unittest.mock import MagicMock, patch

import pytest
import requests
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import estoque_client
from app.db import Base, get_db
from app.estoque_client import EstoqueIndisponivelError
from app.main import app

# Banco de testes: SQLite em memória. Não depende do Postgres estar rodando.
# Em produção (docker-compose), a app usa DATABASE_URL (Postgres) normalmente;
# aqui só trocamos a implementação da dependência get_db para os testes.
engine_teste = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
SessionLocalTeste = sessionmaker(autocommit=False, autoflush=False, bind=engine_teste)


def _get_db_teste():
    db = SessionLocalTeste()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _get_db_teste

client = TestClient(app)


@pytest.fixture(autouse=True)
def recriar_tabelas():
    Base.metadata.create_all(bind=engine_teste)
    yield
    Base.metadata.drop_all(bind=engine_teste)


def _resposta_falsa(status_code: int) -> MagicMock:
    resposta = MagicMock()
    resposta.status_code = status_code
    return resposta


def test_health():
    resposta = client.get("/health")
    assert resposta.status_code == 200


@patch("app.service.estoque_client.reservar_no_estoque")
def test_criar_pedido_com_estoque_disponivel_fica_confirmado(mock_reservar):
    mock_reservar.return_value = _resposta_falsa(200)

    resposta = client.post(
        "/pedidos", json={"codigo_produto": "P1", "quantidade": 2}
    )

    assert resposta.status_code == 201
    dados = resposta.json()
    assert dados["status"] == "CONFIRMADO"
    mock_reservar.assert_called_once_with("P1", 2)


@patch("app.service.estoque_client.reservar_no_estoque")
def test_criar_pedido_sem_estoque_fica_cancelado(mock_reservar):
    mock_reservar.return_value = _resposta_falsa(400)

    resposta = client.post(
        "/pedidos", json={"codigo_produto": "P2", "quantidade": 100}
    )

    assert resposta.status_code == 201
    dados = resposta.json()
    assert dados["status"] == "CANCELADO"


@patch("app.service.estoque_client.reservar_no_estoque")
def test_consultar_pedido_existente(mock_reservar):
    mock_reservar.return_value = _resposta_falsa(200)
    criado = client.post(
        "/pedidos", json={"codigo_produto": "P3", "quantidade": 1}
    ).json()

    resposta = client.get(f"/pedidos/{criado['id']}")

    assert resposta.status_code == 200
    assert resposta.json()["id"] == criado["id"]


def test_consultar_pedido_inexistente_retorna_404():
    resposta = client.get("/pedidos/id-que-nao-existe")
    assert resposta.status_code == 404


@patch("app.service.estoque_client.estornar_no_estoque")
@patch("app.service.estoque_client.reservar_no_estoque")
def test_cancelar_pedido_confirmado_aciona_estorno(mock_reservar, mock_estornar):
    mock_reservar.return_value = _resposta_falsa(200)
    mock_estornar.return_value = _resposta_falsa(200)

    criado = client.post(
        "/pedidos", json={"codigo_produto": "P4", "quantidade": 3}
    ).json()

    resposta = client.put(f"/pedidos/{criado['id']}/cancelar")

    assert resposta.status_code == 200
    assert resposta.json()["status"] == "CANCELADO"
    mock_estornar.assert_called_once_with("P4", 3)


def test_metrics_expoe_formato_prometheus():
    client.get("/health")

    resposta = client.get("/metrics")

    assert resposta.status_code == 200
    assert "http_requests_total" in resposta.text


@patch("app.service.estoque_client.reservar_no_estoque")
def test_criar_pedido_com_estoque_fora_do_ar_fica_cancelado(mock_reservar):
    mock_reservar.side_effect = EstoqueIndisponivelError("timeout")

    resposta = client.post(
        "/pedidos", json={"codigo_produto": "P5", "quantidade": 1}
    )

    assert resposta.status_code == 201
    assert resposta.json()["status"] == "CANCELADO"


@patch("app.service.estoque_client.estornar_no_estoque")
@patch("app.service.estoque_client.reservar_no_estoque")
def test_cancelar_com_estoque_fora_do_ar_retorna_503_e_mantem_confirmado(
    mock_reservar, mock_estornar
):
    mock_reservar.return_value = _resposta_falsa(200)
    mock_estornar.side_effect = EstoqueIndisponivelError("timeout")
    criado = client.post(
        "/pedidos", json={"codigo_produto": "P6", "quantidade": 2}
    ).json()

    resposta = client.put(f"/pedidos/{criado['id']}/cancelar")

    assert resposta.status_code == 503
    assert client.get(f"/pedidos/{criado['id']}").json()["status"] == "CONFIRMADO"


def test_cancelar_pedido_inexistente_retorna_404():
    resposta = client.put("/pedidos/id-que-nao-existe/cancelar")
    assert resposta.status_code == 404


@patch("app.estoque_client.requests.post")
def test_cliente_estoque_envia_codigo_e_quantidade(mock_post):
    mock_post.return_value = _resposta_falsa(200)

    estoque_client.reservar_no_estoque("P7", 4)

    url = mock_post.call_args.args[0]
    assert url.endswith("/estoque/reservar")
    assert mock_post.call_args.kwargs["json"] == {"codigo": "P7", "quantidade": 4}


@patch("app.estoque_client.requests.post")
def test_cliente_estoque_converte_erro_de_rede(mock_post):
    mock_post.side_effect = requests.ConnectionError("recusada")

    with pytest.raises(EstoqueIndisponivelError):
        estoque_client.estornar_no_estoque("P8", 1)
