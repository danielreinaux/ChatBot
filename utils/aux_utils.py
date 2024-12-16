from utils.message_utils import (
    register_log,
    reply_text_message
)
from utils.openai import parse_order_items, parse_all_items
from utils.message_templates import TEMPLATES
from sqlalchemy.orm import Session
from models.whatsapp_log import WhatsAppLog
from models.vendas import Vendas
import uuid
from models.user import User
from datetime import datetime



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

    # Encontrar o último log que marca o fim do último pedido
    last_end_log = db.query(WhatsAppLog) \
        .filter_by(phone=phone, template=13) \
        .order_by(WhatsAppLog.id.desc()) \
        .first()

    query = db.query(WhatsAppLog) \
        .filter_by(phone=phone, user_sender='bot', template=0)

    if last_end_log:
        query = query.filter(WhatsAppLog.id > last_end_log.id)

    all_user_messages = query.order_by(WhatsAppLog.id.asc()).all()

    filtered_messages = [
        log_entry.message for log_entry in all_user_messages
        if not log_entry.message.startswith("Por exemplo") and 
          ("por favor" in log_entry.message.lower() or 
            "os seguintes itens foram removidos:" in log_entry.message.lower() or
            "os seguintes itens foram modificados:" in log_entry.message.lower())
    ]


    user_messages_text = "\n".join(filtered_messages)
    
    print(f'Printando as mensagens capturadas 3{user_messages_text}')

    all_items = []
    for log_entry in filtered_messages:
        parsed_data = parse_order_items(log_entry)
        msg_items = parsed_data.get("items", [])
        all_items.extend(msg_items)
    
    
      
    all_items = parse_all_items(user_messages_text)
    
    print(f'Printando o all_items: {all_items}')
    items_str = format_order_items(all_items)
    print(f'Printando o item_str: {items_str}')


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

# aux_utils.py

def get_order_items_from_logs(db, phone):
    """
    Recupera e filtra mensagens anteriores do pedido.

    Args:
        db (Session): Sessão do banco de dados.
        phone (str): Número de telefone do usuário.

    Returns:
        list: Lista de itens extraídos das mensagens anteriores.
    """
    # Encontrar o último log de final de pedido
    last_end_log = db.query(WhatsAppLog) \
        .filter_by(phone=phone, template=13) \
        .order_by(WhatsAppLog.id.desc()) \
        .first()

    query = db.query(WhatsAppLog) \
        .filter_by(phone=phone, user_sender='bot', template=0)

    if last_end_log:
        query = query.filter(WhatsAppLog.id > last_end_log.id)

    all_user_messages = query.order_by(WhatsAppLog.id.asc()).all()

    filtered_messages = [
        log_entry.message for log_entry in all_user_messages
        if not log_entry.message.startswith("Por exemplo") and 
          ("por favor" in log_entry.message.lower() or 
            "os seguintes itens foram removidos:" in log_entry.message.lower() or
            "os seguintes itens foram modificados:" in log_entry.message.lower())
    ]
    

    user_messages_text = "\n".join(filtered_messages)
    
    print(f'Printando as mensagens capturadas 1 {user_messages_text}')
    
    order_data = parse_order_items(user_messages_text)
    
    print(user_messages_text)
    
    return order_data.get("items", [])


def remove_selected_items(items_list, items_to_remove):
    """
    Remove os itens selecionados da lista de pedidos.

    Args:
        items_list (list): Lista atual de itens no pedido.
        items_to_remove (list): Lista de itens a serem removidos.

    Returns:
        list: Lista atualizada de itens após a remoção.
    """
    return [
        item for item in items_list
        if not any(
            item['name'] == removed['name'] and
            item['quantity'] == removed['quantity'] and
            item['unit'] == removed['unit']
            for removed in items_to_remove
        )
    ]


def respond_with_updated_order(db, phone, items_to_remove, updated_items_list, message_id, user_key):
    """
    Envia uma mensagem ao usuário com os itens removidos e a lista atualizada.

    Args:
        phone (str): Número de telefone do usuário.
        items_to_remove (list): Lista de itens removidos.
        updated_items_list (list): Lista atualizada de itens no pedido.
    """
    items_str = format_order_items(updated_items_list)
    removed_items_str = format_order_items(items_to_remove)

    reply_text_message(
        phone,
        f"Os seguintes itens foram removidos:\n\n{removed_items_str}\n\nLista atualizada final:\n{items_str}\n\nEstá tudo certo? Responda com S (Sim) para finalizar o pedido ou N (Não) para modificar novamente.",
        [],
        'bot'
    )

    # Registrar log da ação
    register_log(db, user_key, phone, 'template_confirmar_remocao', message_id, 7)
    
    
def simulate_order_flow(db, phone, user_key):
    """
    Simula o fluxo do pedido do backoffice inexistente, enviando mensagens de status ao cliente.
    Você pode ajustar delays (usando time.sleep) se quiser simular tempo real.
    """
    # Status 1: Análise
    reply_text_message(phone, "Seu pedido foi recebido e está em análise.", [], 'bot')
    register_log(db, user_key, phone, 'pedido_em_analise', '', 0)
    # time.sleep(2) # opcional

    # Status 2: Conferência de Pedidos
    reply_text_message(phone, "Seu pedido está correto e foi enviado para separação.", [], 'bot')
    register_log(db, user_key, phone, 'pedido_enviado_separacao', '', 0)
    # time.sleep(2) # opcional

    # Status 3: Separação
    reply_text_message(phone, "Seu pedido está sendo separado.", [], 'bot')
    register_log(db, user_key, phone, 'pedido_sendo_separado', '', 0)
    # time.sleep(2) # opcional

    # Status 4: Conferência de Peso (opcionalmente informar o cliente)
    reply_text_message(phone, "Estamos conferindo o peso dos itens do seu pedido.", [], 'bot')
    register_log(db, user_key, phone, 'conferencia_de_peso', '', 0)
    # time.sleep(2) # opcional

    # Status 5: Liberação para Entrega
    reply_text_message(phone, "Seu pedido foi liberado para entrega! Em breve você receberá sua encomenda.", [], 'bot')
    register_log(db, user_key, phone, 'pedido_liberado_entrega', '', 0)
    
def get_last_final_list_message(db: Session, phone: str) -> str:
    """
    Retorna a última mensagem do bot para este telefone que contenha "Lista atualizada Final:"
    """
    last_msg_list = db.query(WhatsAppLog) \
    .order_by(WhatsAppLog.id.desc()) \
    .all()

    for msg in last_msg_list:
        if "Lista atualizada Final:" in msg.message or "lista atualizada final" in msg.message:
            return msg.message
    return None

def create_venda(db: Session, user: User, items_list: list, pagamento: str):
    valor_total = 0.00 
    nova_venda = Vendas(
        produtos=items_list,
        data_compra=datetime.now(),
        valor_total=valor_total,
        status="Em Análise",
        phone=user.phone,  # Adiciona o phone do usuário aqui
        forma_pagamento = pagamento
    )
    db.add(nova_venda)
    db.commit()
