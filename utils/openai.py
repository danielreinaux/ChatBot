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
    Prioriza itens modificados caso haja duplicidade.
    """
    messages = [
        {
            "role": "system",
            "content": (
                "Você é um assistente que extrai itens de uma lista de compras fornecida pelo usuário. "
                "Sua tarefa é identificar os itens, corrigir erros de digitação comuns e fornecer as quantidades e unidades correspondentes.\n\n"
                
                "Instruções detalhadas:\n"
                "1. Identifique cada item, sua quantidade e unidade a partir do texto fornecido.\n"
                "2. Se a mensagem contiver a frase 'Os seguintes itens foram modificados:', extraia os itens listados após essa frase.\n"
                "3. Se houver itens duplicados, o item modificado deve substituir a versão anterior. Priorize sempre o item modificado em caso de conflito.\n"
                "4. Corrija erros de digitação comuns nos nomes dos itens (por exemplo, 'maça' para 'Maçã', 'cebol' para 'Cebola').\n"
                "5. Retorne um JSON no formato: { \"items\": [ {\"name\": <string>, \"quantity\": <number>, \"unit\": <string>} ] }.\n"
                "6. Sempre que possível, padronize a unidade para algo curto e simples (por exemplo: 'kg', 'un', 'duzia'). "
                "   Se a unidade não for clara, tente inferir. Caso não seja possível, use 'unidades'.\n"
                "7. O nome do item deve começar com letra maiúscula e o restante em minúsculas (ex: 'Maçã', 'Banana', 'Alface').\n"
                "8. A quantidade deve ser um número inteiro sempre que possível. Converta expressões como 'meia dúzia' para 6.\n"
                "9. Se não encontrar nenhum item, retorne {\"items\": []}.\n\n"
                
                "Exemplo de cenário com duplicatas e itens modificados:\n"
                "- Lista original: 'Maçã: 2 kg'\n"
                "- Modificação: 'Os seguintes itens foram modificados:\n\nMaçã: 3 kg'\n"
                "- Saída esperada: { \"items\": [ {\"name\": \"Maçã\", \"quantity\": 3, \"unit\": \"kg\"} ] }\n\n"
                
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
    """
    Analisa todas as mensagens do usuário e retorna os itens pedidos,
    excluindo aqueles que foram removidos.

    Args:
        user_messages_text (str): Texto consolidado das mensagens do usuário.

    Returns:
        list: Lista de itens restantes no pedido.
    """
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


def parse_items_to_remove(user_input: str, items_list: list) -> list:
    """
    Usa a API da OpenAI para identificar os itens que o usuário deseja remover da lista.

    Args:
        user_input (str): Mensagem do usuário especificando os itens a remover.
        items_list (list): Lista atual de itens.

    Returns:
        list: Lista de itens a serem removidos.
    """
    item_names = [item.get("name", "") for item in items_list]
    item_names_str = ", ".join(item_names)

    prompt = (
        f"O usuário forneceu a seguinte lista de itens: {item_names_str}.\n"
        f"Com base na mensagem: '{user_input}', identifique quais itens da lista o usuário deseja remover.\n"
        "Responda com os nomes exatos dos itens que devem ser removidos em formato JSON, por exemplo:\n"
        "{ \"items_to_remove\": [\"Maçã\", \"Banana\"] }\n"
        "Se não encontrar nenhum item para remover, retorne {\"items_to_remove\": []}."
    )

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Você é um assistente que identifica itens a serem removidos de uma lista."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0
        )

        content = response.choices[0].message['content'].strip()
        data = json.loads(content)
        items_to_remove_names = data.get("items_to_remove", [])

        # Filtrar os itens originais que correspondem aos nomes identificados
        items_to_remove = [item for item in items_list if item.get("name", "") in items_to_remove_names]

        return items_to_remove

    except Exception as e:
        print(f"Erro ao chamar OpenAI para identificar itens a remover: {e}")
        return []
      

def parse_items_to_modify(message, items_list):
    """
    Usa a OpenAI para identificar os itens a serem modificados e seus novos detalhes com base na mensagem do usuário.

    Args:
        message (str): Mensagem do usuário.
        items_list (list): Lista atual de itens no pedido.

    Returns:
        list: Lista de itens modificados no formato [{"name": "item", "quantity": X, "unit": "Y"}].
    """
    item_names = [f"{item.get('name', '')}: {item.get('quantity', '')} {item.get('unit', '')}" for item in items_list]
    item_names_str = "\n".join(item_names)

    prompt = (
        "O usuário enviou uma mensagem solicitando a modificação de itens no pedido. "
        "A lista atual de itens é a seguinte:\n\n"
        f"{item_names_str}\n\n"
        "Identifique os itens que devem ser modificados na mensagem do usuário e forneça os novos detalhes. "
        "Retorne apenas os itens modificados no formato JSON, por exemplo:\n"
        "{ \"items\": [ {\"name\": \"Maçã\", \"quantity\": 5, \"unit\": \"kg\"} ] }\n\n"
        "Se não conseguir identificar modificações, retorne:\n"
        "{ \"items\": [] }\n\n"
        f"Mensagem do usuário:\n{message}"
    )

    try:
        # Chamar a API da OpenAI
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Você é um assistente que modifica itens de pedidos com base em instruções do usuário."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0
        )

        content = response.choices[0].message['content'].strip()
        data = json.loads(content)

        return data.get("items", [])

    except Exception as e:
        print(f"Erro ao chamar OpenAI: {e}")
        return []
