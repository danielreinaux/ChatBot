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
from utils.template_utils import handle_template_0, handle_template_99, handle_template_1, handle_template_2, handle_template_3, handle_template_6, handle_template_4, handle_template_5, handle_template_7, handle_template_9, handle_template_10, handle_template_11, handle_template_12, handle_template_13
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
              handle_template_4(db, phone, message, message_id, last_template)

            elif template_value == 5:
              handle_template_5(db, phone, message, message_id, last_template)
            
            elif template_value == 7:
              handle_template_7(db, phone, message, message_id, last_template)
                  
            elif template_value == 9:
              handle_template_9(db, phone, message, message_id, last_template)
              
            elif template_value == 10:
              handle_template_10(db, phone, message, message_id, last_template)
              
            elif template_value == 11:
              handle_template_11(db, phone, message, message_id, last_template)
              
            elif template_value == 12:
              handle_template_12(db, phone, message, message_id, last_template)
            
            elif template_value == 13:
              handle_template_13(db, phone, message, message_id, last_template)
              
            
                

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