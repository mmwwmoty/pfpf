import asyncio
import aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

class Form(StatesGroup):
    recipient_id = State()
    anonymous_message = State()
    anonymous_reply = State()

class PhotoProcessing(StatesGroup):
    waiting_for_photos = State()

bot = Bot(token='7083060784:AAGahUaPvGKB6tLYpMaSsD_abPUXR_I-u4s')
dp = Dispatcher(bot, storage=MemoryStorage())

async def connect_to_database():
    return await aiosqlite.connect('database.db')

async def create_tables(conn):
    cursor = await conn.cursor()
    await cursor.execute('''CREATE TABLE IF NOT EXISTS users
                      (id INTEGER PRIMARY KEY, username TEXT)''')
    await cursor.execute('''CREATE TABLE IF NOT EXISTS anonymous_messages
                      (sender_id INTEGER, recipient_id INTEGER, message TEXT)''')
    await conn.commit()

async def execute_query(query, params):
    conn = await connect_to_database()
    cursor = await conn.cursor()
    await cursor.execute(query, params)
    await conn.commit()

async def get_sender_id_from_db(recipient_id):
    conn = await connect_to_database()
    cursor = await conn.cursor()
    await cursor.execute("SELECT sender_id FROM anonymous_messages WHERE recipient_id = ? ORDER BY rowid DESC LIMIT 1", (recipient_id,))
    result = await cursor.fetchone()
    return result[0] if result else None

async def get_recipient_id_from_db(sender_id):
    conn = await connect_to_database()
    cursor = await conn.cursor()
    await cursor.execute("SELECT recipient_id FROM anonymous_messages WHERE sender_id = ? ORDER BY rowid DESC LIMIT 1", (sender_id,))
    result = await cursor.fetchone()
    return result[0] if result else None

def check_start_command(text):
    return '/start' in text

@dp.message_handler(commands='start')
async def start(message: types.Message, state: FSMContext):
    await execute_query("INSERT OR REPLACE INTO users VALUES (?, ?)", (message.from_user.id, message.from_user.username))
    recipient_id = message.get_args()
    if recipient_id:
        async with state.proxy() as data:
            if 'recipient_id' in data and data['recipient_id'] == recipient_id:
                markup = InlineKeyboardMarkup()
                cancel_button = InlineKeyboardButton("✖️ Отменить", callback_data="cancel")
                markup.add(cancel_button)
                await bot.send_message(callback_query.from_user.id, "🚀 Здесь можно отправить <b>анонимное сообщение</b> человеку, который опубликовал эту ссылку\n\n🖊 <b>Напишите сюда всё, что хотите ему передать</b>, и через несколько секунд он получит ваше сообщение, но не будет знать от кого\n\nОтправить можно фото, видео, 💬 текст, 🔊 голосовые, 📷видеосообщения (кружки), а также ✨ стикеры", parse_mode="HTML", reply_markup=markup)
            else:
                data['recipient_id'] = recipient_id
                markup = InlineKeyboardMarkup()
                cancel_button = InlineKeyboardButton("✖️ Отменить", callback_data="cancel")
                markup.add(cancel_button)
                await message.answer("🚀 Здесь можно отправить <b>анонимное сообщение</b> человеку, который опубликовал эту ссылку\n\n🖊 <b>Напишите сюда всё, что хотите ему передать</b>, и через несколько секунд он получит ваше сообщение, но не будет знать от кого\n\nОтправить можно фото, видео, 💬 текст, 🔊 голосовые, 📷видеосообщения (кружки), а также ✨ стикеры", parse_mode="HTML", reply_markup=markup)
                await Form.anonymous_message.set()
    else:
        user_id = message.from_user.id
        markup = InlineKeyboardMarkup()
        share_button = InlineKeyboardButton("🔗 Поделиться ссылкой", url="https://t.me/share/url?url=%D0%97%D0%B0%D0%B4%D0%B0%D0%B9%20%D0%BC%D0%BD%D0%B5%20%D0%B0%D0%BD%D0%BE%D0%BD%D0%B8%D0%BC%D0%BD%D1%8B%D0%B9%20%D0%B2%D0%BE%D0%BF%D1%80%D0%BE%D1%81%0A%F0%9F%91%89%20http://t.me/Ietsqbot?start=" + str(user_id))
        markup.add(share_button)
        await bot.send_message(user_id, "<b>Начните получать анонимные вопросы прямо сейчас!</b>\n\n"
                              "👉 <a href='t.me/Ietsqbot?start=" + str(user_id) + "'>t.me/Ietsqbot?start=" + str(user_id) + "</a>\n\n"
                              "<b>Разместите эту ссылку</b> ☝️ в описании своего профиля Telegram, TikTok, Instagram (stories), <b>чтобы вам могли написать 💬</b>",
                              parse_mode="HTML", reply_markup=markup, disable_web_page_preview=True)

