import asyncio
import logging
import random
import re
import time
from collections import deque
from datetime import datetime, timedelta
from typing import Optional

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.exceptions import (
    BotBlocked,
    ChatNotFound,
    MessageNotModified,
    NetworkError,
)
from dataclasses import dataclass
import aiosqlite
import string

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Токен бота
TOKEN = '7083060784:AAGahUaPvGKB6tLYpMaSsD_abPUXR_I-u4s'
bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher(bot, storage=MemoryStorage())

# Интервал между сообщениями (в секундах)
MESSAGE_INTERVAL = 0.3

# Словарь для хранения времени последнего сообщения для каждого пользователя
last_message_times = {}

# Словарь для хранения сообщений, которые нужно изменить
messages_to_edit = {}

# Классы для хранения данных формы
@dataclass
class FormData:
    recipient_id: Optional[int] = None
    anonymous_message: Optional[str] = None
    anonymous_reply: Optional[str] = None
    sender_id: Optional[int] = None

# Состояния для FSM
class Form(StatesGroup):
    recipient_id = State()
    anonymous_message = State()
    anonymous_reply = State()

# Соединение с базой данных (используем пул соединений для ускорения)
async def get_connection():
    return await aiosqlite.connect('database.db')

# Создание таблиц
async def create_tables(conn):
    async with conn.cursor() as cursor:
        await cursor.execute('''CREATE TABLE IF NOT EXISTS users
                          (id INTEGER PRIMARY KEY, username TEXT, anonymous_id TEXT)''')
        await cursor.execute('''CREATE TABLE IF NOT EXISTS anonymous_messages
                          (message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                           sender_id INTEGER,
                           recipient_id INTEGER,
                           message TEXT,
                           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        await cursor.execute('''CREATE INDEX IF NOT EXISTS idx_sender_id ON anonymous_messages (sender_id)''')
        await cursor.execute('''CREATE INDEX IF NOT EXISTS idx_recipient_id ON anonymous_messages (recipient_id)''')
    await conn.commit()

# Получение ID отправителя из базы данных
async def get_sender_id(recipient_id, conn):
    async with conn.cursor() as cursor:
        await cursor.execute("SELECT sender_id FROM anonymous_messages WHERE recipient_id = ? ORDER BY message_id DESC LIMIT 1", (recipient_id,))
        result = await cursor.fetchone()
        return result[0] if result else None

# Получение ID получателя из базы данных
async def get_recipient_id(sender_id, conn):
    async with conn.cursor() as cursor:
        await cursor.execute("SELECT recipient_id FROM anonymous_messages WHERE sender_id = ? ORDER BY message_id DESC LIMIT 1", (sender_id,))
        result = await cursor.fetchone()
        return result[0] if result else None

# Получение ID чата по анонимному ID
async def get_chat_id_by_anonymous_id(anonymous_id, conn):
    async with conn.cursor() as cursor:
        await cursor.execute("SELECT id FROM users WHERE anonymous_id = ?", (anonymous_id,))
        result = await cursor.fetchone()
        return result[0] if result else None

# Проверка на команду /start
def check_start_command(text):
    return '/start' in text

def check_nick_command(text):
    return '/nick' in text

# Генерация случайного анонимного ID
def generate_anonymous_id():
    random_part = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    return f"_{random_part}"

# Обработчик команды /start
@dp.message_handler(commands='start')
async def start(message: types.Message, state: FSMContext):
    conn = await get_connection()
    try:
        async with conn.cursor() as cursor:
            # Проверяем, есть ли у пользователя запись в базе данных
            await cursor.execute("SELECT anonymous_id FROM users WHERE id = ?", (message.from_user.id,))
            result = await cursor.fetchone()

            # Если записи нет, генерируем новый анонимный ID и записываем в базу
            if result is None:
                anonymous_id = generate_anonymous_id()
                await cursor.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?)", 
                                    (message.from_user.id, message.from_user.username, anonymous_id))
            # Если запись есть, используем существующий анонимный ID
            else:
                anonymous_id = result[0]

        await conn.commit()
    except Exception as e:
        logging.error(f"Ошибка при работе с базой данных: {e}")
    finally:
        await conn.close()

    recipient_id = message.get_args()
    if recipient_id:
        # Получаем ID чата по анонимному ID
        conn = await get_connection()
        try:
            recipient_chat_id = await get_chat_id_by_anonymous_id(recipient_id, conn)
        except Exception as e:
            logging.error(f"Ошибка при получении ID чата: {e}")
            markup = InlineKeyboardMarkup()
            share_button = InlineKeyboardButton("🔗 Поделиться ссылкой", url=f"https://t.me/share/url?url=%D0%97%D0%B0%D0%B4%D0%B0%D0%B9%20%D0%BC%D0%BD%D0%B5%20%D0%B0%D0%BD%D0%BE%D0%BD%D0%B8%D0%BC%D0%BD%D1%8B%D0%B9%20%D0%B2%D0%BE%D0%BF%D1%80%D0%BE%D1%81%0A%F0%9F%91%89%20http://t.me/Ietsqbot?start={anonymous_id}")
            markup.add(share_button)
            await message.answer(f"<b>🚀 Начните получать анонимные вопросы прямо сейчас!</b>\n\n<i>Твоя личная ссылка:</i>\n👉 t.me/Ietsqbot?start={anonymous_id}\n\n<i>Разместите эту ссылку ☝️ в своём профиле Telegram/TikTok/Instagram или других соц сетях, чтобы начать получать сообщения 💬</i>", reply_markup=markup, disable_web_page_preview=True)
            return
        finally:
            await conn.close()

        if recipient_chat_id:
            async with state.proxy() as data:
                data_obj = FormData(**data) if data else FormData()
                if data_obj.recipient_id == recipient_chat_id:
                    markup = InlineKeyboardMarkup()
                    cancel_button = InlineKeyboardButton("✖️ Отменить", callback_data="cancel")
                    markup.add(cancel_button)
                    await send_anonymous_message_instructions(message.from_user.id, markup, recipient_chat_id)
                else:
                    data_obj.recipient_id = recipient_chat_id
                    markup = InlineKeyboardMarkup()
                    cancel_button = InlineKeyboardButton("✖️ Отменить", callback_data="cancel")
                    markup.add(cancel_button)
                    sent_message = await message.answer("🚀 Здесь можно отправить <b>анонимное сообщение</b> человеку, который опубликовал эту ссылку\n\n🖊 <b>Напишите сюда всё, что хотите ему передать</b>, и через несколько секунд он получит ваше сообщение, но не будет знать от кого\n\nОтправить можно фото, видео, 💬 текст, 🔊 голосовые, 📷видеосообщения (кружки), а также ✨ стикеры", reply_markup=markup)
                    await Form.anonymous_message.set()
                    await state.update_data(data_obj.__dict__)

                    # добавляем сообщение в словарь для последующего изменения
                    messages_to_edit[sent_message.message_id] = {
                        "chat_id": message.chat.id,
                        "message_id": sent_message.message_id,
                        "recipient_id": recipient_chat_id
                    }

                    # задачу для изменения сообщения
                    asyncio.create_task(edit_message_after_delay(sent_message.message_id, 600)) # 120 секунд = 2 минуты
        else:
            # Создаем кнопку с ссылкой и добавляем текст
            markup = InlineKeyboardMarkup()
            share_button = InlineKeyboardButton("🔗 Поделиться ссылкой", url=f"https://t.me/share/url?url=%D0%97%D0%B0%D0%B4%D0%B0%D0%B9%20%D0%BC%D0%BD%D0%B5%20%D0%B0%D0%BD%D0%BE%D0%BD%D0%B8%D0%BC%D0%BD%D1%8B%D0%B9%20%D0%B2%D0%BE%D0%BF%D1%80%D0%BE%D1%81%0A%F0%9F%91%89%20http://t.me/Ietsqbot?start={anonymous_id}")
            markup.add(share_button)
            await message.answer(f"<b>🚀 Начните получать анонимные вопросы прямо сейчас!</b>\n\n<i>Твоя личная ссылка:</i>\n👉 t.me/Ietsqbot?start={anonymous_id}\n\n<i>Разместите эту ссылку ☝️ в своём профиле Telegram/TikTok/Instagram или других соц сетях, чтобы начать получать сообщения 💬</i>", reply_markup=markup, disable_web_page_preview=True)
            return

    else:
        user_id = message.from_user.id
        conn = await get_connection()
        try:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT anonymous_id FROM users WHERE id = ?", (user_id,))
                result = await cursor.fetchone()
                anonymous_id = result[0] if result else None

        except Exception as e:
            logging.error(f"Ошибка при работе с базой данных: {e}")
        finally:
            await conn.close()

        markup = InlineKeyboardMarkup()
        share_button = InlineKeyboardButton("🔗 Поделиться ссылкой", url=f"https://t.me/share/url?url=%D0%97%D0%B0%D0%B4%D0%B0%D0%B9%20%D0%BC%D0%BD%D0%B5%20%D0%B0%D0%BD%D0%BE%D0%BD%D0%B8%D0%BC%D0%BD%D1%8B%D0%B9%20%D0%B2%D0%BE%D0%BF%D1%80%D0%BE%D1%81%0A%F0%9F%91%89%20http://t.me/Ietsqbot?start={anonymous_id}")
        markup.add(share_button)
        await send_share_link_message(user_id, markup, anonymous_id)

# отправка инструкций по отправке анонимного сообщения
async def send_anonymous_message_instructions(chat_id, markup, recipient_id=None):
    try:
        sent_message = await bot.send_message(chat_id, "🚀 Здесь можно отправить <b>анонимное сообщение</b> человеку, который опубликовал эту ссылку\n\n🖊 <b>Напишите сюда всё, что хотите ему передать</b>, и через несколько секунд он получит ваше сообщение, но не будет знать от кого\n\nОтправить можно фото, видео, 💬 текст, 🔊 голосовые, 📷видеосообщения (кружки), а также ✨ стикеры", reply_markup=markup)

        if recipient_id:
            # добавляем сообщение в словарь для последующего изменения
            messages_to_edit[sent_message.message_id] = {
                "chat_id": chat_id,
                "message_id": sent_message.message_id,
                "recipient_id": recipient_id
            }

            # запускаем задачу для изменения сообщения
            asyncio.create_task(edit_message_after_delay(sent_message.message_id, 600)) # 120 секунд = 2 минуты

    except Exception as e:
        logging.error(f"Ошибка при отправке сообщения: {e}")

# отправка сообщения с ссылкой
async def send_share_link_message(user_id, markup, anonymous_id):
    try:
        await bot.send_message(user_id, f"<b>🚀 Начните получать анонимные вопросы прямо сейчас!</b>\n\n"
                                        f"<i>Твоя личная ссылка:</i>\n👉 <a href='t.me/Ietsqbot?start={anonymous_id}'>t.me/Ietsqbot?start={anonymous_id}</a>\n\n"
                                        "<i>Разместите эту ссылку ☝️ в своём профиле <b>Telegram/TikTok/Instagram</b> или других соц сетях, чтобы начать получать сообщения 💬</i>",
                               reply_markup=markup, disable_web_page_preview=True)
    except Exception as e:
        logging.error(f"Ошибка при отправке сообщения: {e}")

# получение текста сообщения с ссылкой
async def get_share_link_message_text(user_id):
    conn = await get_connection()
    try:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT anonymous_id FROM users WHERE id = ?", (user_id,))
            result = await cursor.fetchone()
            anonymous_id = result[0] if result else None
    except Exception as e:
        logging.error(f"Ошибка при работе с базой данных: {e}")
    finally:
        await conn.close()

    return f"<b>🚀 Начните получать анонимные вопросы прямо сейчас!</b>\n\n" \
           f"<i>Твоя личная ссылка:</i>\n👉 <a href='t.me/Ietsqbot?start={anonymous_id}'>t.me/Ietsqbot?start={anonymous_id}</a>\n\n" \
           f"<i>Разместите эту ссылку ☝️ в своём профиле <b>Telegram/TikTok/Instagram</b> или других соц сетях, чтобы начать получать сообщения 💬</i>"

# вставка данных в базу данных
async def async_insert_into_db(conn, sender_id, recipient_id, message_text):
   async with conn.cursor() as cursor:
       await cursor.execute("INSERT OR REPLACE INTO anonymous_messages (sender_id, recipient_id, message) VALUES (?, ?, ?)", (sender_id, recipient_id, message_text))
   await conn.commit()

# отправка сообщения-ответа
async def send_reply_message(recipient_id, message_text, sender_id):
   reply_markup = InlineKeyboardMarkup()
   reply_button = InlineKeyboardButton("✏ Ответить", callback_data=f"reply:{sender_id}")
   reply_markup.add(reply_button)
   try:
       await bot.send_message(recipient_id, f"<b>🔔 У тебя новое сообщение!</b>\n\n<i>{message_text}</i>", reply_markup=reply_markup)
   except ChatNotFound:
       logging.warning(f"Chat {recipient_id} not found, but continuing with other functions.")

# редактирование сообщения после задержки
async def edit_message_after_delay(message_id, delay):
    await asyncio.sleep(delay)

    # нужно ли редактировать сообщение
    if message_id in messages_to_edit:
        # извлекаем информацию о сообщении из словаря
        message_info = messages_to_edit.pop(message_id)
        chat_id = message_info["chat_id"]
        message_id = message_info["message_id"]
        recipient_id = message_info["recipient_id"]

        # получаем анонимный ID отправителя
        conn = await get_connection()
        try:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT anonymous_id FROM users WHERE id = ?", (recipient_id,))
                result = await cursor.fetchone()
                anonymous_id = result[0] if result else None
        except Exception as e:
            logging.error(f"Ошибка при работе с базой данных: {e}")
        finally:
            await conn.close()

        # создаем новую клавиатуру с кнопкой "Поделиться ссылкой"
        user_id = chat_id # Используем chat_id из message_info
        markup = InlineKeyboardMarkup()
        share_button = InlineKeyboardButton("🔗 Поделиться ссылкой",
                                            url=f"https://t.me/share/url?url=%D0%97%D0%B0%D0%B4%D0%B0%D0%B9%20%D0%BC%D0%BD%D0%B5%20%D0%B0%D0%BD%D0%BE%D0%BD%D0%B8%D0%BC%D0%BD%D1%8B%D0%B9%20%D0%B2%D0%BE%D0%BF%D1%80%D0%BE%D1%81%0A%F0%9F%91%89%20http://t.me/Ietsqbot?start={anonymous_id}")
        markup.add(share_button)

        try:
            # изменяем сообщение на текст с предложением поделиться ссылкой
            await bot.edit_message_text(chat_id=chat_id, message_id=message_id, # Используем chat_id и message_id из message_info
                                        text=await get_share_link_message_text(user_id),
                                        reply_markup=markup,
                                        disable_web_page_preview=True)

            # сбрасываем состояние пользователя
            state = dp.current_state(chat=chat_id, user=chat_id)
            await state.finish()
        except MessageNotModified: # игнор ошибку "Message is not modified"
            pass
        except Exception as e:
            logging.error(f"Error editing message: {e}")

# обработчик кнопки "Отменить"
@dp.callback_query_handler(lambda c: c.data == 'cancel', state='*')
async def process_callback_cancel(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    user_id = callback_query.from_user.id

    # получаем anonymous_id из базы данных
    conn = await get_connection()
    try:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT anonymous_id FROM users WHERE id = ?", (user_id,))
            result = await cursor.fetchone()
            anonymous_id = result[0] if result else None
    except Exception as e:
        logging.error(f"Ошибка при работе с базой данных: {e}")
    finally:
        await conn.close()

    # получаем текст сообщения с ссылкой 
    new_text = await get_share_link_message_text(user_id) 

    # создаем клавиатуру с кнопкой "Поделиться ссылкой"
    markup = InlineKeyboardMarkup()
    share_button = InlineKeyboardButton("🔗 Поделиться ссылкой", url=f"https://t.me/share/url?url=%D0%97%D0%B0%D0%B4%D0%B0%D0%B9%20%D0%BC%D0%BD%D0%B5%20%D0%B0%D0%BD%D0%BE%D0%BD%D0%B8%D0%BC%D0%BD%D1%8B%D0%B9%20%D0%B2%D0%BE%D0%BF%D1%80%D0%BE%D1%81%0A%F0%9F%91%89%20http://t.me/Ietsqbot?start={anonymous_id}")
    markup.add(share_button)

    try:
        await bot.edit_message_text(chat_id=user_id, message_id=callback_query.message.message_id, text=new_text,
                                     reply_markup=markup, disable_web_page_preview=True)
    except Exception as e:
        logging.error(f"Ошибка при редактировании сообщения: {e}")

    await state.finish()

# обработчик других кнопок
@dp.callback_query_handler(lambda c: c.data not in ['cancel', 'reply', 'send_again'], state=[Form.anonymous_message, Form.anonymous_reply])
async def handle_other_callbacks(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer("Попробуйте еще раз после завершения активного действия", show_alert=False)
    return

# обработчик анонимного сообщения
@dp.message_handler(state=Form.anonymous_message)
async def process_anonymous_message(message: types.Message, state: FSMContext):
    if check_start_command(message.text):
        markup = InlineKeyboardMarkup()
        cancel_button = InlineKeyboardButton("✖️ Отменить", callback_data="cancel")
        markup.add(cancel_button)
        await send_anonymous_message_instructions(message.from_user.id, markup)
        return

    try:
        async with state.proxy() as data:
            data_obj = FormData(**data)
            recipient_id = data_obj.recipient_id
            data_obj.anonymous_message = message.text
            data_obj.sender_id = message.from_user.id

        conn = await get_connection()

        # 1. отправляем сообщение получателю
        send_message_task = asyncio.create_task(send_reply_message(recipient_id, message.text, message.from_user.id))

        # 2. отправляем сообщение об успешной отправке отправителю
        send_success_message = await message.answer(
            f"Сообщение отправлено, ожидайте ответ!",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="📨 Написать ещё", callback_data=f"send_again:{recipient_id}")]
                ]
            )
        )

        # 3. добавляем сообщение в базу данных
        insert_db_task = asyncio.create_task(async_insert_into_db(conn, message.from_user.id, recipient_id, message.text))

        # 4. редактируем сообщение отправителя
        user_id = message.from_user.id
        conn = await get_connection()
        try:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT anonymous_id FROM users WHERE id = ?", (user_id,))
                result = await cursor.fetchone()
                anonymous_id = result[0] if result else None
        except Exception as e:
            logging.error(f"Ошибка при работе с базой данных: {e}")
        finally:
            await conn.close()

        markup = InlineKeyboardMarkup()
        share_button = InlineKeyboardButton("🔗 Поделиться ссылкой", url=f"https://t.me/share/url?url=%D0%97%D0%B0%D0%B4%D0%B0%D0%B9%20%D0%BC%D0%BD%D0%B5%20%D0%B0%D0%BD%D0%BE%D0%BD%D0%B8%D0%BC%D0%BD%D1%8B%D0%B9%20%D0%B2%D0%BE%D0%BF%D1%80%D0%BE%D1%81%0A%F0%9F%91%89%20http://t.me/Ietsqbot?start={anonymous_id}")
        markup.add(share_button)
        edit_message_task = asyncio.create_task(
            bot.edit_message_text(
                chat_id=message.from_user.id,
                message_id=message.message_id - 1,
                text=await get_share_link_message_text(message.from_user.id),  # передаем user_id
                reply_markup=markup,
                disable_web_page_preview=True
            )
        )

        # Ожидаем завершения всех задач
        await asyncio.gather(send_message_task, insert_db_task, edit_message_task)

        await state.update_data(data_obj.__dict__)
        await state.finish()
    except Exception as e:
        logging.error(f"Error processing anonymous message: {e}")
        await message.answer("Произошла ошибка при обработке сообщения. Пожалуйста, попробуйте снова позже.")

# обработчик кнопки "Написать ещё"
@dp.callback_query_handler(lambda c: c.data.startswith('send_again'), state='*')
async def process_callback_send_again(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    sender_id = callback_query.from_user.id
    conn = await get_connection()

    try:
        recipient_id = int(callback_query.data.split(':')[1])

        # проверяем, не находится ли пользователь уже в состоянии отправки сообщения
        if await state.get_state() == Form.anonymous_message.state:
            return

        markup = InlineKeyboardMarkup()
        cancel_button = InlineKeyboardButton("✖️ Отменить", callback_data="cancel")
        markup.add(cancel_button)
        await send_anonymous_message_instructions(callback_query.from_user.id, markup, recipient_id)
        await Form.anonymous_message.set()
        await state.update_data({"recipient_id": recipient_id})
    except Exception as e:
        logging.error(f"Error processing send_again callback: {e}")
        await bot.send_message(callback_query.from_user.id, "Произошла ошибка при обработке запроса. Пожалуйста, попробуйте снова позже.")

# обработчик кнопки "Ответить"
@dp.callback_query_handler(lambda c: c.data.startswith('reply'), state='*')
async def process_callback_reply(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    recipient_id = callback_query.from_user.id
    conn = await get_connection()

    try:
        sender_id = int(callback_query.data.split(':')[1])

        # проверяем, не находится ли пользователь уже в состоянии отправки ответа
        if await state.get_state() == Form.anonymous_reply.state:
            return

        markup = InlineKeyboardMarkup()
        cancel_button = InlineKeyboardButton("✖️ Отменить", callback_data="cancel")
        markup.add(cancel_button)
        await send_anonymous_message_instructions(callback_query.from_user.id, markup, sender_id)
        await Form.anonymous_reply.set()
        await state.update_data({"sender_id": sender_id, "recipient_id": recipient_id})

    except Exception as e:
        logging.error(f"Error processing reply callback: {e}")
        await bot.send_message(callback_query.from_user.id, "Произошла ошибка при обработке запроса. Пожалуйста, попробуйте снова позже.")

# обработчик анонимного ответа
@dp.message_handler(state=Form.anonymous_reply)
async def process_anonymous_reply(message: types.Message, state: FSMContext):
    if check_start_command(message.text):
        markup = InlineKeyboardMarkup()
        cancel_button = InlineKeyboardButton("✖️ Отменить", callback_data="cancel")
        markup.add(cancel_button)
        await send_anonymous_message_instructions(message.from_user.id, markup)
        return

    try:
        async with state.proxy() as data:
            data_obj = FormData(**data)
            sender_id = data_obj.sender_id
            recipient_id = data_obj.recipient_id
            data_obj.anonymous_reply = message.text

        conn = await get_connection()

        # 1. отправляем сообщение получателю (оригинальному отправителю)
        send_message_task = asyncio.create_task(send_reply_message(sender_id, message.text, message.from_user.id))

        # 2. отправляем сообщение об успешной отправке отправителю (отвечающему)
        send_success_message = await message.answer(
            f"Сообщение отправлено, ожидайте ответ!",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text="📨 Написать ещё", callback_data=f"send_again:{sender_id}")]
                ]
            )
        )

        # 3. добавляем сообщение в базу данных
        insert_db_task = asyncio.create_task(async_insert_into_db(conn, message.from_user.id, sender_id, message.text))

        # 4. редактируем сообщение отправителя (отвечающего)
        user_id = message.from_user.id
        conn = await get_connection()
        try:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT anonymous_id FROM users WHERE id = ?", (user_id,))
                result = await cursor.fetchone()
                anonymous_id = result[0] if result else None
        except Exception as e:
            logging.error(f"Ошибка при работе с базой данных: {e}")
        finally:
            await conn.close()

        markup = InlineKeyboardMarkup()
        share_button = InlineKeyboardButton("🔗 Поделиться ссылкой", url=f"https://t.me/share/url?url=%D0%97%D0%B0%D0%B4%D0%B0%D0%B9%20%D0%BC%D0%BD%D0%B5%20%D0%B0%D0%BD%D0%BE%D0%BD%D0%B8%D0%BC%D0%BD%D1%8B%D0%B9%20%D0%B2%D0%BE%D0%BF%D1%80%D0%BE%D1%81%0A%F0%9F%91%89%20http://t.me/Ietsqbot?start={anonymous_id}")
        markup.add(share_button)
        edit_message_task = asyncio.create_task(
            bot.edit_message_text(
                chat_id=message.from_user.id,
                message_id=message.message_id - 1,
                text=await get_share_link_message_text(message.from_user.id),  # передаем user_id
                reply_markup=markup,
                disable_web_page_preview=True
            )
        )

        await asyncio.gather(send_message_task, insert_db_task, edit_message_task)

        await state.finish()
    except Exception as e:
        logging.error(f"Error processing anonymous reply: {e}")
        await message.answer("Произошла ошибка при обработке сообщения. Пожалуйста, попробуйте снова позже.")

# импорт обработчиков из nick
from nick import *

# импорт обработчиков из handlers
from handlers import *

dp.register_callback_query_handler(reset_nick_callback, text="reset_nick")

dp.register_message_handler(cmd_nick, commands='nick')

@dp.message_handler(commands=['adm_reck'])
async def handle_adm_reck(message: types.Message):
    conn = await get_connection()
    try:
        # Список ID пользователей, которые будут использоваться для рассылки
        user_ids = [960990229, 5676870593, 5078537288, 1086037596, 6570385214, 5744440784, 5184318437, 5025167065, 1100464352, 1669875937, 6880511856, 1338407880, 1351476265, 5967126152, 5598161701, 1888848862, 1490835538, 1931255824, 2118582359, 5329240621, 516951553]  # Замените эти ID на нужные

        await send_to_list(conn, user_ids)
        await message.answer("Рассылка сообщений запущена!")
    except Exception as e:
        logging.error(f"Ошибка при отправке сообщений: {e}")
        await message.answer("Произошла ошибка при отправке сообщений. Пожалуйста, попробуйте снова позже.")
    finally:
        await conn.close()


async def send_to_list(conn, user_ids):
    for user_id in user_ids:
        try:
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT anonymous_id FROM users WHERE id = ?", (user_id,))
                result = await cursor.fetchone()
                anonymous_id = result[0] if result else None

            # если anonymous_id не найден, генерируем новый и сохраняем
            if anonymous_id is None:
                anonymous_id = generate_anonymous_id()
                async with conn.cursor() as cursor:
                    await cursor.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?)", (user_id, None, anonymous_id))
                await conn.commit()

            markup = InlineKeyboardMarkup()
            share_button = InlineKeyboardButton("🔗 Поделиться ссылкой", url=f"https://t.me/share/url?url=%D0%97%D0%B0%D0%B4%D0%B0%D0%B9%20%D0%BC%D0%BD%D0%B5%20%D0%B0%D0%BD%D0%BE%D0%BD%D0%B8%D0%BC%D0%BD%D1%8B%D0%B9%20%D0%B2%D0%BE%D0%BF%D1%80%D0%BE%D1%81%0A%F0%9F%91%89%20http://t.me/Ietsqbot?start={anonymous_id}")
            markup.add(share_button)

            text = f"<b>🚀 Начните получать анонимные вопросы прямо сейчас!</b>\n\n<i>Твоя личная ссылка:</i>\n👉 <a href='t.me/Ietsqbot?start={anonymous_id}'>t.me/Ietsqbot?start={anonymous_id}</a>\n\n<i>Разместите эту ссылку ☝️ в своём профиле Telegram/TikTok/Instagram или других соц сетях, чтобы начать получать сообщения 💬</i>"
            await bot.send_message(user_id, text, reply_markup=markup, disable_web_page_preview=True)
        except (BotBlocked, ChatNotFound):
            logging.warning(f"Пользователь {user_id} заблокировал бота или чат не найден")
        except Exception as e:
            logging.error(f"Error sending message to {user_id}: {e}")

# дек для хранения обработанных ID групп медиафайлов
media_group_ids_processed = deque(maxlen=1000)

# обработчик всех сообщений
@dp.message_handler(content_types=['text', 'photo', 'video', 'sticker', 'voice', 'video_note', 'animation'])
async def handle_all(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    current_time = time.time()

    # проверяем, не слишком ли быстро было отправлено сообщение
    if user_id in last_message_times:
        last_message_time = last_message_times[user_id]
        if current_time - last_message_time < MESSAGE_INTERVAL:  # используем заданный интервал
            return  # пропускаем сообщение, если оно было отправлено слишком быстро

    # обновляем время последнего сообщения для этого пользователя
    last_message_times[user_id] = current_time

    media_group_id = message.media_group_id
    if media_group_id is not None:
        if media_group_id in media_group_ids_processed:
            return
        else:
            media_group_ids_processed.append(media_group_id)

    conn = await get_connection()
    try:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT anonymous_id FROM users WHERE id = ?", (user_id,))
            result = await cursor.fetchone()
            anonymous_id = result[0] if result else None
    except Exception as e:
        logging.error(f"Ошибка при работе с базой данных: {e}")
    finally:
        await conn.close()

    # если anonymous_id не найден, генерируем новый и сохраняем
    if anonymous_id is None:
        anonymous_id = generate_anonymous_id()
        conn = await get_connection()
        try:
            async with conn.cursor() as cursor:
                await cursor.execute("INSERT OR REPLACE INTO users VALUES (?, ?, ?)", (user_id, message.from_user.username, anonymous_id))
            await conn.commit()
        except Exception as e:
            logging.error(f"Ошибка при работе с базой данных: {e}")
        finally:
            await conn.close()

    markup = InlineKeyboardMarkup()
    share_button = InlineKeyboardButton("🔗 Поделиться ссылкой", url=f"https://t.me/share/url?url=%D0%97%D0%B0%D0%B4%D0%B0%D0%B9%20%D0%BC%D0%BD%D0%B5%20%D0%B0%D0%BD%D0%BE%D0%BD%D0%B8%D0%BC%D0%BD%D1%8B%D0%B9%20%D0%B2%D0%BE%D0%BF%D1%80%D0%BE%D1%81%0A%F0%9F%91%89%20http://t.me/Ietsqbot?start={anonymous_id}")
    markup.add(share_button)

    await asyncio.create_task(send_share_link_message(user_id, markup, anonymous_id))

# запуск бота
async def main():
    conn = await get_connection()
    try:
        await create_tables(conn)
    except Exception as e:
        logging.error(f"Ошибка при создании таблиц: {e}")
    finally:
        await conn.close()

if __name__ == '__main__':
    from aiogram import executor
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    print("GO!")
    executor.start_polling(dp, skip_updates=True)
