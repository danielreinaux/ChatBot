from database.base import Base, engine
from database.session import get_db
from models.whatsapp_log import WhatsAppLog

def init_db():
    # Criação das tabelas no banco de dados
    Base.metadata.create_all(bind=engine)
    print("✅ Banco de dados inicializado com sucesso!")

def test_connection():
    try:
        db = next(get_db())
        print("✅ Conexão com o banco de dados estabelecida!")
    except Exception as e:
        print(f"❌ Erro ao conectar ao banco de dados: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_connection()
    init_db()
