from sqlalchemy.orm import Session
from sqlalchemy.sql import text  # Import necessário para expressões SQL textuais

def get_products_message(db: Session) -> str:
    """
    Consulta os produtos no banco de dados agrupados por classificação e formata uma mensagem no template base com markdown.
    """
    query = text("""
        SELECT classificacao, produto, valor, unidade
        FROM produtos
        WHERE deleted_at IS NULL
        ORDER BY classificacao, produto
    """)
    products = db.execute(query).fetchall()

    classification_groups = {}
    for classificacao, produto, valor, unidade in products:
        if classificacao not in classification_groups:
            classification_groups[classificacao] = []
        classification_groups[classificacao].append(f"{produto}: {valor} {unidade}")

    # Construir a mensagem com markdown
    message = "*Produtos disponíveis:* "
    for classificacao, items in classification_groups.items():
        items_str = " | ".join(items)
        message += f"*{classificacao}:* {items_str} | "

    # Adicionar opções ao final
    options_message = "1️⃣ Voltar ao menu principal | 2️⃣ Encerrar atendimento"
    message += options_message

    # Remover espaços consecutivos
    message = " ".join(message.split())

    return message.strip()