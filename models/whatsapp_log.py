from sqlalchemy import Column, Integer, String, Boolean, DateTime
from database.base import Base
from datetime import datetime

class WhatsAppLog(Base):
    __tablename__ = 'whatsapp_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_sender = Column(String, nullable=True)
    phone = Column(String, nullable=False)
    message = Column(String, nullable=True)
    sent = Column(Boolean, default=False)
    delivered = Column(Boolean, default=False)
    read = Column(Boolean, default=False)
    message_id = Column(String, unique=True, nullable=False)
    template = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<WhatsAppLog(id={self.id}, phone={self.phone}, message_id={self.message_id})>"
