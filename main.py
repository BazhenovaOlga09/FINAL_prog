import telebot
from config import LOGS
from creds import get_bot_token
from admin import ADMIN_USERS
import db
import logging
from gpt import ask_gpt
from keyboard import create_keyboard
from validators import check_number_of_users, is_gpt_token_limit, is_stt_block_limit, is_tts_symbol_limit
from speechkit import speech_to_text, text_to_speech

logging.basicConfig(filename=LOGS, level=logging.ERROR, format="%(asctime)s FILE: %(filename)s IN: %(funcName)s MESSAGE: %(message)s", filemode="w")
bot = telebot.TeleBot(get_bot_token())


@bot.message_handler(commands=['start'])
def start_command(message):
    user_name = message.from_user.first_name
    bot.send_message(message.chat.id, f"Приветсвую тебя, {user_name}! Скорее вводи голосовое или текстовое сообщение и я тебе отвечу!))) Так же этот бот умеет расшифровывать сообщения и наоборт переводить их в голос! Это можно сделать по командам /stt и /tts", reply_markup=create_keyboard(["/stt", "/tts"]))


@bot.message_handler(commands=['help'])
def help(message):
    bot.send_message(message.from_user.id, "Чтобы приступить к общению, отправь мне голосовое сообщение или текст")


@bot.message_handler(commands=['debug'])
def debug(message):
    user_id = message.from_user.id
    if user_id in ADMIN_USERS:
        with open("logs.txt", "rb") as f:
            bot.send_document(message.chat.id, f)
    else:
        bot.send_message(user_id, "Извини, но этот файл я могу отправить только админу(((")
        return


@bot.message_handler(commands=['tts'])
def tts_handler(message):
    user_id = message.from_user.id
    bot.send_message(user_id, 'Отправь следующим сообщением текст, чтобы я его озвучил!')
    bot.register_next_step_handler(message, process_tts)

def process_tts(message):
    user_id = message.from_user.id
    text = message.text

    if message.content_type != 'text':
        bot.send_message(user_id, 'Отправь текстовое сообщение')
        bot.register_next_step_handler(message, process_tts)
        return

    tts_symbol = is_tts_symbol_limit(message, text)
    if not tts_symbol:
        bot.send_message(user_id, tts_symbol)
        return

    status_tts, tts_text = text_to_speech(text)

    full_user_message = [tts_text, 'user', 0, 0, tts_symbol]
    db.add_message(user_id=user_id, full_message=full_user_message)

    if status_tts:
        bot.send_voice(user_id, tts_text)
        bot.send_message(user_id, "Вводи команду /tts если хочешь перевести еще одно сообщение, а если нет то просто отправь свой вопрос и gpt тебе ответит", reply_markup=create_keyboard(["/stt", "/tts"]))
    else:
        bot.send_message(user_id, tts_text)


@bot.message_handler(commands=['stt'])
def stt_handler(message):
    user_id = message.from_user.id
    bot.send_message(user_id, 'Отправь голосовое сообщение, чтобы я его распознал!')
    bot.register_next_step_handler(message, prossec_stt)

def prossec_stt(message):
    user_id = message.from_user.id

    file_id = message.voice.file_id
    file_info = bot.get_file(file_id)
    file = bot.download_file(file_info.file_path)

    if not message.voice:
        bot.send_message(user_id, "Отправь голосовое сообщение")
        bot.register_next_step_handler(message, prossec_stt)
        return

    stt_blocks = is_stt_block_limit(message, message.voice.duration)
    if not stt_blocks:
        bot.send_message(user_id, stt_blocks)
        return


    status_stt, stt_text = speech_to_text(file)
    full_user_message = [stt_text, 'user', 0, 0, stt_blocks]
    db.add_message(user_id=user_id, full_message=full_user_message)
    if status_stt:

        bot.send_message(user_id, stt_text, reply_to_message_id=message.id)
        bot.send_message(user_id, "Если хочешь ввести еще одно голосове смело жми /stt!!! А если нет, то вводи простое сообщение чтобы gpt смогу ответить на него)", reply_markup=create_keyboard(["/stt", "/tts"]))


