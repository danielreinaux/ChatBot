from utils.message_utils import (
    register_log,
    reply_single_message,
    reply_single_message_template,
    reply_text_message
)
from utils.openai import parse_order_items, process_response, parse_items_to_remove, parse_items_to_modify, parse_final_order_from_message, parse_customer_data
from utils.get_produtos import get_products_message
from utils.message_templates import TEMPLATES
from models.user import User
import uuid
from sqlalchemy.orm import Session
from models.whatsapp_log import WhatsAppLog
from utils.aux_utils import format_order_items, finalize_order, continue_order, handle_invalid_response, get_order_items_from_logs, remove_selected_items, respond_with_updated_order, get_last_final_list_message, create_venda
from sqlalchemy import text

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
            phone, 'template_base', 'Em breve nossa equipe entrará em contato para atendê-lo', 'bot'
        )
        register_log(db, '', phone, 'template_base', message_id, 98)
        # Gatilho por enquanto mockado:
        #trigger_b2b_notification(phone)
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
    order_data = parse_order_items(message)

    items_list = order_data.get("items", [])

    items_str = format_order_items(items_list)

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

def handle_template_4(db, phone, message, message_id, last_template):
    """
    Lida com o template_value == 4, permitindo ao usuário voltar ao menu principal ou encerrar o atendimento.
    """
    user_key = last_template.user_sender
    user = db.query(User).filter_by(key=user_key).first()
    user_name = user.full_name if user else ''

    if message == "1":
        # Voltar ao menu principal
        reply_single_message_template(
            phone, 'template_inicial_classificado', user_name, 'bot'
        )
        register_log(db, user_key, phone, 'template_inicial_classificado', message_id, 2)
    elif message == "2":
        # Encerrar atendimento
        reply_single_message_template(
            phone, 'template_base', 'Atendimento encerrado. Obrigado!', 'bot'
        )
        register_log(db, user_key, phone, 'template_base', message_id, 5)

def handle_template_5(db, phone, message, message_id, last_template):
    """
    Lida com o template_value == 5, informando que o atendimento já foi encerrado.
    """
    user_key = last_template.user_sender
    user = db.query(User).filter_by(key=user_key).first()
    user_name = user.full_name if user else ''

    reply_single_message(
        phone, 'template_base',
        'O atendimento já foi encerrado. Caso necessite de algo mais, por favor inicie uma nova conversa. 😊',
        'bot'
    )
    register_log(db, user_key, phone, 'template_base', message_id, 0)
    
def handle_template_7(db: Session, phone: str, message: str, message_id: str, last_template):
    user_key = last_template.user_sender
    user = db.query(User).filter_by(key=user_key).first()
    user_choice = message.strip().upper()
    
    
    last_sale = db.execute(
            text("""
                SELECT forma_pagamento 
                FROM vendas 
                WHERE phone = :phone
                ORDER BY created_at DESC
                LIMIT 1
            """),
            {"phone": phone}
        ).fetchone()

    if user_choice == "S":
        cliente = db.execute(
            text("SELECT * FROM clientes WHERE telefone = :telefone"),
            {"telefone": phone}
        ).fetchone()

        if cliente:
            # Cliente já existe, tem dados
            email = cliente.email
            endereco = cliente.endereco
            forma_pagamento = last_sale.forma_pagamento if last_sale else "Não informado"

            reply_text_message(
                phone,
                f"Seus dados cadastrados são:\n"
                f"Email: {email}\n"
                f"Endereço: {endereco}\n"
                f"Forma de pagamento: {forma_pagamento}\n\n"
                "Tudo certo com esses dados?\n\nS = Sim\nN = Não",
                [], user_key
            )
            # Agora aguarda a resposta no template 15
            register_log(db, user_key, phone, "Confirmar dados existentes", message_id, 15)

        else:
            # Não existe o cliente cadastrado, pedir dados
            reply_text_message(
                phone,
                "Não encontramos seus dados de cadastro. Por favor, informe seu email, endereço e a forma que fará o pagamento (Crédito, Pix, Débito etc)\n\n"
                "Exemplo: 'Meu email é fulano@gmail.com e meu endereço é Rua Exemplo 123'",
                [],
                user_key
            )
            # Aguardar o usuário mandar os dados, template 16
            register_log(db, user_key, phone, "Solicitar dados cadastro", message_id, 16)

    elif user_choice == "N":
        # Se não está tudo certo, redirecionar para o menu de modificação (template 9)
        reply_text_message(
            phone,
            TEMPLATES["template_opcoes_modificacao"],  # Mensagem que pergunta se quer adicionar/remover/modificar
            [],
            user_key
        )
        register_log(db, user_key, phone, "Pedido para modificação", message_id, 9)
        
    else:
        reply_text_message(
            phone,
            "Por favor, responda com S (Sim) para confirmar ou N (Não) para modificar o pedido.",
            [],
            user_key
        )
        register_log(db, user_key, phone, "Resposta inválida no template 7", message_id, 7)

        
        
