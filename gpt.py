from config import MAX_GPT_TOKENS, SYSTEM_PROMPT
from creds import get_creds
import requests
import logging

iam_token, folder_id = get_creds()

def count_gpt_tokens(messages):
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/tokenizeCompletion"
    headers = {
        'Authorization': f'Bearer {iam_token}',
        'Content-Type': 'application/json'
    }
    data = {
        'modelUri': f"gpt://{folder_id}/yandexgpt-lite",
        "messages": messages
    }
    try:
        return len(requests.post(url=url, json=data, headers=headers).json()['tokens'])
    except Exception as e:
        logging.error(e)
        return 0

def ask_gpt(messages):
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        'Authorization': f'Bearer {iam_token}',
        'Content-Type': 'application/json'
    }
    data = {
        'modelUri': f"gpt://{folder_id}/yandexgpt-lite",
        "completionOptions": {
            "stream": False,
            "temperature": 0.3,
            "maxTokens": MAX_GPT_TOKENS
        },
        "messages": SYSTEM_PROMPT + messages
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        print(response.json)
        if response.status_code != 200:
            return False, f"Ошибка GPT. Статус-код: {response.status_code}", None

        answer = response.json()['result']['alternatives'][0]['message']['text']

        tokens_in_answer = count_gpt_tokens([{'role': 'assistant', 'text': answer}])
        return True, answer, tokens_in_answer
    except Exception as e:
        logging.error(e)
        return False, "Ошибка при обращении к GPT",  None
