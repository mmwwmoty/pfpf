import aiogram
import asyncio
from aiogram.utils.exceptions import NetworkError
import aiosqlite
import time
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from collections import deque
import logging
from typing import Optional
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)

TOKEN = '7083060784:AAGahUaPvGKB6tLYpMaSsD_abPUXR_I-u4s'
bot = Bot(token=TOKEN, parse_mode="HTML")
dp = Dispatcher(bot, storage=MemoryStorage())

@dataclass
class FormData:
    recipient_id: Optional[int] = None
    anonymous_message: Optional[str] = None
    anonymous_reply: Optional[str] = None
    sender_id: Optional[int] = None

class Form(StatesGroup):
    recipient_id = State()
    anonymous_message = State()
    anonymous_reply = State()

class PhotoProcessing(StatesGroup):
    waiting_for_photos = State()

async def get_connection():
    return await aiosqlite.connect('database.db')

async def create_tables(conn):
    async with conn.cursor() as cursor:
        await cursor.execute('''CREATE TABLE IF NOT EXISTS users
                          (id INTEGER PRIMARY KEY, username TEXT)''')
        await cursor.execute('''CREATE TABLE IF NOT EXISTS anonymous_messages
                          (sender_id INTEGER, recipient_id INTEGER, message TEXT, PRIMARY KEY (sender_id, recipient_id))''')
        await cursor.execute('''CREATE INDEX IF NOT EXISTS idx_sender_id ON anonymous_messages (sender_id)''')
        await cursor.execute('''CREATE INDEX IF NOT EXISTS idx_recipient_id ON anonymous_messages (recipient_id)''')
    await conn.commit()

async def get_sender_id(recipient_id, conn):
    async with conn.cursor() as cursor:
        await cursor.execute("SELECT sender_id FROM anonymous_messages WHERE recipient_id = ? ORDER BY rowid DESC LIMIT 1", (recipient_id,))
        result = await cursor.fetchone()
        return result[0] if result else None

async def get_recipient_id(sender_id, conn):
    async with conn.cursor() as cursor:
        await cursor.execute("SELECT recipient_id FROM anonymous_messages WHERE sender_id = ? ORDER BY rowid DESC LIMIT 1", (sender_id,))
        result = await cursor.fetchone()
        return result[0] if result else None

def check_start_command(text):
    return '/start' in text

@dp.message_handler(commands='start')
async def start(message: types.Message, state: FSMContext):
    conn = await get_connection()
    try:
        async with conn.cursor() as cursor:
            await cursor.execute("INSERT OR REPLACE INTO users VALUES (?, ?)", (message.from_user.id, message.from_user.username))
        await conn.commit()
    except Exception as e:
        logging.error(f"Ошибка при работе с базой данных: {e}")
    finally:
        await conn.close()

    recipient_id = message.get_args()
    if recipient_id:
        async with state.proxy() as data:
            data_obj = FormData(**data) if data else FormData()
            if data_obj.recipient_id == recipient_id:
                markup = InlineKeyboardMarkup()
                cancel_button = InlineKeyboardButton("✖️ Отменить", callback_data="cancel")
                markup.add(cancel_button)
                await send_anonymous_message_instructions(message.from_user.id, markup)
            else:
                data_obj.recipient_id = recipient_id
                markup = InlineKeyboardMarkup()
                cancel_button = InlineKeyboardButton("✖️ Отменить", callback_data="cancel")
                markup.add(cancel_button)
                await message.answer("🚀 Здесь можно отправить <b>анонимное сообщение</b> человеку, который опубликовал эту ссылку\n\n🖊 <b>Напишите сюда всё, что хотите ему передать</b>, и через несколько секунд он получит ваше сообщение, но не будет знать от кого\n\nОтправить можно фото, видео, 💬 текст, 🔊 голосовые, 📷видеосообщения (кружки), а также ✨ стикеры", reply_markup=markup)
                await Form.anonymous_message.set()
                await state.update_data(data_obj.__dict__)
    else:
        user_id = message.from_user.id
        markup = InlineKeyboardMarkup()
        share_button = InlineKeyboardButton("🔗 Поделиться ссылкой", url=f"https://t.me/share/url?url=%D0%97%D0%B0%D0%B4%D0%B0%D0%B9%20%D0%BC%D0%BD%D0%B5%20%D0%B0%D0%BD%D0%BE%D0%BD%D0%B8%D0%BC%D0%BD%D1%8B%D0%B9%20%D0%B2%D0%BE%D0%BF%D1%80%D0%BE%D1%81%0A%F0%9F%91%89%20http://t.me/Ietsqbot?start={user_id}")
        markup.add(share_button)
        await send_share_link_message(user_id, markup)

async def send_anonymous_message_instructions(chat_id, markup):
    try:
        await bot.send_message(chat_id, "🚀 Здесь можно отправить <b>анонимное сообщение</b> человеку, который опубликовал эту ссылку\n\n🖊 <b>Напишите сюда всё, что хотите ему передать</b>, и через несколько секунд он получит ваше сообщение, но не будет знать от кого\n\nОтправить можно фото, видео, 💬 текст, 🔊 голосовые, 📷видеосообщения (кружки), а также ✨ стикеры", reply_markup=markup)
    except Exception as e:
        logging.error(f"Ошибка при отправке сообщения: {e}")

