import os
import requests
from flask import request, jsonify
from models.whatsapp_log import WhatsAppLog
from sqlalchemy.orm import Session
from database.session import get_db
from models.user import User
import uuid
from utils.openai import process_response, parse_order_items
from utils.get_produtos import get_products_message


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

            # 1. Recuperar o último log da conversa do usuário
            last_template = db.query(WhatsAppLog).filter_by(phone=phone).order_by(WhatsAppLog.id.desc()).first()

            # 2. Determinar o valor do template
            template_value = last_template.template if last_template else 0

            # 3. Registrar um novo log caso não exista um registro anterior
            if not last_template:
                WhatsAppController.register_log(db, '', phone, message, message_id, template_value)

            # 4. Lógica de processamento baseada no template
            if template_value == 0:
                WhatsAppController.reply_single_message(phone, 'template_primeiro_contato', message, 'bot')
                WhatsAppController.register_log(db, '', phone, 'template_base', message_id, 99)

            # 5. Nesse caso, quando perguntamos se é B2B ou B2C
            elif template_value == 99:
              # Definir as opções esperadas (1 e 2 neste caso)
              expected_options = ['1', '2']

              # Processar a mensagem do usuário usando a função flexível
              interpreted_message = process_response(message, expected_options)

              if interpreted_message == "1":
                  # Sendo esse o caso, é um cliente comum
                  WhatsAppController.reply_single_message_template(
                      phone, 'template_base', 'Para continuarmos, por favor informe seu nome.', 'bot'
                  )
                  WhatsAppController.register_log(db, '', phone, 'template_base', message_id, 1)
              elif interpreted_message == "2":
                  WhatsAppController.reply_single_message_template(
                      phone, 'template_base', 'Em breve nosso consultor entrará em contato.', 'bot'
                  )
                  WhatsAppController.register_log(db, '', phone, 'template_base', message_id, 98)
              else:
                  WhatsAppController.reply_single_message(
                      phone, 'template_primeiro_contato', message, 'bot'
                  )
                  WhatsAppController.register_log(db, '', phone, 'template_base', message_id, 99)


            elif template_value == 1:
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
              WhatsAppController.reply_single_message_template(
                  phone, 'template_inicial_classificado', message, 'bot'
              )
              WhatsAppController.register_log(db, user_key, phone, 'template_inicial_classificado', message_id, 2)


            elif template_value == 2:
                user = db.query(User).filter_by(key=last_template.user_sender).first()
                user_name = user.full_name if user else ''
                
                if message == "1":
                  # Usuário quer começar o pedido
                  WhatsAppController.reply_single_message_template(
                      phone,
                      'template_inicial_compra_classificado',  # O template que pede os itens ao usuário
                      user_name,  # Passamos o nome do usuário aqui no parâmetro para o template
                      last_template.user_sender
                  )
                
                  WhatsAppController.register_log(
                      db, last_template.user_sender, phone,'template_inicial_compra_classificado',message_id,3
                    )

                elif message == "2":
                  # Enviar a lista de produtos com as opções 1 e 2
                  products_message = get_products_message(db)  # Gera a mensagem com a lista de produtos
                  
                  WhatsAppController.reply_single_message_template(
                      phone, 'template_base', products_message, last_template.user_sender
                  )
                  WhatsAppController.register_log(
                      db, last_template.user_sender, phone, 'template_base', message_id, 4
                  )
                  
                    
                else:
                    # Para os outros números, envie uma mensagem padrão ou nenhuma mensagem
                    WhatsAppController.reply_single_message(
                        phone, 'template_base', 'Por favor, selecione uma opção válida.', 'bot'
                    )
                    WhatsAppController.register_log(
                        db, last_template.user_sender, phone, 'template_base', message_id, 99
                    )

            elif template_value == 3:
                # Estado 3: O usuário já recebeu o template_inicial_compra_classificado e enviou itens.
                user = db.query(User).filter_by(key=last_template.user_sender).first()
                user_name = user.full_name if user else ''
                
                order_data = parse_order_items(message)
                
                items_list = order_data.get("items", [])
                
                if items_list:
                  # Formatar a lista de itens em string
                  # Por exemplo: "Maçã: 2kg, Banana: 1 dúzia, Cenoura: 3kg"
                  formatted_items = []
                  for item in items_list:
                      name = item.get("name", "")
                      quantity = item.get("quantity", "")
                      unit = item.get("unit", "")
                      formatted_items.append(f"{name}: {quantity}{unit}")

                  items_str = ", ".join(formatted_items)
                
                # Enviar o template_processo_compra
                # {{1}} = Nome do usuário
                # {{2}} = itens formatados
                WhatsAppController.reply_single_message_template(
                    phone,
                    'template_processo_compra',
                    [user_name, items_str], 
                    last_template.user_sender
                )
                
                # Registrar log e atualizar o estado. Por ex, agora template_value = 6 (após exibir o resumo)
                WhatsAppController.register_log(
                    db, last_template.user_sender, phone, 'template_processo_compra', message_id, 6
                )
                
            elif template_value == 7:
                pass  # Implementar lógica para template 7
              
            elif template_value == 4:
              # Aqui o usuário já recebeu a lista de produtos e as opções (1) Voltar ao menu principal e (2) Encerrar atendimento.
              user_key = last_template.user_sender
              user = db.query(User).filter_by(key=user_key).first()
              user_name = user.full_name if user else ''

              if message == "1":
                  # Voltar ao menu principal
                  # Reenviar o template_inicial_classificado com o nome do usuário para o menu de opções
                  WhatsAppController.reply_single_message_template(
                      phone, 'template_inicial_classificado', user_name, 'bot'
                  )
                  # Agora template_value = 2 novamente, voltamos ao menu principal
                  WhatsAppController.register_log(db, user_key, phone, 'template_inicial_classificado', message_id, 2)

              elif message == "2":
                  # Encerrar atendimento
                  WhatsAppController.reply_single_message_template(
                      phone, 'template_base', 'Atendimento encerrado. Obrigado!', 'bot'
                  )
                  # Define um novo estado, por exemplo template_value = 5, indicando que o atendimento foi encerrado
                  WhatsAppController.register_log(db, user_key, phone, 'template_base', message_id, 5)


            elif template_value == 5:
              # O atendimento já foi encerrado anteriormente.
              # Caso o usuário envie qualquer mensagem agora, apenas informe que o atendimento já foi concluído.
              user_key = last_template.user_sender
              user = db.query(User).filter_by(key=user_key).first()
              user_name = user.full_name if user else ''

              WhatsAppController.reply_single_message(
                  phone, 'template_base',
                  'O atendimento já foi encerrado. Caso necessite de algo mais, por favor inicie uma nova conversa. 😊',
                  'bot'
              )
              # Mantemos o template_value = 5 para indicar que não há mais fluxo.
              WhatsAppController.register_log(db, user_key, phone, 'template_base', message_id, 5)
                
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

    @staticmethod
    def reply_single_message(to: str, template_name: str, params: str, user_sender: str):
        """
        Envia uma mensagem simples para o destinatário
        """
        try:
            # Monta o payload para enviar a mensagem
            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": "pt_BR"}
                }
            }
            # Configura os headers e a URL do WhatsApp Business API
            headers = {
                "Authorization": f"Bearer {os.getenv('WHATSAPP_BUSINESS_TOKEN')}",
                "Content-Type": "application/json"
            }
            url = os.getenv("WHATSAPP_BUSINESS_URL")
            
            # Faz a requisição para enviar a mensagem
            response = requests.post(url, json=payload, headers=headers)
            response_data = response.json()

            print(f"Mensagem enviada: {response_data}")

            # Salva o log no banco de dados
            db = next(get_db())
            new_log = WhatsAppLog(
                user_sender=user_sender,
                phone=to,
                message=params
            )
            db.add(new_log)
            db.commit()
        except Exception as e:
            print(f"Erro ao enviar mensagem: {e}")

    @staticmethod
    def reply_single_message_template(to: str, template_name: str, params, user_sender: str):
        """
        Envia uma mensagem com template e parâmetros personalizados.
        'params' pode ser uma string única ou uma lista de strings.
        Cada string na lista corresponde a um parâmetro {{1}}, {{2}}, etc.
        """
        try:
            # Se 'params' for string, transforma em lista para ficar padronizado
            if isinstance(params, str):
                params = [params]

            # Cria a lista de parâmetros no formato esperado
            body_params = []
            for p in params:
                # Garante que 'p' é uma string
                p = str(p)
                body_params.append({"type": "text", "text": p})

            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": "pt_BR"},
                    "components": [
                        {
                            "type": "body",
                            "parameters": body_params
                        }
                    ]
                }
            }

            # Configura os headers e a URL do WhatsApp Business API
            headers = {
                "Authorization": f"Bearer {os.getenv('WHATSAPP_BUSINESS_TOKEN')}",
                "Content-Type": "application/json"
            }
            url = os.getenv("WHATSAPP_BUSINESS_URL")

            # Faz a requisição para enviar a mensagem
            response = requests.post(url, json=payload, headers=headers)
            response_data = response.json()

            print(f"Mensagem enviada: {response_data}")

            # Salva o log no banco de dados
            db = next(get_db())
            new_log = WhatsAppLog(
                user_sender=user_sender,
                phone=to,
                message=" | ".join(params)  # Armazena todos os parâmetros separados por |
            )
            db.add(new_log)
            db.commit()
        except Exception as e:
            print(f"Erro ao enviar mensagem com template: {e}")


    @staticmethod
    def register_log(db: Session, user_sender: str, phone: str, message: str, message_id: str, template: int):
        try:
            new_log = WhatsAppLog(
                user_sender=user_sender,
                phone=phone,
                message=message,
                message_id=message_id,
                template=template
            )
            db.add(new_log)
            db.commit()
        except Exception as e:
            print(f"Erro ao registrar log: {e}")