def handle_template_9(db, phone, message, message_id, last_template):
    """
    Lida com o template_value == 9, permitindo adicionar, remover ou modificar itens.
    """
    user_key = last_template.user_sender if last_template and last_template.user_sender else 'bot'

    # 1. Encontrar o último log com template=16 (que marca o fim do último pedido)
    last_end_log = db.query(WhatsAppLog) \
        .filter_by(phone=phone, template=13) \
        .order_by(WhatsAppLog.id.desc()) \
        .first()

    # 2. Construir a query para pegar mensagens do template=0 (itens do pedido atual)
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

    print(f'Printando as mensagens capturadas: {user_messages_text}')
    order_data = parse_order_items(user_messages_text)
    items_list = order_data.get("items", [])
    items_str = format_order_items(items_list)

    if message == "1":
        reply_text_message(
            phone,
            'Continuando seu pedido... Por favor, envie mais itens que deseja adicionar.',
            [],
            user_key
        )
        register_log(db, user_key, phone, 'template_base', message_id, 3)
    elif message == "2":
        reply_text_message(
            phone,
            f"Você escolheu remover itens. Aqui estão os pedidos:\n\n{items_str}\n\nQuais itens você deseja remover?",
            [],
            user_key
        )
        register_log(db, user_key, phone, 'template_remover_itens', message_id, 10)
    elif message == "3":
        # Modificar itens do pedido e mostrar a lista atual
        reply_text_message(
            phone,
            f"Aqui estão os itens do seu pedido atual:\n\n{items_str}\n\n"
            "Por favor, informe qual item você deseja modificar e o novo detalhe (quantidade ou unidade).\n\n"
            "Por exemplo:\n'Maçã: 5 kg' para modificar a quantidade de maçã para 5 kg.",
            [],
            user_key
        )
        register_log(db, user_key, phone, 'template_modificar_itens', message_id, 11)
    else:
        reply_text_message(
            phone,
            "Por favor, escolha uma opção válida:\n1⃣ Adicionar\n2⃣ Remover\n3⃣ Modificar",
            [],
            user_key
        )
        register_log(db, user_key, phone, 'template_opcoes_modificacao', message_id, 9)
        
def handle_template_10(db, phone, message, message_id, last_template):
    """
    Lida com o template_value == 10, removendo os itens selecionados pelo usuário.
    """
    user_key = last_template.user_sender if last_template and last_template.user_sender else 'bot'

    # Recuperar itens do pedido
    items_list = get_order_items_from_logs(db, phone)

    if not items_list:
        reply_text_message(
            phone,
            "Não há itens no seu pedido para remover.",
            [],
            'bot'
        )
        register_log(db, user_key, phone, 'template_sem_itens', message_id, 9)
        return

    # Identificar itens para remover usando OpenAI
    items_to_remove = parse_items_to_remove(message, items_list) or []

    if not items_to_remove:
        reply_text_message(
            phone,
            "Não consegui identificar os itens que você deseja remover. Por favor, tente novamente.",
            [],
            'bot'
        )
        register_log(db, user_key, phone, 'template_remover_itens_falha', message_id, 10)
        return

    # Remover itens e obter lista atualizada
    updated_items_list = remove_selected_items(items_list, items_to_remove)

    if not updated_items_list:
        reply_text_message(
            phone,
            "Todos os itens foram removidos do pedido. O pedido agora está vazio.",
            [],
            'bot'
        )
        register_log(db, user_key, phone, 'template_pedido_vazio', message_id, 9)
        return

    respond_with_updated_order(db, phone, items_to_remove, updated_items_list, message_id, user_key)


