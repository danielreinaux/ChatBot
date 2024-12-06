import os
import openai
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

def process_response(user_input, expected_options):
    """
    Processa a resposta do usuário usando OpenAI para interpretar nuances e mapeá-la para uma opção esperada.
    
    Args:
        user_input (str): Entrada do usuário.
        expected_options (list): Lista de opções esperadas (ex: ['1', '2', '3']).
    
    Returns:
        str: A opção correspondente se for encontrada, ou 'None' se a entrada não for válida.
    """
    try:
        # Cria a mensagem no formato esperado pela API ChatCompletion
        messages = [
            {
                "role": "system",
                "content": (
                    "Você é um assistente que mapeia a entrada do usuário para uma das opções fornecidas. "
                    "Responda apenas com uma das opções fornecidas, sem explicações adicionais."
                )
            },
            {
                "role": "user",
                "content": (
                    f"O usuário disse: '{user_input}'. "
                    "Mapeie esta entrada para uma das seguintes opções exatamente como escrito: "
                    f"{', '.join(expected_options)}. "
                    "Se a entrada for inválida ou ambígua, responda apenas com 'None'."
                )
            }
        ]

        # Chamar a API ChatCompletion
        response = openai.ChatCompletion.create(
            model="gpt-4",  # Substitua por "gpt-4-turbo" se necessário
            messages=messages,
            max_tokens=10,
            temperature=0
        )

        # Extrair e normalizar a resposta gerada
        mapped_response = response.choices[0].message['content'].strip()

        # Verifica se a resposta está entre as opções válidas
        if mapped_response in expected_options:
            return mapped_response
        else:
            return None
    except Exception as e:
        print(f"Erro ao processar resposta: {e}")
        return None
