import db
from config import  MAX_USERS, MAX_USER_TTS_SYMBOLS, MAX_USER_STT_BLOCKS, MAX_GPT_TOKENS, MAX_USER_GPT_TOKENS, MAX_TTS_SYMBOLS
from creds import get_bot_token
from creds import get_creds
import requests
import sqlite3
import math
import telebot
from db import count_all_blocks, count_users
from gpt import count_gpt_tokens

bot = telebot.TeleBot(get_bot_token())
iam_token, folder_id = get_creds()


def count_tokens_in_dialog(messages: sqlite3.Row):
    headers = {
        'Authorization': f'Bearer {iam_token}',
        'Content-Type': 'application/json'
    }
    data = {
       "modelUri": f"gpt://{folder_id}/yandexgpt/latest",
       "maxTokens": MAX_GPT_TOKENS,
       "messages": []
    }


    for row in messages:
        role, content = row
        print(messages)
        data["messages"].append(
            {
                "role": role,
                "text": content
            }
        )
    resp = requests.post(
            "https://llm.api.cloud.yandex.net/foundationModels/v1/tokenizeCompletion",
            json=data,
            headers=headers
        ).json()
    print(resp)

    return len(
        resp["tokens"]
    )


def check_number_of_users(user_id):
    count = count_users(user_id)
    if count is None:
        return None, "Ошибка при работе с БД"
    if count > MAX_USERS:
        return None, "Превышено максимальное количество пользователей"
    return True, ""


def is_stt_block_limit(message, duration):
    user_id = message.from_user.id
    audio_blocks = math.ceil(duration / 15)

    all_blocks = count_all_blocks(user_id) + audio_blocks

    if duration >= 30:
        msg = "SpeechKit STT работает с голосовыми сообщениями меньше 30 секунд"
        bot.send_message(user_id, msg)
        return

    if all_blocks >= MAX_USER_STT_BLOCKS:
        msg = f"Превышен общий лимит SpeechKit STT {MAX_USER_STT_BLOCKS}. Использовано {all_blocks} блоков. Доступно: {MAX_USER_STT_BLOCKS - all_blocks}"
        bot.send_message(user_id, msg)
        return None
    return audio_blocks


def is_tts_symbol_limit(message, text):
    user_id = message.from_user.id
    text_symbols = len(text)
    all_symbols = db.count_all_limits(user_id, "tts_symbols") + text_symbols

    if all_symbols >= MAX_USER_TTS_SYMBOLS:
        msg = f"Превышен общий лимит SpeechKit TTS {MAX_USER_TTS_SYMBOLS}. Использовано: {all_symbols} символов. Доступно: {MAX_USER_TTS_SYMBOLS - all_symbols}"
        bot.send_message(user_id, msg)
        return None


    if text_symbols >= MAX_TTS_SYMBOLS:
        msg = f"Превышен лимит SpeechKit TTS на запрос {MAX_TTS_SYMBOLS}, в сообщении {text_symbols} символов"
        bot.send_message(user_id, msg)
        bot.send_message(user_id, 'Отправь  сообщение:')

        return None
    return len(text)

def is_gpt_token_limit(messages, total_spent_tokens):
    all_tokens = count_gpt_tokens(messages) + total_spent_tokens

    if all_tokens > MAX_USER_GPT_TOKENS:
        return None, f"Превышен общий лимит GPT-токенов {MAX_USER_GPT_TOKENS}"
    return all_tokens, ""