def handle_template_11(db, phone, message, message_id, last_template):
    user_key = last_template.user_sender if last_template and last_template.user_sender else 'bot'

    # Recuperar itens do pedido
    items_list = get_order_items_from_logs(db, phone)

    if not items_list:
        reply_text_message(
            phone,
            "Não há itens no seu pedido para modificar.",
            [],
            'bot'
        )
        register_log(db, user_key, phone, 'template_sem_itens', message_id, 9)
        return

    # Identificar modificações usando a função modularizada
    items_to_modify = parse_items_to_modify(message, items_list)

    if not items_to_modify:
        reply_text_message(
            phone,
            "Não consegui identificar os itens que você deseja modificar. Por favor, tente novamente.",
            [],
            'bot'
        )
        register_log(db, user_key, phone, 'template_modificar_itens_falha', message_id, 11)
        return

    # Aplicar as modificações nos itens originais
    # Aqui assumimos que o "items_to_modify" retorna itens no mesmo formato da lista original
    for modified_item in items_to_modify:
        for idx, original_item in enumerate(items_list):
            if original_item["name"] == modified_item["name"]:
                items_list[idx] = modified_item  # Substitui o original pelo modificado

    # Gerar string dos itens modificados
    modified_items_str = "\n".join(
        [f"{item['name']}: {item['quantity']} {item['unit']}" for item in items_to_modify]
    )

    # Gerar string da lista completa atualizada
    updated_items_str = format_order_items(items_list)

    # Agora, exibir tanto os itens modificados quanto a lista atualizada
    reply_text_message(
        phone,
        f"Os seguintes itens foram modificados:\n\n{modified_items_str}\n\n"
        f"Lista atualizada final:\n{updated_items_str}\n\n"
        "Está tudo certo? Responda com S (Sim) para finalizar o pedido ou N (Não) para modificar novamente.",
        [],
        'bot'
    )

    register_log(db, user_key, phone, 'template_modificar_itens', message_id, 7)

def handle_template_12(db: Session, phone: str, message: str, message_id: str, last_template):
    user_key = last_template.user_sender
    user = db.query(User).filter_by(key=user_key).first()
    
    reply_text_message(
        phone,
        "Vimos que você já realizou um pedido.\n\n"
        "1️⃣ Ver status e itens do pedido\n"
        "2️⃣ Fazer um novo pedido",
        [],
        user_key
    )
    # Agora, aguardamos a escolha do usuário no template 14
    register_log(db, user_key, phone, "Menu intermediário após pedido", message_id, 13)
    
def handle_template_13(db: Session, phone: str, message: str, message_id: str, last_template):
    user_key = last_template.user_sender
    user = db.query(User).filter_by(key=user_key).first()
    choice = message.strip()

    if choice == "1":
        # Exibe status do último pedido
        venda = db.execute(
            text("""
              SELECT * FROM vendas
              WHERE phone = :phone
              ORDER BY created_at DESC
              LIMIT 1
          """), {"phone": user.phone}).fetchone()

        if venda:
            items_list = venda.produtos
            status = venda.status
            items_str = format_order_items(items_list)

            reply_text_message(
                phone,
                f"Seu pedido atual está com status: {status}.\n\n"
                f"Aqui estão os itens do seu pedido:\n{items_str}\n\n"
                "Algo mais que possa ajudar?",
                [],
                user_key
            )

            register_log(db, user_key, phone, 'template_inicial_classificado', message_id, 12)

        else:
            reply_text_message(
                phone,
                "Não encontramos nenhum pedido registrado para este número.",
                [],
                user_key
            )
            # Mesmo sem pedidos, chamar menu inicial
            user_name = user.full_name if user else ''
            reply_single_message_template(
                phone, 'template_inicial_classificado', user_name, 'bot'
            )
            register_log(db, user_key, phone, 'template_inicial_classificado', message_id, 2)

    elif choice == "2":
        # Fazer novo pedido - vai direto ao menu inicial classificado
        user_name = user.full_name if user else ''
        reply_single_message_template(
            phone, 'template_inicial_classificado', user_name, 'bot'
        )
        register_log(db, user_key, phone, 'template_inicial_classificado', message_id, 2)

    else:
        # Se inválido, repete as opções do template 14
        reply_text_message(
            phone,
            "Opção inválida. Por favor, escolha:\n1️⃣ Ver status do pedido\n2️⃣ Fazer um novo pedido",
            [],
            user_key
        )
        register_log(db, user_key, phone, "menu_pos_finalizacao_invalido", message_id, 13)

