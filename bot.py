import telebot
from config import *
from database import *
from speechkit import text_to_speech, speech_to_text
import math
from yandex_gpt import *
from validators import *  # модуль для валидации
# подтягиваем константы из config файла
# подтягиваем функции из database файла
from database import *
create_database()
from creds.creds import get_bot_token  # модуль для получения bot_token

bot = telebot.TeleBot(get_bot_token())  # создаём объект бота

@bot.message_handler(commands=['debug'])
def debug(message):
    with open("logs.txt", "rb") as f:
        bot.send_document(message.chat.id, f)

@bot.message_handler(commands=['start'])
def handle_start(message):
    user_id = message.chat.id
    firstname = message.from_user.first_name
    bot.send_message(user_id, f"Приветствую, {firstname}!💞\n"
                              f"Это нейросеть которая которая будет отвечать на ваши запросы по тексту, а также по голосу!💙\n"
                              f"/help - помощь по боту и командам.💕\n")

@bot.message_handler(commands=['help'])
def handle_help(message):
    user_id = message.chat.id
    bot.send_message(user_id, "Мои команды:\n"
                              "/debug - отправляется файл с логами."
                              "Команды для проверки:\n"
                              "/tts - проверка, текста в голосовое сообщение.🟥\n"
                              "/stt - проверка, голосового сообщения в текст.🟥\n"
                              "Другие команды:\n"
                              "/about - о боте.💗\n"
                              "/n1 - мандарин.🧡\n"
                              "/n2 - банан.💛")

# about - о боте
@bot.message_handler(commands=['about'])
def about(message):
    user_id = message.chat.id
    bot.send_message(user_id, "Я нейросеть Android, могу отвечать на ваши запросы по тексту так и голосовыми сообщениями!💚\n"
                              "Мой создатель - @llonnne 💞"
                              "обратно, /help")

# n1 - мандарин
@bot.message_handler(commands=['n1'])
def n1(message):
    user_id = message.chat.id
    photo = open("frukt/mandarin.jpg", "rb")
    bot.send_photo(user_id, photo)
    bot.send_message(user_id, "обратно, /help")

# n2 - банан
@bot.message_handler(commands=['n2'])
def n2(message):
    user_id = message.chat.id
    photo = open("frukt/banana.jpg", "rb")
    bot.send_photo(user_id, photo)
    bot.send_message(user_id, "обратно, /help")


@bot.message_handler(commands=['tts'])
def tts_handler(message):
    user_id = message.from_user.id
    bot.send_message(user_id, 'Отправь следующим сообщеним текст, чтобы я его озвучил!')
    bot.register_next_step_handler(message, tts)


def tts(message):
    user_id = message.from_user.id
    text = message.text

    # Проверка, что сообщение действительно текстовое
    if message.content_type != 'text':
        bot.send_message(user_id, 'Отправь текстовое сообщение')
        return

        # Считаем символы в тексте и проверяем сумму потраченных символов
    text_symbol = is_tts_symbol_limit(message, text)
    if text_symbol is None:
        return

    # Записываем сообщение и кол-во символов в БД
    full_gpt_message = [message.text, 'user', 0, text_symbol, 0]
    add_message(user_id=user_id, full_message=full_gpt_message)

    # Получаем статус и содержимое ответа от SpeechKit
    status, content = text_to_speech(text)

    # Если статус True - отправляем голосовое сообщение, иначе - сообщение об ошибке
    if status:
        bot.send_voice(user_id, content)
    else:
        bot.send_message(user_id, content)


# Обрабатываем команду /stt
@bot.message_handler(commands=['stt'])
def stt_handler(message):
    user_id = message.from_user.id
    bot.send_message(user_id, 'Отправь голосовое сообщение, чтобы я его распознал!')
    bot.register_next_step_handler(message, stt)


# Переводим голосовое сообщение в текст после команды stt
def stt(message):
    user_id = message.from_user.id

    # Проверка, что сообщение действительно голосовое
    if not message.voice:
        return

    # Считаем аудиоблоки и проверяем сумму потраченных аудиоблоков
    stt_blocks = is_stt_block_limit(message, message.voice.duration)
    if not stt_blocks:
        return

    file_id = message.voice.file_id  # получаем id голосового сообщения
    file_info = bot.get_file(file_id)  # получаем информацию о голосовом сообщении
    file = bot.download_file(file_info.file_path)  # скачиваем голосовое сообщение

    # Получаем статус и содержимое ответа от SpeechKit
    status, text = speech_to_text(file)  # преобразовываем голосовое сообщение в текст

    # Если статус True - отправляем текст сообщения и сохраняем в БД, иначе - сообщение об ошибке
    if status:
        # Записываем сообщение и кол-во аудиоблоков в БД
        full_gpt_message = [text, 'user', 0, 0, stt_blocks]
        add_message(user_id=user_id, full_message=full_gpt_message)
        bot.send_message(user_id, text, reply_to_message_id=message.id)
    else:
        bot.send_message(user_id, text)


