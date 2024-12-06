from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from dotenv import load_dotenv
import os
from urllib.parse import quote_plus

# Carregar variáveis do .env
load_dotenv()

# Base declarativa para os modelos
Base = declarative_base()

password = quote_plus(os.getenv("DB_PASSWORD")) 
# Configuração da conexão com o banco de dados
DATABASE_URL = (
    f"postgresql+psycopg2://{os.getenv('DB_USER')}:{password}@"
    f"{os.getenv('DB_HOST')}:{os.getenv('DB_PORT')}/{os.getenv('DB_DATABASE')}"
)

# Criar a engine do SQLAlchemy
engine = create_engine(DATABASE_URL)
