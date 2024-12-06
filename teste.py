from flask import Flask, request, jsonify
from controllers.whatsapp_controller import WhatsAppController

# Inicializa o servidor Flask
app = Flask(__name__)

# Rota para simular o webhook
@app.route('/webhook', methods=['POST'])
def webhook():
    # Recebe os dados enviados no corpo da requisição (JSON)
    data = request.json
    print("Evento recebido:", data)  # Exibe os dados no console (logs)
    # Simula o processamento dos dados recebidos
    if "messages" in data.get("entry", [])[0].get("changes", [])[0].get("value", {}):
        WhatsAppController.webhook()  # Chama o controller para processar os dados
        return jsonify({"status": "Mensagem recebida e processada com sucesso"})
    else:
        return jsonify({"status": "Nenhuma mensagem encontrada"}), 400

# Inicia o servidor na porta 5000
if __name__ == '__main__':
    app.run(port=5000)
