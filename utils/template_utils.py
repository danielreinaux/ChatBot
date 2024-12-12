from utils.message_utils import (
    register_log,
    reply_single_message,
    reply_single_message_template,
    reply_text_message
)
from utils.openai import parse_order_items, process_response, parse_all_items
from utils.get_produtos import get_products_message
from utils.message_templates import TEMPLATES
from models.user import User
import uuid
from sqlalchemy.orm import Session
from models.whatsapp_log import WhatsAppLog

def handle_template_0(db, phone, message, message_id):
    """
    Lida com o template_value == 0 enviando a mensagem inicial e registrando o log.
    """
    reply_single_message(phone, 'template_primeiro_contato', message, 'bot')
    register_log(db, '', phone, 'template_base', message_id, 99)
    

def handle_template_99(db, phone, message, message_id):
    """
    Lida com o template_value == 99, processando a resposta do usuário e respondendo com base na opção escolhida.
    """
    # Definir as opções esperadas (1 e 2 neste caso)
    expected_options = ['1', '2']

    # Processar a mensagem do usuário usando a função flexível
    interpreted_message = process_response(message, expected_options)

    if interpreted_message == "1":
        # Sendo esse o caso, é um cliente comum
        reply_text_message(phone, TEMPLATES["template_pedido_para_casa"], [], 'bot')
        register_log(db, '', phone, 'template_base', message_id, 1)
    elif interpreted_message == "2":
        # Caso o usuário escolha a opção 2
        reply_single_message_template(
            phone, 'template_base', 'Em breve nosso consultor entrará em contato.', 'bot'
        )
        register_log(db, '', phone, 'template_base', message_id, 98)
    else:
        # Para qualquer outra resposta
        reply_single_message(phone, 'template_primeiro_contato', message, 'bot')
        register_log(db, '', phone, 'template_base', message_id, 99)

def handle_template_1(db, phone, message, message_id):
    """
    Lida com o template_value == 1, verifica se o usuário existe, cria um novo usuário se não existir,
    envia o template 'template_inicial_classificado' e registra o log.
    """
    # Verificar se o usuário já existe pelo número de telefone
    existing_user = db.query(User).filter_by(phone=phone).first()

    if not existing_user:
        # Gerar uma chave única para o novo usuário
        user_key = str(uuid.uuid4())

        # Criar um novo usuário
        new_user = User(
            key=user_key,
            phone=phone,
            full_name=message,
            email='',
            password=User.hash_password('senhatemporaria')
        )
        
        db.add(new_user)
        db.commit()
    else:
        # Se o usuário já existe, usa a chave dele
        user_key = existing_user.key

    # Enviar o template e registrar o log (parte idêntica para ambos os casos)
    reply_single_message_template(
        phone, 'template_inicial_classificado', message, 'bot'
    )
    register_log(db, user_key, phone, 'template_inicial_classificado', message_id, 2)
    

def handle_template_2(db, phone, message, message_id, last_template):
    """
    Lida com o template_value == 2, enviando opções para o usuário iniciar o pedido ou consultar a lista de produtos.
    """
    user = db.query(User).filter_by(key=last_template.user_sender).first()
    user_name = user.full_name if user else ''

    if message == "1":
        # Usuário quer começar o pedido
        reply_single_message(
            phone,
            'template_inicial_compra_nao_classificado',
            message,
            last_template.user_sender
        )

        register_log(
            db, last_template.user_sender, phone, 'template_inicial_compra_classificado', message_id, 3
        )

    elif message == "2":
        # Enviar a lista de produtos com as opções 1 e 2
        products_message = get_products_message(db)  # Gera a mensagem com a lista de produtos

        reply_single_message_template(
            phone, 'template_base', products_message, last_template.user_sender
        )

        register_log(
            db, last_template.user_sender, phone, 'template_base', message_id, 4
        )

    else:
        # Para entradas inválidas, enviar uma mensagem padrão com instruções claras
        reply_text_message(
            phone,
            'Opção invalida, por favor, selecione um número',
            [],
            'bot'
        )

        register_log(
            db, last_template.user_sender, phone, 'template_base', message_id, 2
        )


def handle_template_3(db, phone, message, message_id, last_template):
    """
    Lida com o template_value == 3, processando os itens enviados pelo usuário e enviando a confirmação do pedido.
    """
    user = db.query(User).filter_by(key=last_template.user_sender).first()
    user_name = user.full_name if user else ''

    order_data = parse_order_items(message)

    print(order_data)

    items_list = order_data.get("items", [])

    print(f'Mostrando item list: {items_list}')

    if items_list:
        # Formatar a lista de itens em string (com quebra de linha entre os itens)
        formatted_items = []
        for item in items_list:
            name = item.get("name", "")
            quantity = item.get("quantity", "")
            unit = item.get("unit", "")
            formatted_items.append(f"{name}: {quantity} {unit}")

        items_str = "\n".join(formatted_items)
    else:
        items_str = "Nenhum item encontrado."

    reply_text_message(
        phone,
        TEMPLATES["mensagem_processo_compra"],
        [items_str],
        'bot'
    )

    # Registrar log e atualizar o estado (template_value = 6)
    register_log(
        db, last_template.user_sender, phone, 'template_processo_compra', message_id, 6
    )


def handle_template_6(db: Session, phone: str, message: str, message_id: str, last_template):
    """
    Lida com o template_value == 6, processando a resposta do usuário (S ou N) para adicionar ou finalizar o pedido.
    """
    user_key = last_template.user_sender
    user_choice = message.strip().upper()

    if user_choice == "S":
        continue_order(db, phone, message_id, user_key)
    elif user_choice == "N":
        finalize_order(db, phone, message_id, user_key)
    else:
        handle_invalid_response(db, phone, message_id, user_key)


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

    formatted_items = []
    for item in all_items:
        name = item.get("name", "")
        quantity = item.get("quantity", "")
        unit = item.get("unit", "")
        formatted_items.append(f"{name}: {quantity} {unit}")

    items_str = "\n".join(formatted_items) if formatted_items else "Nenhum item encontrado."

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
