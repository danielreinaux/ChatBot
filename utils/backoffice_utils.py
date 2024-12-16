import requests

def trigger_b2b_notification(phone):
    """
    Gera uma notificação via webhook para o painel do cliente B2B.

    Args:
        phone (str): Número de telefone do cliente.
    """
    webhook_url = "https://painel-cliente.com/webhook"  # URL do webhook do painel
    whatsapp_link = f"https://wa.me/{phone}?text=Olá,%20preciso%20de%20ajuda!"

    payload = {
        "type": "B2B_NOTIFICATION",
        "phone": phone,
        "message": "Novo cliente B2B identificado. Clique no link abaixo para entrar em contato via WhatsApp.",
        "whatsapp_link": whatsapp_link
    }

    headers = {
        "Content-Type": "application/json"
    }

    try:
        response = requests.post(webhook_url, json=payload, headers=headers)
        response.raise_for_status()
        print(f"Notificação B2B enviada com sucesso para {phone}")
    except requests.exceptions.RequestException as e:
        print(f"Erro ao enviar notificação B2B: {e}")