import requests

from app.config import ESTOQUE_SERVICE_URL, ESTOQUE_TIMEOUT


class EstoqueIndisponivelError(Exception):
    """O estoque-service não respondeu (fora do ar, timeout ou erro de rede)."""


def _post(caminho: str, codigo_produto: str, quantidade: int) -> requests.Response:
    try:
        return requests.post(
            f"{ESTOQUE_SERVICE_URL}{caminho}",
            json={"codigo": codigo_produto, "quantidade": quantidade},
            timeout=ESTOQUE_TIMEOUT,
        )
    except requests.RequestException as erro:
        raise EstoqueIndisponivelError(f"Estoque indisponível: {erro}") from erro


def reservar_no_estoque(codigo_produto: str, quantidade: int) -> requests.Response:
    return _post("/estoque/reservar", codigo_produto, quantidade)


def estornar_no_estoque(codigo_produto: str, quantidade: int) -> requests.Response:
    return _post("/estoque/estornar", codigo_produto, quantidade)
