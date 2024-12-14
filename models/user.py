from sqlalchemy import Column, Integer, String, DateTime, func
from sqlalchemy.orm import validates
from passlib.hash import pbkdf2_sha256  # Substituímos bcrypt por pbkdf2_sha256
from database.base import Base

class User(Base):
    __tablename__ = "users"  # Nome da tabela no banco de dados

    # Colunas da tabela
    id = Column(Integer, primary_key=True, autoincrement=True)  # ID primário
    key = Column(String, nullable=False, unique=True)          # Chave única
    phone = Column(String, nullable=False, unique=True)        # Número de telefone único
    full_name = Column(String, nullable=True)                  # Nome completo (pode ser nulo)
    email = Column(String, nullable=True, unique=True)         # Email único
    password = Column(String, nullable=False)                  # Senha (armazenada como hash)
    created_at = Column(DateTime, server_default=func.now())   # Data de criação
    updated_at = Column(DateTime, onupdate=func.now())         # Data de atualização
    deleted_at = Column(DateTime, nullable=True)               # Data de exclusão (soft delete)
    

    # Validação de email (opcional)
    @validates("email")
    def validate_email(self, key, email):
        # Substituir strings vazias por None
        if email == "":
            email = None
        # Validar formato apenas se o email não for None
        if email and ("@" not in email or "." not in email):
            raise ValueError("Email inválido")
        return email

    # Métodos auxiliares para hashing de senha
    @staticmethod
    def hash_password(password: str) -> str:
        """Gera um hash para a senha."""
        return pbkdf2_sha256.hash(password)

    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """Verifica se a senha fornecida corresponde ao hash armazenado."""
        return pbkdf2_sha256.verify(password, hashed_password)

    # Representação do modelo (para fins de depuração)
    def __repr__(self):
        return f"<User(id={self.id}, email={self.email}, phone={self.phone})>"
