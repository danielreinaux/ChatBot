from utils.message_utils import (
    register_log,
    reply_text_message
)
from utils.openai import parse_order_items, parse_all_items
from utils.message_templates import TEMPLATES
from sqlalchemy.orm import Session
from models.whatsapp_log import WhatsAppLog



def continue_order(db: Session, phone: str, message_id: str, user_key: str):
    """
    Função para continuar o pedido quando o usuário escolhe 'S'.
    """
    reply_text_message(
        phone,
        'Continuando seu pedido... Por favor, envie mais itens que deseja adicionar.',
        [],
        'bot'
    )
    register_log(db, user_key, phone, 'template_base', message_id, 3)


def finalize_order(db: Session, phone: str, message_id: str, user_key: str):
    """
    Função para finalizar o pedido quando o usuário escolhe 'N'.
    """
    all_user_messages = db.query(WhatsAppLog) \
        .filter_by(phone=phone) \
        .filter(WhatsAppLog.user_sender == 'bot') \
        .filter(WhatsAppLog.template == 0) \
        .order_by(WhatsAppLog.id.asc()) \
        .all()

    filtered_messages = [
        log_entry.message for log_entry in all_user_messages
        if not log_entry.message.startswith("Por exemplo") and "por favor" in log_entry.message.lower()
    ]

    user_messages_text = "\n".join(filtered_messages)

    all_items = []
    for log_entry in filtered_messages:
        parsed_data = parse_order_items(log_entry)
        msg_items = parsed_data.get("items", [])
        all_items.extend(msg_items)

    all_items = parse_all_items(user_messages_text)

    items_str = format_order_items(all_items)


    reply_text_message(
        phone,
        TEMPLATES["template_finalizar_pedido"],
        [items_str],
        user_key
    )

    register_log(db, user_key, phone, 'template_finalizar_pedido', message_id, 7)


def handle_invalid_response(db: Session, phone: str, message_id: str, user_key: str):
    """
    Função para tratar respostas inválidas.
    """
    reply_text_message(
        phone,
        'Por favor, responda S (Sim) ou N (Não).',
        [],
        'bot'
    )
    register_log(db, user_key, phone, 'template_base', message_id, 6)

def format_order_items(items_list):
    """
    Formata a lista de itens em uma string.

    Args:
        items_list (list): Lista de dicionários com itens.

    Returns:
        str: String formatada com os itens ou uma mensagem padrão se a lista estiver vazia.
    """
    if not items_list:
        return "Nenhum item encontrado."

    return "\n".join([
        f"{item.get('name', '')}: {item.get('quantity', '')} {item.get('unit', '')}"
        for item in items_list
    ])
