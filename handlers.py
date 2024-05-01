from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from main import dp, bot, Form, FormData, get_connection

@dp.callback_query_handler(lambda c: c.data.startswith('reply'), state='*')
async def process_callback_reply(callback_query: types.CallbackQuery, state: FSMContext):
    sender_id = int(callback_query.data.split(':')[1])
    await state.update_data(sender_id=sender_id)
    markup = InlineKeyboardMarkup()
    cancel_button = InlineKeyboardButton("✖️ Отменить", callback_data="cancel")
    markup.add(cancel_button)
    await bot.send_message(callback_query.from_user.id, "🚀 Здесь можно отправить <b>анонимное сообщение</b> человеку, который опубликовал эту ссылку\n\n🖊 <b>Напишите сюда всё, что хотите ему передать</b>, и через несколько секунд он получит ваше сообщение, но не будет знать от кого\n\nОтправить можно фото, видео, 💬 текст, 🔊 голосовые, 📷видеосообщения (кружки), а также ✨ стикеры", parse_mode="HTML", reply_markup=markup)
    await Form.anonymous_reply.set()

@dp.message_handler(content_types=['photo'], state=Form.anonymous_message)
async def process_anonymous_photo(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data_obj = FormData(**data)
        recipient_id = data_obj.recipient_id
    photo_id = message.photo[-1].file_id

    conn = await get_connection()
    async with conn.cursor() as cursor:
        await cursor.execute("INSERT INTO anonymous_messages (sender_id, recipient_id, message) VALUES (?, ?, ?)", (message.from_user.id, recipient_id, photo_id))
    await conn.commit()

    reply_markup = InlineKeyboardMarkup()
    reply_button = InlineKeyboardButton("✏ Ответить", callback_data=f"reply:{message.from_user.id}")
    reply_markup.add(reply_button)

    await bot.send_photo(chat_id=recipient_id, photo=message.photo[-1].file_id, caption="<b>🔔 У тебя новое сообщение!</b>\n\n", reply_markup=reply_markup, parse_mode="HTML")

    again_markup = InlineKeyboardMarkup()
    again_button = InlineKeyboardButton("📨 Написать ещё", callback_data=f"send_again:{recipient_id}")
    again_markup.add(again_button)

    await bot.send_message(message.from_user.id, "Сообщение отправлено, ожидайте ответ!", reply_markup=again_markup)
    await state.finish()

@dp.message_handler(content_types=['photo'], state=Form.anonymous_reply)
async def process_anonymous_reply_photo(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data_obj = FormData(**data)
        sender_id = data_obj.sender_id
    photo_id = message.photo[-1].file_id

    conn = await get_connection()
    async with conn.cursor() as cursor:
        await cursor.execute("INSERT INTO anonymous_messages (sender_id, recipient_id, message) VALUES (?, ?, ?)", (message.from_user.id, sender_id, photo_id))
    await conn.commit()

    reply_markup = InlineKeyboardMarkup()
    reply_button = InlineKeyboardButton("📨 Написать ещё", callback_data=f"send_again:{sender_id}")
    reply_markup.add(reply_button)

    await message.answer(f"Сообщение отправлено, ожидайте ответ!", reply_markup=reply_markup)

    reply_markup = InlineKeyboardMarkup()
    reply_button = InlineKeyboardButton("✏ Ответить", callback_data=f"reply:{message.from_user.id}")
    reply_markup.add(reply_button)

    await bot.send_photo(sender_id, photo_id, caption="<b>🔔 У тебя новое сообщение!</b>\n\n", reply_markup=reply_markup, parse_mode="HTML")
    await state.finish()

@dp.message_handler(content_types=['video'], state=Form.anonymous_message)
async def process_anonymous_video(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data_obj = FormData(**data)
        recipient_id = data_obj.recipient_id
    video_id = message.video.file_id

    conn = await get_connection()
    async with conn.cursor() as cursor:
        await cursor.execute("INSERT INTO anonymous_messages (sender_id, recipient_id, message) VALUES (?, ?, ?)", (message.from_user.id, recipient_id, video_id))
    await conn.commit()

    reply_markup = InlineKeyboardMarkup()
    reply_button = InlineKeyboardButton("✏ Ответить", callback_data=f"reply:{message.from_user.id}")
    reply_markup.add(reply_button)

    await bot.send_video(chat_id=recipient_id, video=message.video.file_id, caption="<b>🔔 У тебя новое сообщение!</b>\n\n", reply_markup=reply_markup, parse_mode="HTML")

    again_markup = InlineKeyboardMarkup()
    again_button = InlineKeyboardButton("📨 Написать ещё", callback_data=f"send_again:{recipient_id}")
    again_markup.add(again_button)

    await bot.send_message(message.from_user.id, "Сообщение отправлено, ожидайте ответ!", reply_markup=again_markup)
    await state.finish()

@dp.message_handler(content_types=['video'], state=Form.anonymous_reply)
async def process_anonymous_reply_video(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data_obj = FormData(**data)
        sender_id = data_obj.sender_id
    video_id = message.video.file_id

    conn = await get_connection()
    async with conn.cursor() as cursor:
        await cursor.execute("INSERT INTO anonymous_messages (sender_id, recipient_id, message) VALUES (?, ?, ?)", (message.from_user.id, sender_id, video_id))
    await conn.commit()

    reply_markup = InlineKeyboardMarkup()
    reply_button = InlineKeyboardButton("📨 Написать ещё", callback_data=f"send_again:{sender_id}")
    reply_markup.add(reply_button)

    await message.answer(f"Сообщение отправлено, ожидайте ответ!", reply_markup=reply_markup)

    reply_markup = InlineKeyboardMarkup()
    reply_button = InlineKeyboardButton("✏ Ответить", callback_data=f"reply:{message.from_user.id}")
    reply_markup.add(reply_button)

    await bot.send_video(sender_id, video_id, caption="<b>🔔 У тебя новое сообщение!</b>\n\n", reply_markup=reply_markup, parse_mode="HTML")
    await state.finish()

@dp.message_handler(content_types=['voice'], state=Form.anonymous_message)
async def process_anonymous_voice(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data_obj = FormData(**data)
        recipient_id = data_obj.recipient_id
    voice_id = message.voice.file_id

    conn = await get_connection()
    async with conn.cursor() as cursor:
        await cursor.execute("INSERT INTO anonymous_messages (sender_id, recipient_id, message) VALUES (?, ?, ?)", (message.from_user.id, recipient_id, voice_id))
    await conn.commit()

    reply_markup = InlineKeyboardMarkup()
    reply_button = InlineKeyboardButton("✏ Ответить", callback_data=f"reply:{message.from_user.id}")
    reply_markup.add(reply_button)

    await bot.send_voice(chat_id=recipient_id, voice=message.voice.file_id, caption="<b>🔔 У тебя новое сообщение!</b>\n\n", reply_markup=reply_markup, parse_mode="HTML")

    again_markup = InlineKeyboardMarkup()
    again_button = InlineKeyboardButton("📨 Написать ещё", callback_data=f"send_again:{recipient_id}")
    again_markup.add(again_button)

    await bot.send_message(message.from_user.id, "Сообщение отправлено, ожидайте ответ!", reply_markup=again_markup)
    await state.finish()

@dp.message_handler(content_types=['voice'], state=Form.anonymous_reply)
async def process_anonymous_reply_voice(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data_obj = FormData(**data)
        sender_id = data_obj.sender_id
    voice_id = message.voice.file_id

    conn = await get_connection()
    async with conn.cursor() as cursor:
        await cursor.execute("INSERT INTO anonymous_messages (sender_id, recipient_id, message) VALUES (?, ?, ?)", (message.from_user.id, sender_id, voice_id))
    await conn.commit()

    reply_markup = InlineKeyboardMarkup()
    reply_button = InlineKeyboardButton("📨 Написать ещё", callback_data=f"send_again:{sender_id}")
    reply_markup.add(reply_button)

    await message.answer(f"Сообщение отправлено, ожидайте ответ!", reply_markup=reply_markup)

    reply_markup = InlineKeyboardMarkup()
    reply_button = InlineKeyboardButton("✏ Ответить", callback_data=f"reply:{message.from_user.id}")
    reply_markup.add(reply_button)

    await bot.send_voice(sender_id, voice_id, caption="<b>🔔 У тебя новое сообщение!</b>\n\n", reply_markup=reply_markup, parse_mode="HTML")
    await state.finish()

@dp.message_handler(content_types=['video_note'], state=Form.anonymous_message)
async def process_anonymous_video_note(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data_obj = FormData(**data)
        recipient_id = data_obj.recipient_id
    video_note_id = message.video_note.file_id

    conn = await get_connection()
    async with conn.cursor() as cursor:
        await cursor.execute("INSERT INTO anonymous_messages (sender_id, recipient_id, message) VALUES (?, ?, ?)", (message.from_user.id, recipient_id, video_note_id))
    await conn.commit()

    reply_markup = InlineKeyboardMarkup()
    reply_button = InlineKeyboardButton("✏ Ответить", callback_data=f"reply:{message.from_user.id}")
    reply_markup.add(reply_button)

    video_note_message = await bot.send_video_note(chat_id=recipient_id, video_note=video_note_id)
    await bot.send_message(chat_id=recipient_id, text="<b>🔔 У тебя новое сообщение!</b>\n\n", reply_markup=reply_markup, reply_to_message_id=video_note_message.message_id, parse_mode="HTML")

    again_markup = InlineKeyboardMarkup()
    again_button = InlineKeyboardButton("📨 Написать ещё", callback_data=f"send_again:{recipient_id}")
    again_markup.add(again_button)

    await bot.send_message(message.from_user.id, "Сообщение отправлено, ожидайте ответ!", reply_markup=again_markup)
    await state.finish()

@dp.message_handler(content_types=['video_note'], state=Form.anonymous_reply)
async def process_anonymous_reply_video_note(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data_obj = FormData(**data)
        sender_id = data_obj.sender_id
    video_note_id = message.video_note.file_id

    conn = await get_connection()
    async with conn.cursor() as cursor:
        await cursor.execute("INSERT INTO anonymous_messages (sender_id, recipient_id, message) VALUES (?, ?, ?)", (message.from_user.id, sender_id, video_note_id))
    await conn.commit()

    reply_markup = InlineKeyboardMarkup()
    reply_button = InlineKeyboardButton("📨 Написать ещё", callback_data=f"send_again:{sender_id}")
    reply_markup.add(reply_button)

    await message.answer(f"Сообщение отправлено, ожидайте ответ!", reply_markup=reply_markup)

    reply_markup = InlineKeyboardMarkup()
    reply_button = InlineKeyboardButton("✏ Ответить", callback_data=f"reply:{message.from_user.id}")
    reply_markup.add(reply_button)

    video_note_message = await bot.send_video_note(chat_id=sender_id, video_note=video_note_id)
    await bot.send_message(chat_id=sender_id, text="<b>🔔 У тебя новое сообщение!</b>\n\n", reply_markup=reply_markup, reply_to_message_id=video_note_message.message_id, parse_mode="HTML")

    await state.finish()

@dp.message_handler(content_types=['sticker'], state=Form.anonymous_message)
async def process_anonymous_sticker(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data_obj = FormData(**data)
        recipient_id = data_obj.recipient_id
    sticker_id = message.sticker.file_id

    conn = await get_connection()
    async with conn.cursor() as cursor:
        await cursor.execute("INSERT INTO anonymous_messages (sender_id, recipient_id, message) VALUES (?, ?, ?)", (message.from_user.id, recipient_id, sticker_id))
    await conn.commit()

    reply_markup = InlineKeyboardMarkup()
    reply_button = InlineKeyboardButton("✏ Ответить", callback_data=f"reply:{message.from_user.id}")
    reply_markup.add(reply_button)

    sticker_message = await bot.send_sticker(chat_id=recipient_id, sticker=message.sticker.file_id)
    await bot.send_message(chat_id=recipient_id, text="<b>🔔 У тебя новое сообщение!</b>\n\n", reply_markup=reply_markup, reply_to_message_id=sticker_message.message_id, parse_mode="HTML")

    again_markup = InlineKeyboardMarkup()
    again_button = InlineKeyboardButton("📨 Написать ещё", callback_data=f"send_again:{recipient_id}")
    again_markup.add(again_button)

    await bot.send_message(message.from_user.id, "Сообщение отправлено, ожидайте ответ!", reply_markup=again_markup)
    await state.finish()

@dp.message_handler(content_types=['sticker'], state=Form.anonymous_reply)
async def process_anonymous_reply_sticker(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data_obj = FormData(**data)
        sender_id = data_obj.sender_id
    sticker_id = message.sticker.file_id

    conn = await get_connection()
    async with conn.cursor() as cursor:
        await cursor.execute("INSERT INTO anonymous_messages (sender_id, recipient_id, message) VALUES (?, ?, ?)", (message.from_user.id, sender_id, sticker_id))
    await conn.commit()

    reply_markup = InlineKeyboardMarkup()
    reply_button = InlineKeyboardButton("📨 Написать ещё", callback_data=f"send_again:{sender_id}")
    reply_markup.add(reply_button)

    await message.answer(f"Сообщение отправлено, ожидайте ответ!", reply_markup=reply_markup)

    reply_markup = InlineKeyboardMarkup()
    reply_button = InlineKeyboardButton("✏ Ответить", callback_data=f"reply:{message.from_user.id}")
    reply_markup.add(reply_button)

    sticker_message = await bot.send_sticker(chat_id=sender_id, sticker=sticker_id)
    await bot.send_message(chat_id=sender_id, text="<b>🔔 У тебя новое сообщение!</b>\n\n", reply_markup=reply_markup, reply_to_message_id=sticker_message.message_id, parse_mode="HTML")

    await state.finish()