@bot.message_handler(content_types=['voice'])
def voice_message(message):
    try:
        user_id = message.from_user.id

        file_id = message.voice.file_id
        file_info = bot.get_file(file_id)
        file = bot.download_file(file_info.file_path)

        status_check_users = check_number_of_users(user_id)
        if not status_check_users:
            bot.send_message(user_id, "Извини но количество пользователей превысило лимит((")
            return

        stt_blocks = is_stt_block_limit(message, message.voice.duration)
        if not stt_blocks:
            bot.send_message(user_id, stt_blocks)
            return

        status_stt, stt_text = speech_to_text(file)
        if not status_stt:
            bot.send_message(user_id, stt_text)
            return

        full_user_message = [stt_text, 'user', 0, 0, stt_blocks]
        db.add_message(user_id=user_id, full_message=full_user_message)

        last_messages, total_spent_tokens = db.select_n_last_messages(user_id)

        total_gpt_tokens, error_message = is_gpt_token_limit(last_messages, total_spent_tokens)
        if error_message:
            bot.send_message(user_id, "К сожалению ты потратил все токены для обращения к GPT, попробуй команды /stt или /tts!", reply_markup=create_keyboard(["/tts", "/stt"]))
            bot.send_message(user_id, error_message)
            return

        status_gpt, answer_gpt, tokens_in_answer = ask_gpt(last_messages)
        if not status_gpt:
            bot.send_message(user_id, answer_gpt)
            return

        total_gpt_tokens += tokens_in_answer

        tts_symbols = is_tts_symbol_limit(message, answer_gpt)
        if not tts_symbols:
            bot.send_message(user_id, tts_symbols)
            return


        full_gpt_message = [answer_gpt, 'assistant', total_gpt_tokens, tts_symbols, 0]
        db.add_message(user_id=user_id, full_message=full_gpt_message)


        status_tts, tts_text = text_to_speech(answer_gpt)
        if status_tts:
            bot.send_voice(user_id, tts_text)
            full_user_message = [tts_text, 'user', 0, 0, tts_symbols]
            db.add_message(user_id=user_id, full_message=full_user_message)
            bot.send_message(user_id, "Если еще хочешь постпрашивать gpt, отправляй твое сообщение")

        else:
            bot.send_message(user_id, tts_text)


    except Exception as e:
        logging.error(e)
        user_id = message.from_user.id
        bot.send_message(user_id, "Не получилось ответить. Попробуй написать другое сообщение")


@bot.message_handler(content_types=['text'])
def text_message(message):
    try:
        user_id = message.from_user.id

        status_check_users, error_message = check_number_of_users(user_id)
        if not status_check_users:
            bot.send_message(user_id, "Извини но количество пользователей превысило лимит((")
            return

        full_user_message = [message.text, 'user', 0, 0, 0]
        db.add_message(user_id=user_id, full_message=full_user_message)

        last_messages, total_spent_tokens = db.select_n_last_messages(user_id,4)
        last_messages += {"text": message.text, "role": "user"}
        total_gpt_tokens, error_message = is_gpt_token_limit(last_messages, total_spent_tokens)
        if error_message:
            bot.send_message(user_id, "К сожалению ты потратил все токены для обращения к GPT, попробуй команды /stt или /tts!", reply_markup=create_keyboard(["/tts", "/stt"]))
            bot.send_message(user_id, error_message)
            return

        status_gpt, answer_gpt, tokens_in_answer = ask_gpt(last_messages)

        if not status_gpt:

            bot.send_message(user_id, answer_gpt)
            return
        total_gpt_tokens += tokens_in_answer

        full_gpt_message = [answer_gpt, 'assistant', total_gpt_tokens, 0, 0]
        db.add_message(user_id=user_id, full_message=full_gpt_message)

        bot.send_message(user_id, answer_gpt, reply_to_message_id=message.id)
        bot.send_message(user_id, "Если еще хочешь постпрашивать gpt, отправляй твое сообщение")

    except Exception as e:
        logging.error(e)
        bot.send_message(message.from_user.id, "Не получилось ответить. Попробуй написать другое сообщение")


@bot.message_handler()
def user_message(message):
    user_id = message.from_user.id
    bot.send_message(user_id, "Извини, но пока что я научился понимать только аудио и текстовые сообщения(( Попробуй отправить их!")
    return

db.create_database()
bot.polling()
