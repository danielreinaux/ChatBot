import os
import openai
import json

# Carrega as variáveis de ambiente do arquivo .env
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


def parse_order_items(user_input: str) -> dict:
    """
    Usa a API da OpenAI para analisar a lista de itens enviada pelo usuário
    e retornar uma estrutura JSON com nome, quantidade e unidade de cada item.
    """
    messages = [
    {
        "role": "system",
        "content": (
            "Você é um assistente que extrai itens de uma lista de compras fornecida pelo usuário. "
            "Sua tarefa é identificar os itens, corrigir erros de digitação comuns e fornecer as quantidades e unidades correspondentes.\n\n"
            "Instruções detalhadas:\n"
            "1. Identifique cada item, sua quantidade e unidade a partir do texto fornecido.\n"
            "2. Corrija erros de digitação comuns nos nomes dos itens (por exemplo, 'maça' para 'Maçã', 'cebol' para 'Cebola').\n"
            "3. Retorne um JSON no formato: { \"items\": [ {\"name\": <string>, \"quantity\": <number>, \"unit\": <string>} ] }.\n"
            "4. Sempre que possível, padronize a unidade para algo curto e simples (por exemplo: 'kg', 'un', 'duzia'). "
            "   Se a unidade não for clara, tente inferir. Caso não seja possível, use 'unidades'.\n"
            "5. O nome do item deve começar com letra maiúscula e o restante em minúsculas (ex: 'Maçã', 'Banana', 'Alface').\n"
            "6. A quantidade deve ser um número inteiro sempre que possível. Converta expressões como 'meia dúzia' para 6.\n"
            "7. Se não encontrar nenhum item, retorne {\"items\": []}.\n\n"
            "Exemplos de correções automáticas:\n"
            "- 'maça' deve ser corrigido para 'Maçã'\n"
            "- 'cebol' deve ser corrigido para 'Cebola'\n"
            "- 'tomate' já está correto\n"
            "- 'laranja' já está correto\n\n"
            "Não adicione comentários, explicações ou texto extra fora do JSON. Retorne apenas o JSON final."
        )
    },
    {
        "role": "user",
        "content": f"Texto do usuário: '{user_input}'"
        }
    ]


    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=messages,
            max_tokens=300,
            temperature=0
        )

        content = response.choices[0].message['content'].strip()
        data = json.loads(content)

        if "items" not in data:
            data = {"items": []}
        return data

    except Exception as e:
        print(f"Erro ao chamar OpenAI: {e}")
        return {"items": []}


def parse_all_items(user_messages_text: str) -> list:
    # Prompt explicando ao GPT o que fazer:
    prompt = (
        "O usuário enviou várias mensagens contendo possivelmente itens e quantidades. "
        "Você deve analisar todas as mensagens abaixo e retornar apenas os itens pedidos, "
        "no formato JSON, por exemplo:\n"
        "{ \"items\": [ {\"name\": \"Maçã\", \"quantity\": 2, \"unit\": \"un\"}, ... ]}\n\n"
        "Se não encontrar itens, retorne {\"items\": []}.\n\n"
        "Mensagens do usuário:\n"
        f"{user_messages_text}"
    )

    # Aqui você chama a função da OpenAI (ChatCompletion)
    # Certifique-se de ter sua chave da OpenAI e tudo configurado.
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Você é um assistente que extrai itens de pedido."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.0
    )

    content = response.choices[0].message['content'].strip()
    import json
    try:
        data = json.loads(content)
    except:
        data = {"items": []}
    return data.get("items", [])