async def send_share_link_message(user_id, markup):
    try:
        await bot.send_message(user_id, f"<b>🚀 Начните получать анонимные вопросы прямо сейчас!</b>\n\n"
                                        f"<i>Твоя личная ссылка:</i>\n👉 <a href='t.me/Ietsqbot?start={user_id}'>t.me/Ietsqbot?start={user_id}</a>\n\n"
                                        "<i>Разместите эту ссылку ☝️ в своём профиле <b>Telegram/TikTok/Instagram</b> или других соц сетях, чтобы начать получать сообщения 💬</i>",
                               reply_markup=markup, disable_web_page_preview=True)
    except Exception as e:
        logging.error(f"Ошибка при отправке сообщения: {e}")

async def get_share_link_message_text(user_id):
   return f"<b>🚀 Начните получать анонимные вопросы прямо сейчас!</b>\n\n" \
          f"<i>Твоя личная ссылка:</i>\n👉 <a href='t.me/Ietsqbot?start={user_id}'>t.me/Ietsqbot?start={user_id}</a>\n\n" \
          f"<i>Разместите эту ссылку ☝️ в своём профиле <b>Telegram/TikTok/Instagram</b> или других соц сетях, чтобы начать получать сообщения 💬</i>"

async def async_insert_into_db(conn, sender_id, recipient_id, message_text):
   async with conn.cursor() as cursor:
       await cursor.execute("INSERT OR REPLACE INTO anonymous_messages (sender_id, recipient_id, message) VALUES (?, ?, ?)", (sender_id, recipient_id, message_text))
   await conn.commit()

async def send_reply_message(recipient_id, message_text, sender_id):
   reply_markup = InlineKeyboardMarkup()
   reply_button = InlineKeyboardButton("✏ Ответить", callback_data=f"reply:{sender_id}")
   reply_markup.add(reply_button)
   try:
       await bot.send_message(recipient_id, f"<b>🔔 У тебя новое сообщение!</b>\n\n<i>{message_text}</i>", reply_markup=reply_markup)
   except aiogram.utils.exceptions.ChatNotFound:
       logging.warning("Chat not found, but continuing with other functions.")

@dp.callback_query_handler(lambda c: c.data == 'cancel', state='*')
async def process_callback_cancel(callback_query: types.CallbackQuery, state: FSMContext):
   await bot.answer_callback_query(callback_query.id)
   user_id = callback_query.from_user.id
   markup = InlineKeyboardMarkup()
   share_button = InlineKeyboardButton("🔗 Поделиться ссылкой", url=f"https://t.me/share/url?url=%D0%97%D0%B0%D0%B4%D0%B0%D0%B9%20%D0%BC%D0%BD%D0%B5%20%D0%B0%D0%BD%D0%BE%D0%BD%D0%B8%D0%BC%D0%BD%D1%8B%D0%B9%20%D0%B2%D0%BE%D0%BF%D1%80%D0%BE%D1%81%0A%F0%9F%91%89%20http://t.me/Ietsqbot?start={user_id}")
   markup.add(share_button)
   new_text = await get_share_link_message_text(user_id)

   try:
       await bot.edit_message_text(chat_id=user_id, message_id=callback_query.message.message_id, text=new_text,
                                    reply_markup=markup, disable_web_page_preview=True)
   except Exception as e:
       logging.error(f"Ошибка при редактировании сообщения: {e}")

   await state.finish()

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
       insert_db_task = asyncio.create_task(async_insert_into_db(conn, message.from_user.id, recipient_id, message.text))

       user_id = message.from_user.id
       markup = InlineKeyboardMarkup()
       share_button = InlineKeyboardButton("🔗 Поделиться ссылкой", url=f"https://t.me/share/url?url=%D0%97%D0%B0%D0%B4%D0%B0%D0%B9%20%D0%BC%D0%BD%D0%B5%20%D0%B0%D0%BD%D0%BE%D0%BD%D0%B8%D0%BC%D0%BD%D1%8B%D0%B9%20%D0%B2%D0%BE%D0%BF%D1%80%D0%BE%D1%81%0A%F0%9F%91%89%20http://t.me/Ietsqbot?start={user_id}")
       markup.add(share_button)
       edit_message_task = asyncio.create_task(bot.edit_message_text(chat_id=message.from_user.id, message_id=message.message_id - 1, text=await get_share_link_message_text(user_id), reply_markup=markup, disable_web_page_preview=True))

       send_message_task = asyncio.create_task(send_reply_message(recipient_id, message.text, message.from_user.id))

       await asyncio.gather(insert_db_task, send_message_task)
       await edit_message_task

       send_success_message = await message.answer(f"Сообщение отправлено, ожидайте ответ!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📨 Написать ещё", callback_data=f"send_again:{recipient_id}")]]))

       await state.update_data(data_obj.__dict__)
       await state.finish()
   except Exception as e:
       logging.error(f"Error processing anonymous message: {e}")
       await message.answer("Произошла ошибка при обработке сообщения. Пожалуйста, попробуйте снова позже.")