def handle_template_15(db: Session, phone: str, message: str, message_id: str, last_template):
    user_key = last_template.user_sender
    user = db.query(User).filter_by(key=user_key).first()
    user_choice = message.strip().upper()

    if user_choice == "S":
        # Recuperar a forma de pagamento do último log com template 16
        last_payment_log = db.query(WhatsAppLog) \
            .filter_by(phone=phone, template=16) \
            .order_by(WhatsAppLog.id.desc()) \
            .first()

        forma_pagamento = ""
        if last_payment_log and "Forma de pagamento:" in last_payment_log.message:
            forma_pagamento = last_payment_log.message.split("Forma de pagamento:")[1].strip()

        # Dados confirmados, agora criar a venda
        last_final_list_msg = get_last_final_list_message(db, phone)
        if last_final_list_msg:
            order_data = parse_final_order_from_message(last_final_list_msg)
            items_list = order_data.get("items", [])
            create_venda(db, user, items_list, pagamento=forma_pagamento)

        reply_text_message(
            phone,
            "Pedido encaminhado para nossa loja, agradecemos o pedido e traremos atualizações nos próximos dias.",
            [], user_key
        )
        register_log(db, user_key, phone, "Pedido confirmado com dados existentes", message_id, 12)

    elif user_choice == "N":
        # Usuário quer alterar os dados
        reply_text_message(
            phone,
            "Entendi, por favor informe os campos email, endereço e forma de pagamento atualizados.",
            [], user_key
        )
        register_log(db, user_key, phone, "Alterar dados", message_id, 16)

    else:
        reply_text_message(
            phone,
            "Por favor, responda com S (Sim) ou N (Não).",
            [], user_key
        )
        register_log(db, user_key, phone, "Resposta inválida no template 15", message_id, 15)


def handle_template_16(db: Session, phone: str, message: str, message_id: str, last_template):
    user_key = last_template.user_sender
    user = db.query(User).filter_by(key=user_key).first()

    # Chama a função OpenAI para extrair email e endereço
    customer_data = parse_customer_data(message)  # retorna algo como {"email": "...", "endereco": "..."}

    email = customer_data.get("email", "")
    endereco = customer_data.get("endereco", "")
    forma_pagamento = customer_data.get("forma_pagamento", "")

    if not email or not endereco or not forma_pagamento:
        reply_text_message(
            phone,
            "Não consegui identificar seu email, endereço ou forma de pagamento. Por favor, tente novamente.\n"
            "Informe seu email, endereço e forma de pagamento (Crédito, Pix, Débito etc) em uma frase clara.",
            [], user_key
        )
        register_log(db, user_key, phone, 'Dados incompletos', message_id, 16)
        return

    
    new_guid = str(uuid.uuid4())
    user_name = user.full_name if user and user.full_name else "Nome não informado"
    
    db.execute(text("""
        INSERT INTO clientes (guid, nome, telefone, email, endereco) 
        VALUES (:guid, :nome, :telefone, :email, :endereco)
        ON CONFLICT (telefone) DO UPDATE 
        SET nome = EXCLUDED.nome, email = EXCLUDED.email, endereco = EXCLUDED.endereco
    """), {"guid": new_guid, "nome": user_name, "telefone": phone, "email": email, "endereco": endereco})

    db.commit()

    # Registrar a forma de pagamento no log temporariamente
    register_log(db, user_key, phone, f"Forma de pagamento: {forma_pagamento}", message_id, 16)

    # Confirmação para o usuário
    reply_text_message(
        phone,
        f"Entendi, seus dados são:\nEmail: {email}\nEndereço: {endereco}\nForma de pagamento: {forma_pagamento}\n\n"
        "Tudo certo?\nS = Sim\nN = Não",
        [], user_key
    )
    
    register_log(db, user_key, phone, 'Confirmar dados inseridos', message_id, 15)