@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    user_id = message.chat.id
    # Проверка на максимальное количество пользователей
    status_check_users, error_message = check_number_of_users(user_id)
    if not status_check_users:
        bot.send_message(user_id, error_message)
        return

    # Проверка на доступность аудиоблоков
    stt_blocks, error_message = is_stt_block_limit(message, message.voice.duration)
    if not stt_blocks:
        bot.send_message(user_id, error_message)
        return

    # Обработка голосового сообщения
    file_id = message.voice.file_id
    file_info = bot.get_file(file_id)
    file = bot.download_file(file_info.file_path)
    status_stt, stt_text = speech_to_text(file)
    if not status_stt:
        bot.send_message(user_id, stt_text)
        return

    # Запись в БД
    add_message(user_id=user_id, full_message=[stt_text, 'user', 0, 0, stt_blocks])

    # Проверка на доступность GPT-токенов
    last_messages, total_spent_tokens = select_n_last_messages(user_id, COUNT_LAST_MSG)
    total_gpt_tokens, error_message = is_gpt_token_limit(last_messages, total_spent_tokens)
    if error_message:
        bot.send_message(user_id, error_message)
        return

    # Запрос к GPT и обработка ответа
    status_gpt, answer_gpt, tokens_in_answer = ask_gpt(last_messages)
    if not status_gpt:
        bot.send_message(user_id, answer_gpt)
        return
    total_gpt_tokens += tokens_in_answer

    # Проверка на лимит символов для SpeechKit
    tts_symbols, error_message = is_tts_symbol_limit(message, answer_gpt)

    # Запись ответа GPT в БД
    add_message(user_id=user_id, full_message=[answer_gpt, 'assistant', total_gpt_tokens, tts_symbols, 0])

    if error_message:
        bot.send_message(user_id, error_message)
        return

    # Преобразование ответа в аудио и отправка
    status_tts, voice_response = text_to_speech(answer_gpt)
    if status_tts:
        bot.send_voice(user_id, voice_response, reply_to_message_id=message.id)
    else:
        bot.send_message(user_id, answer_gpt, reply_to_message_id=message.id)


@bot.message_handler(content_types=['text'])
def handle_text(message):
    try:
        user_id = message.from_user.id

        # ВАЛИДАЦИЯ: проверяем, есть ли место для ещё одного пользователя (если пользователь новый)
        status_check_users, error_message = check_number_of_users(user_id)
        if not status_check_users:
            bot.send_message(user_id, error_message)  # мест нет =(
            return

        # БД: добавляем сообщение пользователя и его роль в базу данных
        full_user_message = [message.text, 'user', 0, 0, 0]
        add_message(user_id=user_id, full_message=full_user_message)

        # ВАЛИДАЦИЯ: считаем количество доступных пользователю GPT-токенов
        # получаем последние 4 (COUNT_LAST_MSG) сообщения и количество уже потраченных токенов
        last_messages, total_spent_tokens = select_n_last_messages(user_id, COUNT_LAST_MSG)
        # получаем сумму уже потраченных токенов + токенов в новом сообщении и оставшиеся лимиты пользователя
        total_gpt_tokens, error_message = is_gpt_token_limit(last_messages, total_spent_tokens)
        if error_message:
            # если что-то пошло не так — уведомляем пользователя и прекращаем выполнение функции
            bot.send_message(user_id, error_message)
            return

        # GPT: отправляем запрос к GPT
        status_gpt, answer_gpt, tokens_in_answer = ask_gpt(last_messages)
        # GPT: обрабатываем ответ от GPT
        if not status_gpt:
            # если что-то пошло не так — уведомляем пользователя и прекращаем выполнение функции
            bot.send_message(user_id, answer_gpt)
            return
        # сумма всех потраченных токенов + токены в ответе GPT
        total_gpt_tokens += tokens_in_answer

        # БД: добавляем ответ GPT и потраченные токены в базу данных
        full_gpt_message = [answer_gpt, 'assistant', total_gpt_tokens, 0, 0]
        add_message(user_id=user_id, full_message=full_gpt_message)

        bot.send_message(user_id, answer_gpt, reply_to_message_id=message.id)  # отвечаем пользователю текстом
    except Exception as e:
        logging.error(e)  # если ошибка — записываем её в логи
        bot.send_message(message.from_user.id, "Не получилось ответить. Попробуй написать другое сообщение")

# обрабатываем все остальные типы сообщений
@bot.message_handler(func=lambda: True)
def handler(message):
    bot.send_message(message.from_user.id, "Отправь мне голосовое или текстовое сообщение, и я тебе отвечу")

# Запуск бота
bot.polling()