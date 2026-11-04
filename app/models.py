"""
Camada de MODELOS (ORM).
Aqui definimos como a tabela "pedidos" existe de verdade no PostgreSQL,
usando SQLAlchemy. Cada instância de PedidoORM é uma linha da tabela.
O status é guardado como texto simples (os valores vêm de StatusPedido, em app/enums.py).
"""

from sqlalchemy import Column, Integer, String

from app.db import Base


class PedidoORM(Base):
    __tablename__ = "pedidos"

    id = Column(String, primary_key=True, index=True)
    codigo_produto = Column(String, nullable=False)
    quantidade = Column(Integer, nullable=False)
    status = Column(String, nullable=False)
