import os
import requests
from models.whatsapp_log import WhatsAppLog
from sqlalchemy.orm import Session
from database.session import get_db

def reply_single_message(to: str, template_name: str, params: str, user_sender: str):
    """
    Envia uma mensagem simples para o destinatário.
    """
    try:
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": "pt_BR"}
            }
        }

        headers = {
            "Authorization": f"Bearer {os.getenv('WHATSAPP_BUSINESS_TOKEN')}",
            "Content-Type": "application/json"
        }

        url = os.getenv("WHATSAPP_BUSINESS_URL")

        response = requests.post(url, json=payload, headers=headers)
        response_data = response.json()
        print(f"Mensagem enviada: {response_data}")

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

def reply_single_message_template(to: str, template_name: str, params, user_sender: str):
    """
    Envia uma mensagem com template e parâmetros personalizados.
    """
    try:
        if isinstance(params, str):
            params = [params]

        body_params = [{"type": "text", "text": str(p)} for p in params]

        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": "pt_BR"},
                "components": [{"type": "body", "parameters": body_params}]
            }
        }

        headers = {
            "Authorization": f"Bearer {os.getenv('WHATSAPP_BUSINESS_TOKEN')}",
            "Content-Type": "application/json"
        }

        url = os.getenv("WHATSAPP_BUSINESS_URL")

        response = requests.post(url, json=payload, headers=headers)
        response_data = response.json()
        print(f"Mensagem enviada: {response_data}")

        db = next(get_db())
        new_log = WhatsAppLog(
            user_sender=user_sender,
            phone=to,
            message=" | ".join(params)
        )
        db.add(new_log)
        db.commit()
    except Exception as e:
        print(f"Erro ao enviar mensagem com template: {e}")

def register_log(db: Session, user_sender: str, phone: str, message: str, message_id: str, template: int):
    """
    Registra o log no banco de dados.
    """
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

def reply_text_message(to: str, text: str, params, user_sender: str):
    """
    Envia uma mensagem de texto simples para o destinatário.
    """
    try:
        if isinstance(params, str):
            params = [params]

        for i, param in enumerate(params):
            placeholder = f"{{{{{i + 1}}}}}"
            text = text.replace(placeholder, str(param))

        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": text}
        }

        headers = {
            "Authorization": f"Bearer {os.getenv('WHATSAPP_BUSINESS_TOKEN')}",
            "Content-Type": "application/json"
        }

        url = os.getenv("WHATSAPP_BUSINESS_URL")

        response = requests.post(url, json=payload, headers=headers)
        response_data = response.json()
        print(f"Mensagem enviada: {response_data}")

        db = next(get_db())
        new_log = WhatsAppLog(
            user_sender=user_sender,
            phone=to,
            message=text
        )
        db.add(new_log)
        db.commit()
    except Exception as e:
        print(f"Erro ao enviar mensagem de texto: {e}")

def get_last_template(db: Session, phone: str, message: str, message_id: str) -> int:
    """
    Recupera o último template da conversa do usuário e registra um novo log se não existir.

    Args:
        db (Session): Sessão do banco de dados.
        phone (str): Número de telefone do usuário.
        message (str): Mensagem recebida.
        message_id (str): ID da mensagem recebida.

    Returns:
        int: O valor do template associado ao último log ou 0 se não existir.
    """
    # Recuperar o último log da conversa do usuário
    last_template = db.query(WhatsAppLog).filter_by(phone=phone).order_by(WhatsAppLog.id.desc()).first()

    # Determinar o valor do template
    template_value = last_template.template if last_template else 0

    # Registrar um novo log caso não exista um registro anterior
    if not last_template:
        register_log(db, '', phone, message, message_id, template_value)

    return last_template, template_value