@dp.callback_query_handler(lambda c: c.data == 'cancel', state='*')
async def process_callback_cancel(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    user_id = callback_query.from_user.id
    # Удаляем сообщение с кнопкой
    await bot.delete_message(chat_id=user_id, message_id=callback_query.message.message_id)
    markup = InlineKeyboardMarkup()
    share_button = InlineKeyboardButton("🔗 Поделиться ссылкой", url="https://t.me/share/url?url=%D0%97%D0%B0%D0%B4%D0%B0%D0%B9%20%D0%BC%D0%BD%D0%B5%20%D0%B0%D0%BD%D0%BE%D0%BD%D0%B8%D0%BC%D0%BD%D1%8B%D0%B9%20%D0%B2%D0%BE%D0%BF%D1%80%D0%BE%D1%81%0A%F0%9F%91%89%20http://t.me/Ietsqbot?start=" + str(user_id))
    markup.add(share_button)
    await bot.send_message(user_id, "<b>Начните получать анонимные вопросы прямо сейчас!</b>\n\n"
                              "👉 <a href='t.me/Ietsqbot?start=" + str(user_id) + "'>t.me/Ietsqbot?start=" + str(user_id) + "</a>\n\n"
                              "<b>Разместите эту ссылку</b> ☝️ в описании своего профиля Telegram, TikTok, Instagram (stories), <b>чтобы вам могли написать 💬</b>",
                              parse_mode="HTML", reply_markup=markup, disable_web_page_preview=True)
    await state.finish()

@dp.message_handler(state=Form.anonymous_message)
async def process_anonymous_message(message: types.Message, state: FSMContext):
    if check_start_command(message.text):
        markup = InlineKeyboardMarkup()
        cancel_button = InlineKeyboardButton("✖️ Отменить", callback_data="cancel")
        markup.add(cancel_button)
        await message.answer("🚀 Здесь можно отправить <b>анонимное сообщение</b> человеку, который опубликовал эту ссылку\n\n🖊 <b>Напишите сюда всё, что хотите ему передать</b>, и через несколько секунд он получит ваше сообщение, но не будет знать от кого\n\nОтправить можно фото, видео, 💬 текст, 🔊 голосовые, 📷видеосообщения (кружки), а также ✨ стикеры", parse_mode="HTML", reply_markup=markup)
        return
    async with state.proxy() as data:
        recipient_id = data['recipient_id']
        data['anonymous_message'] = message.text
        data['sender_id'] = message.from_user.id  # Сохраняем sender_id в состоянии
    await execute_query("INSERT INTO anonymous_messages (sender_id, recipient_id, message) VALUES (?, ?, ?)", (message.from_user.id, recipient_id, message.text))
    
    await message.answer(f"Ваше анонимное сообщение было отправлено.", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="📨 Написать ещё", callback_data="send_again")]]))
    
    # Создаем кнопку "Ответить" и отправляем сообщение получателю
    reply_markup = InlineKeyboardMarkup()
    reply_button = InlineKeyboardButton("✏ Ответить", callback_data="reply")
    reply_markup.add(reply_button)
    await bot.send_message(recipient_id, f"<b>🔔 У тебя новое сообщение!</b>\n\n<i>{message.text}</i>",parse_mode="HTML", reply_markup=reply_markup)
    await state.finish()