@dp.callback_query_handler(lambda c: c.data.startswith('send_again'), state='*')
async def process_callback_send_again(callback_query: types.CallbackQuery, state: FSMContext):
  await bot.answer_callback_query(callback_query.id)
  sender_id = callback_query.from_user.id
  conn = await get_connection()

  try:
      recipient_id = int(callback_query.data.split(':')[1])
      markup = InlineKeyboardMarkup()
      cancel_button = InlineKeyboardButton("✖️ Отменить", callback_data="cancel")
      markup.add(cancel_button)
      await send_anonymous_message_instructions(callback_query.from_user.id, markup)
      await Form.anonymous_message.set()
      await state.update_data({"recipient_id": recipient_id})
  except Exception as e:
      logging.error(f"Error processing send_again callback: {e}")
      await bot.send_message(callback_query.from_user.id, "Произошла ошибка при обработке запроса. Пожалуйста, попробуйте снова позже.")

@dp.callback_query_handler(lambda c: c.data.startswith('reply'), state='*')
async def process_callback_reply(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    recipient_id = callback_query.from_user.id
    conn = await get_connection()

    try:
        sender_id = int(callback_query.data.split(':')[1])
        markup = InlineKeyboardMarkup()
        cancel_button = InlineKeyboardButton("✖️ Отменить", callback_data="cancel")
        markup.add(cancel_button)
        await send_anonymous_message_instructions(callback_query.from_user.id, markup)
        await Form.anonymous_reply.set()
        await state.update_data({"sender_id": sender_id, "recipient_id": recipient_id})

    except Exception as e:
        logging.error(f"Error processing reply callback: {e}")
        await bot.send_message(callback_query.from_user.id, "Произошла ошибка при обработке запроса. Пожалуйста, попробуйте снова позже.")

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
        insert_db_task = asyncio.create_task(async_insert_into_db(conn, message.from_user.id, sender_id, message.text))

        user_id = message.from_user.id
        markup = InlineKeyboardMarkup()
        share_button = InlineKeyboardButton("🔗 Поделиться ссылкой", url=f"https://t.me/share/url?url=%D0%97%D0%B0%D0%B4%D0%B0%D0%B9%20%D0%BC%D0%BD%D0%B5%20%D0%B0%D0%BD%D0%BE%D0%BD%D0%B8%D0%BC%D0%BD%D1%8B%D0%B9%20%D0%B2%D0%BE%D0%BF%D1%80%D0%BE%D1%81%0A%F0%9F%91%89%20http://t.me/Ietsqbot?start={user_id}")
        markup.add(share_button)
        edit_message_task = asyncio.create_task(bot.edit_message_text(chat_id=message.from_user.id, message_id=message.message_id - 1, text=await get_share_link_message_text(user_id), reply_markup=markup, disable_web_page_preview=True))

        send_message_task = asyncio.create_task(send_reply_message(sender_id, message.text, message.from_user.id))

        await asyncio.gather(insert_db_task, edit_message_task, send_message_task)

        send_success_message = await message.answer(f"Сообщение отправлено, ожидайте ответ!", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📨 Написать ещё", callback_data=f"send_again:{sender_id}")]]))

        await state.finish()
    except Exception as e:
        logging.error(f"Error processing anonymous reply: {e}")
        await message.answer("Произошла ошибка при обработке сообщения. Пожалуйста, попробуйте снова позже.")

from handlers import *

media_group_ids_processed = deque(maxlen=1000)

last_message_times = {}

@dp.message_handler(content_types=['text', 'photo', 'video', 'sticker', 'voice', 'video_note'])
async def handle_all(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    current_time = time.time()

    # Проверяем, не слишком ли быстро было отправлено сообщение
    if user_id in last_message_times:
        last_message_time = last_message_times[user_id]
        if current_time - last_message_time < 0.4:  # Задаем допустимый интервал между сообщениями 
            return  # Пропускаем сообщение, если оно было отправлено слишком быстро

    # Обновляем время последнего сообщения для этого пользователя
    last_message_times[user_id] = current_time
    media_group_id = message.media_group_id
    if media_group_id is not None:
        if media_group_id in media_group_ids_processed:
            return
        else:
            media_group_ids_processed.append(media_group_id)

    user_id = message.from_user.id
    markup = InlineKeyboardMarkup()
    share_button = InlineKeyboardButton("🔗 Поделиться ссылкой", url=f"https://t.me/share/url?url=%D0%97%D0%B0%D0%B4%D0%B0%D0%B9%20%D0%BC%D0%BD%D0%B5%20%D0%B0%D0%BD%D0%BE%D0%BD%D0%B8%D0%BC%D0%BD%D1%8B%D0%B9%20%D0%B2%D0%BE%D0%BF%D1%80%D0%BE%D1%81%0A%F0%9F%91%89%20http://t.me/Ietsqbot?start={user_id}")
    markup.add(share_button)

    await asyncio.create_task(send_share_link_message(user_id, markup))

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
