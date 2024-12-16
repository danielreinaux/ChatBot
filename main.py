from flask import Flask
from controllers.whatsapp_controller import WhatsAppController

app = Flask(__name__)

# Rota para verificar o webhook
@app.route('/api/register_webhook', methods=['GET'])
def register_webhook():
    return WhatsAppController.register_webhook()

# Rota principal para receber mensagens do webhook
@app.route('/api', methods=['POST'])
def webhook():
    return WhatsAppController.webhook()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