@dp.callback_query_handler(lambda c: c.data == 'send_again', state='*')
async def process_callback_send_again(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    sender_id = callback_query.from_user.id
    recipient_id = await get_recipient_id_from_db(sender_id)
    if recipient_id:
        await state.update_data(recipient_id=recipient_id)  # Save recipient_id in the state
        markup = InlineKeyboardMarkup()
        cancel_button = InlineKeyboardButton("✖️ Отменить", callback_data="cancel")
        markup.add(cancel_button)
        await bot.send_message(callback_query.from_user.id, "🚀 Здесь можно отправить <b>анонимное сообщение</b> человеку, который опубликовал эту ссылку\n\n🖊 <b>Напишите сюда всё, что хотите ему передать</b>, и через несколько секунд он получит ваше сообщение, но не будет знать от кого\n\nОтправить можно фото, видео, 💬 текст, 🔊 голосовые, 📷видеосообщения (кружки), а также ✨ стикеры", parse_mode="HTML", reply_markup=markup)
        await Form.anonymous_message.set()
    else:
        await bot.send_message(callback_query.from_user.id, "Не удалось найти получателя. Пожалуйста, начните заново.")

@dp.callback_query_handler(lambda c: c.data == 'reply', state='*')
async def process_callback_reply(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    recipient_id = callback_query.from_user.id
    sender_id = await get_sender_id_from_db(recipient_id)
    if sender_id:
        await state.update_data(sender_id=sender_id)  # Сохраняем sender_id в состоянии
        markup = InlineKeyboardMarkup()
        cancel_button = InlineKeyboardButton("✖️ Отменить", callback_data="cancel")
        markup.add(cancel_button)
        await bot.send_message(callback_query.from_user.id, "🚀 Здесь можно отправить <b>анонимное сообщение</b> человеку, который опубликовал эту ссылку\n\n🖊 <b>Напишите сюда всё, что хотите ему передать</b>, и через несколько секунд он получит ваше сообщение, но не будет знать от кого\n\nОтправить можно фото, видео, 💬 текст, 🔊 голосовые, 📷видеосообщения (кружки), а также ✨ стикеры", parse_mode="HTML", reply_markup=markup)
        await Form.anonymous_reply.set()
    else:
        await bot.send_message(callback_query.from_user.id, "Не удалось найти отправителя. Пожалуйста, начните заново.")

@dp.message_handler(state=Form.anonymous_reply)
async def process_anonymous_reply(message: types.Message, state: FSMContext):
    if check_start_command(message.text):
        markup = InlineKeyboardMarkup()
        cancel_button = InlineKeyboardButton("✖️ Отменить", callback_data="cancel")
        markup.add(cancel_button)
        await message.answer("🚀 Здесь можно отправить <b>анонимное сообщение</b> человеку, который опубликовал эту ссылку\n\n🖊 <b>Напишите сюда всё, что хотите ему передать</b>, и через несколько секунд он получит ваше сообщение, но не будет знать от кого\n\nОтправить можно фото, видео, 💬 текст, 🔊 голосовые, 📷видеосообщения (кружки), а также ✨ стикеры", parse_mode="HTML", reply_markup=markup)
        return
    async with state.proxy() as data:
        sender_id = data.get('sender_id')  # Получаем sender_id из данных
        recipient_id = data.get('recipient_id')  # Получаем recipient_id из данных
        data['anonymous_reply'] = message.text
    await execute_query("INSERT INTO anonymous_messages (sender_id, recipient_id, message) VALUES (?, ?, ?)", (message.from_user.id, sender_id, message.text))
    
    # Создаем кнопку "Написать еще" и отправляем сообщение отправителю
    reply_markup = InlineKeyboardMarkup()
    reply_button = InlineKeyboardButton("📨 Написать ещё", callback_data="send_again")
    reply_markup.add(reply_button)
    
    await message.answer(f"Сообщение отправлено, ожидайте ответ!", reply_markup=reply_markup)
    
    # Создаем кнопку "Ответить" и отправляем сообщение получателю
    reply_markup = InlineKeyboardMarkup()
    reply_button = InlineKeyboardButton("✏ Ответить", callback_data="reply")
    reply_markup.add(reply_button)
    
    await bot.send_message(sender_id, f"<b>🔔 У тебя новое сообщение!</b>\n\n<i>{message.text}</i>", reply_markup=reply_markup, parse_mode="HTML")
    await state.finish()

from handlers import *

media_group_ids_processed = set()

@dp.message_handler(content_types=['text', 'photo', 'video', 'sticker', 'voice', 'video_note'])
async def handle_all(message: types.Message, state: FSMContext):
    media_group_id = message.media_group_id
    if media_group_id is not None:
        if media_group_id in media_group_ids_processed:
            return
        else:
            media_group_ids_processed.add(media_group_id)
    user_id = message.from_user.id
    markup = InlineKeyboardMarkup()
    share_button = InlineKeyboardButton("🔗 Поделиться ссылкой", url="https://t.me/share/url?url=%D0%97%D0%B0%D0%B4%D0%B0%D0%B9%20%D0%BC%D0%BD%D0%B5%20%D0%B0%D0%BD%D0%BE%D0%BD%D0%B8%D0%BC%D0%BD%D1%8B%D0%B9%20%D0%B2%D0%BE%D0%BF%D1%80%D0%BE%D1%81%0A%F0%9F%91%89%20http://t.me/Ietsqbot?start=" + str(user_id))
    markup.add(share_button)
    await bot.send_message(user_id, "<b>Начните получать анонимные вопросы прямо сейчас!</b>\n\n"
                              "👉 <a href='t.me/Ietsqbot?start=" + str(user_id) + "'>t.me/Ietsqbot?start=" + str(user_id) + "</a>\n\n"
                              "<b>Разместите эту ссылку</b> ☝️ в описании своего профиля Telegram, TikTok, Instagram (stories), <b>чтобы вам могли написать 💬</b>",
                              parse_mode="HTML", reply_markup=markup, disable_web_page_preview=True)


async def main():
    conn = await connect_to_database()
    await create_tables(conn)
    await conn.close()

if __name__ == '__main__':
    from aiogram import executor
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
    print("Бот включен!")
    executor.start_polling(dp, skip_updates=True)
