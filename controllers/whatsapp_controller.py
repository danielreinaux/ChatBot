import os
import requests
from flask import request, jsonify
from models.whatsapp_log import WhatsAppLog
from database.session import get_db
from models.user import User
import uuid
from utils.openai import parse_order_items, parse_all_items
from utils.get_produtos import get_products_message
from utils.message_templates import TEMPLATES
from utils.template_utils import handle_template_0, handle_template_99, handle_template_1, handle_template_2, handle_template_3, handle_template_6
from utils.message_utils import reply_single_message, reply_single_message_template, reply_text_message, register_log, get_last_template



class WhatsAppController:
    @staticmethod
    def register_webhook():
        query = request.args  # query contém todos os parâmetros da URL

        if query.get("hub.mode") == "subscribe" and query.get("hub.verify_token") == "123":
            return jsonify(query.get("hub.challenge")), 200

        return jsonify({"error": "Invalid token"}), 403

    @staticmethod
    def webhook():
        body = request.json
        print(f"Payload recebido no webhook: {body}")

        if body.get("object") == "whatsapp_business_account":
            changes = body.get("entry", [{}])[0].get("changes", [{}])[0].get("value", {})

            if "messages" in changes and len(changes["messages"]) > 0:
                message = changes["messages"][0]
                from_ = message.get("from")
                text = message.get("text", {}).get("body")
                message_id = message.get("id")

                WhatsAppController.process_message(from_, text, message_id)
                print(f"Novo contato recebido de {from_}: {text}")

        return jsonify({"status": "EVENT_RECEIVED"}), 200

    @staticmethod
    def process_message(phone: str, message: str, message_id: str):
        print(f"Processando mensagem: phone={phone}, message={message}, message_id={message_id}")
        """
        Processa uma mensagem recebida do WhatsApp Business
        """
        try:
            db = next(get_db())

            # Obter o último template e registar o log se necessário
            last_template, template_value = get_last_template(db, phone, message, message_id)

            # Dentro do método process_message:
            if template_value == 0:
                handle_template_0(db, phone, message, message_id)

            # 5. Nesse caso, quando perguntamos se é B2B ou B2C
            elif template_value == 99:
              handle_template_99(db, phone, message, message_id)


            elif template_value == 1:
              handle_template_1(db, phone, message, message_id)


            elif template_value == 2:
              handle_template_2(db, phone, message, message_id, last_template)

            elif template_value == 3:
              handle_template_3(db, phone, message, message_id, last_template)

            elif template_value == 6:
              handle_template_6(db, phone, message, message_id, last_template)
                  
              
            elif template_value == 4:
              # Aqui o usuário já recebeu a lista de produtos e as opções (1) Voltar ao menu principal e (2) Encerrar atendimento.
              user_key = last_template.user_sender
              user = db.query(User).filter_by(key=user_key).first()
              user_name = user.full_name if user else ''

              if message == "1":
                  # Voltar ao menu principal
                  # Reenviar o template_inicial_classificado com o nome do usuário para o menu de opções
                  reply_single_message_template(
                      phone, 'template_inicial_classificado', user_name, 'bot'
                  )
                  # Agora template_value = 2 novamente, voltamos ao menu principal
                  register_log(db, user_key, phone, 'template_inicial_classificado', message_id, 2)

              elif message == "2":
                  # Encerrar atendimento
                  reply_single_message_template(
                      phone, 'template_base', 'Atendimento encerrado. Obrigado!', 'bot'
                  )
                  # Define um novo estado, por exemplo template_value = 5, indicando que o atendimento foi encerrado
                  register_log(db, user_key, phone, 'template_base', message_id, 5)


            elif template_value == 5:
              # O atendimento já foi encerrado anteriormente.
              # Caso o usuário envie qualquer mensagem agora, apenas informe que o atendimento já foi concluído.
              user_key = last_template.user_sender
              user = db.query(User).filter_by(key=user_key).first()
              user_name = user.full_name if user else ''

              reply_single_message(
                  phone, 'template_base',
                  'O atendimento já foi encerrado. Caso necessite de algo mais, por favor inicie uma nova conversa. 😊',
                  'bot'
              )
              # Mantemos o template_value = 5 para indicar que não há mais fluxo.
              register_log(db, user_key, phone, 'template_base', message_id, 5)
            
            elif template_value == 7:
              user_key = last_template.user_sender
              user = db.query(User).filter_by(key=user_key).first()
              user_name = user.full_name if user else ''  
              
              user_choice = message.strip().upper()

              if user_choice == "S":
                reply_text_message(
                    phone,
                    "Pedido encaminhado para nossa loja, agradecemos o pedido e traremos atualizações nos próximos dias.",
                    [],
                    user_key
                )
                register_log(db, user_key, phone, "Pedido confirmado", message_id, 8)
              
              elif user_choice == "N":
                reply_text_message(
                      phone,
                      TEMPLATES["template_opcoes_modificacao"],
                      [],
                      user_key
                )
                register_log(db, user_key, phone, "Pedido para modificação", message_id, 9)
              
              else:
                  # Caso o usuário envie algo diferente de S ou N
                  reply_text_message(
                      phone,
                      "Por favor, responda com S (Sim) para confirmar ou N (Não) para modificar o pedido.",
                      [],
                      user_key
                  )
                  register_log(db, user_key, phone, "Resposta inválida no template 7", message_id, 7)
                  
            elif template_value == 9:
              if message == "1":
                user_key = last_template.user_sender if last_template and last_template.user_sender else 'bot'
                # Usuário escolheu adicionar novos itens
                reply_text_message(
                    phone,
                    'Continuando seu pedido... Por favor, envie mais itens que deseja adicionar.',
                    [],
                    user_key
                )
                register_log(
                    db, user_key, phone, 'template_base', message_id, 3 
                )
              elif message == "2":
                # Usuário escolheu remover itens do pedido
                all_user_messages = db.query(WhatsAppLog) \
                    .filter_by(phone=phone) \
                    .filter(WhatsAppLog.user_sender == 'bot') \
                    .filter(WhatsAppLog.template == 0) \
                    .order_by(WhatsAppLog.id.asc()) \
                    .all()

                # Filtra mensagens que não começam com "Por exemplo" e contêm "por favor"
                filtered_messages = [
                    log_entry.message for log_entry in all_user_messages
                    if not log_entry.message.startswith("Por exemplo") and "por favor" in log_entry.message.lower()
                ]

                # Concatena todas as mensagens em uma única string
                user_messages_text = "\n".join(filtered_messages)

                # Analisa os itens usando a função parse_order_items
                order_data = parse_order_items(user_messages_text)
                items_list = order_data.get("items", [])

                # Formata os itens para exibição
                if items_list:
                    formatted_items = [f"{item.get('name', '')}: {item.get('quantity', '')} {item.get('unit', '')}" for item in items_list]
                    items_str = "\n".join(formatted_items)
                else:
                    items_str = "Nenhum item encontrado."

                # Envia a mensagem com os itens para o usuário
                reply_text_message(
                    phone,
                    f"Você escolheu remover itens. Aqui estão os pedidos:\n\n{items_str}\n\nQuais itens você deseja remover?",
                    [],
                    'bot'
                )
                register_log(
                    db, user_key, phone, 'template_remover_itens', message_id, 10
                )
              
              elif message == "3":
                  # Usuário escolheu modificar itens do pedido
                  reply_text_message(
                      phone,
                      "Por favor, informe qual item você deseja modificar e o novo detalhe (quantidade ou unidade).\n\nPor exemplo:\n'Maçã: 5 kg' para modificar a quantidade de maçã para 5 kg.",
                      [],
                      'bot'
                  )
                  register_log(
                      db, user_key, phone, 'template_modificar_itens', message_id, 11 
                  )

              else:
                  # Resposta inválida
                  reply_text_message(
                      phone,
                      "Por favor, escolha uma opção válida:\n1️⃣ Adicionar\n2️⃣ Remover\n3️⃣ Modificar",
                      [],
                      user_key
                  )
                  register_log(
                      db, user_key, phone, 'template_opcoes_modificacao', message_id, 9
                  )
              
            else:
                print(f"Template desconhecido: {template_value}")
                

        
        except Exception as e:
            print(f"Erro ao processar mensagem: {e}")

    @staticmethod
    def get_user_data(phone: str) -> str:
        """
        Recupera a chave do usuário pelo número de telefone
        """
        try:
            db = next(get_db())
            user = db.query(User).filter_by(phone=phone).first()
            return user.key if user else ""
        except Exception as e:
            print(f"Erro ao recuperar dados do usuário: {e}")
            return ""