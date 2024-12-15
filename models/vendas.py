from sqlalchemy import Column, Integer, Numeric, String, DateTime, text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.ext.declarative import declarative_base
import uuid
from database.base import Base

Base = declarative_base()

class Vendas(Base):
    __tablename__ = 'vendas'

    id = Column(Integer, primary_key=True, autoincrement=True)
    guid = Column(UUID(as_uuid=True), nullable=False, default=uuid.uuid4)
    produtos = Column(JSONB)
    data_compra = Column(DateTime(timezone=True))
    valor_total = Column(Numeric(12,2))
    status = Column(String(255))
    deleted_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=text('now()'))
    updated_at = Column(DateTime(timezone=True), server_default=text('now()'), onupdate=text('now()'))
    forma_pagamento = Column(String, nullable=True)

    # Agora adicionamos a ForeignKey aqui também:
    phone = Column(String(15))
