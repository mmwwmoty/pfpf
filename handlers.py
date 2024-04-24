from aiogram import types
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from main import dp, bot, Form, get_connection  # Импортируем функцию connect_to_database из main.py

@dp.callback_query_handler(state='*')
async def process_callback_reply(callback_query: types.CallbackQuery, state: FSMContext):
    sender_id = int(callback_query.data)  # Получаем идентификатор пользователя из callback_data
    await state.update_data(sender_id=sender_id)  # Сохраняем sender_id в состоянии
    markup = InlineKeyboardMarkup()
    cancel_button = InlineKeyboardButton("✖️ Отменить", callback_data="cancel")
    markup.add(cancel_button)
    await bot.send_message(callback_query.from_user.id, "🚀 Здесь можно отправить <b>анонимное сообщение</b> человеку, который опубликовал эту ссылку\n\n🖊 <b>Напишите сюда всё, что хотите ему передать</b>, и через несколько секунд он получит ваше сообщение, но не будет знать от кого\n\nОтправить можно фото, видео, 💬 текст, 🔊 голосовые, 📷видеосообщения (кружки), а также ✨ стикеры", parse_mode="HTML", reply_markup=markup)
    await Form.anonymous_reply.set()

@dp.message_handler(content_types=['photo'], state=Form.anonymous_message)
async def process_anonymous_photo(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        recipient_id = data['recipient_id']
    photo_id = message.photo[-1].file_id  # Получаем идентификатор файла фотографии

    conn = await get_connection()  # Создаем соединение с базой данных
    async with conn.cursor() as cursor:  # Создаем курсор
        await cursor.execute("INSERT INTO anonymous_messages (sender_id, recipient_id, message) VALUES (?, ?, ?)", (message.from_user.id, recipient_id, photo_id))  # Выполняем SQL-запрос
    await conn.commit()  # Сохраняем изменения
    
    # Создаем кнопку "Ответить"
    reply_markup = InlineKeyboardMarkup()
    reply_button = InlineKeyboardButton("✏ Ответить", callback_data=str(message.from_user.id))
    reply_markup.add(reply_button)
    
    # Отправляем фото с кнопкой "Ответить" получателю
    await bot.send_photo(chat_id=recipient_id, photo=message.photo[-1].file_id, caption="<b>🔔 У тебя новое сообщение!</b>\n\n", reply_markup=reply_markup, parse_mode="HTML")
    
    # Создаем кнопку "Написать еще" и отправляем сообщение пользователю
    again_markup = InlineKeyboardMarkup()
    again_button = InlineKeyboardButton("📨 Написать ещё", callback_data="send_again")
    again_markup.add(again_button)
    
    await bot.send_message(message.from_user.id, "Сообщение отправлено, ожидайте ответ!", reply_markup=again_markup)
    await state.finish()

@dp.message_handler(content_types=['photo'], state=Form.anonymous_reply)
async def process_anonymous_reply_photo(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        sender_id = data.get('sender_id')  # Получаем sender_id из данных
    photo_id = message.photo[-1].file_id  # Получаем идентификатор файла фотографии

    conn = await get_connection()  # Создаем соединение с базой данных
    async with conn.cursor() as cursor:  # Создаем курсор
        await cursor.execute("INSERT INTO anonymous_messages (sender_id, recipient_id, message) VALUES (?, ?, ?)", (message.from_user.id, sender_id, photo_id))  # Выполняем SQL-запрос
    await conn.commit()  # Сохраняем изменения
    
    # Создаем кнопку "Написать еще" и отправляем сообщение отправителю
    reply_markup = InlineKeyboardMarkup()
    reply_button = InlineKeyboardButton("📨 Написать ещё", callback_data="send_again")
    reply_markup.add(reply_button)
    
    await message.answer(f"Сообщение отправлено, ожидайте ответ!", reply_markup=reply_markup)
    
    # Создаем кнопку "Ответить" и отправляем сообщение получателю
    reply_markup = InlineKeyboardMarkup()
    reply_button = InlineKeyboardButton("✏ Ответить", callback_data="reply")
    reply_markup.add(reply_button)
    
    await bot.send_photo(sender_id, photo_id, caption="<b>🔔 У тебя новое сообщение!</b>\n\n", reply_markup=reply_markup, parse_mode="HTML")
    await state.finish()

@dp.message_handler(content_types=['video'], state=Form.anonymous_message)
async def process_anonymous_video(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        recipient_id = data['recipient_id']
    video_id = message.video.file_id  # Получаем идентификатор файла видео

    conn = await get_connection()  # Создаем соединение с базой данных
    async with conn.cursor() as cursor:  # Создаем курсор
        await cursor.execute("INSERT INTO anonymous_messages (sender_id, recipient_id, message) VALUES (?, ?, ?)", (message.from_user.id, recipient_id, video_id))  # Выполняем SQL-запрос
    await conn.commit()  # Сохраняем изменения
    
    reply_markup = InlineKeyboardMarkup()
    reply_button = InlineKeyboardButton("✏ Ответить", callback_data=str(message.from_user.id))
    reply_markup.add(reply_button)
    
    await bot.send_video(chat_id=recipient_id, video=message.video.file_id, caption="<b>🔔 У тебя новое сообщение!</b>\n\n", reply_markup=reply_markup, parse_mode="HTML")
    
    again_markup = InlineKeyboardMarkup()
    again_button = InlineKeyboardButton("📨 Написать ещё", callback_data="send_again")
    again_markup.add(again_button)
    
    await bot.send_message(message.from_user.id, "Сообщение отправлено, ожидайте ответ!", reply_markup=again_markup)
    await state.finish()

@dp.message_handler(content_types=['video'], state=Form.anonymous_reply)
async def process_anonymous_reply_video(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        sender_id = data.get('sender_id')  # Получаем sender_id из данных
    video_id = message.video.file_id  # Получаем идентификатор файла видео

    conn = await get_connection()  # Создаем соединение с базой данных
    async with conn.cursor() as cursor:  # Создаем курсор
        await cursor.execute("INSERT INTO anonymous_messages (sender_id, recipient_id, message) VALUES (?, ?, ?)", (message.from_user.id, sender_id, video_id))  # Выполняем SQL-запрос
    await conn.commit()  # Сохраняем изменения
    
    reply_markup = InlineKeyboardMarkup()
    reply_button = InlineKeyboardButton("📨 Написать ещё", callback_data="send_again")
    reply_markup.add(reply_button)
    
    await message.answer(f"Сообщение отправлено, ожидайте ответ!", reply_markup=reply_markup)
    
    reply_markup = InlineKeyboardMarkup()
    reply_button = InlineKeyboardButton("✏ Ответить", callback_data="reply")
    reply_markup.add(reply_button)
    
    await bot.send_video(sender_id, video_id, caption="<b>🔔 У тебя новое сообщение!</b>\n\n", reply_markup=reply_markup, parse_mode="HTML")
    await state.finish()

@dp.message_handler(content_types=['voice'], state=Form.anonymous_message)
async def process_anonymous_voice(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        recipient_id = data['recipient_id']
    voice_id = message.voice.file_id  # Получаем идентификатор файла голосового сообщения

    conn = await get_connection()  # Создаем соединение с базой данных
    async with conn.cursor() as cursor:  # Создаем курсор
        await cursor.execute("INSERT INTO anonymous_messages (sender_id, recipient_id, message) VALUES (?, ?, ?)", (message.from_user.id, recipient_id, voice_id))  # Выполняем SQL-запрос
    await conn.commit()  # Сохраняем изменения
    
    # Создаем кнопку "Ответить"
    reply_markup = InlineKeyboardMarkup()
    reply_button = InlineKeyboardButton("✏ Ответить", callback_data=str(message.from_user.id))
    reply_markup.add(reply_button)
    
    # Отправляем голосовое сообщение с кнопкой "Ответить" получателю
    await bot.send_voice(chat_id=recipient_id, voice=message.voice.file_id, caption="<b>🔔 У тебя новое сообщение!</b>\n\n", reply_markup=reply_markup, parse_mode="HTML")
    
    # Создаем кнопку "Написать еще" и отправляем сообщение пользователю
    again_markup = InlineKeyboardMarkup()
    again_button = InlineKeyboardButton("📨 Написать ещё", callback_data="send_again")
    again_markup.add(again_button)
    
    await bot.send_message(message.from_user.id, "Сообщение отправлено, ожидайте ответ!", reply_markup=again_markup)
    await state.finish()

@dp.message_handler(content_types=['voice'], state=Form.anonymous_reply)
async def process_anonymous_reply_voice(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        sender_id = data.get('sender_id')  # Получаем sender_id из данных
    voice_id = message.voice.file_id  # Получаем идентификатор файла голосового сообщения

    conn = await get_connection()  # Создаем соединение с базой данных
    async with conn.cursor() as cursor:  # Создаем курсор
        await cursor.execute("INSERT INTO anonymous_messages (sender_id, recipient_id, message) VALUES (?, ?, ?)", (message.from_user.id, sender_id, voice_id))  # Выполняем SQL-запрос
    await conn.commit()  # Сохраняем изменения
    
    # Создаем кнопку "Написать еще" и отправляем сообщение отправителю
    reply_markup = InlineKeyboardMarkup()
    reply_button = InlineKeyboardButton("📨 Написать ещё", callback_data="send_again")
    reply_markup.add(reply_button)
    
    await message.answer(f"Сообщение отправлено, ожидайте ответ!", reply_markup=reply_markup)
    
    # Создаем кнопку "Ответить" и отправляем сообщение получателю
    reply_markup = InlineKeyboardMarkup()
    reply_button = InlineKeyboardButton("✏ Ответить", callback_data="reply")
    reply_markup.add(reply_button)
    
    await bot.send_voice(sender_id, voice_id, caption="<b>🔔 У тебя новое сообщение!</b>\n\n", reply_markup=reply_markup, parse_mode="HTML")
    await state.finish()

@dp.message_handler(content_types=['video_note'], state=Form.anonymous_message)
async def process_anonymous_video_note(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        recipient_id = data['recipient_id']
    video_note_id = message.video_note.file_id  # Получаем идентификатор файла видеокружочка

    conn = await get_connection()  # Создаем соединение с базой данных
    async with conn.cursor() as cursor:  # Создаем курсор
        await cursor.execute("INSERT INTO anonymous_messages (sender_id, recipient_id, message) VALUES (?, ?, ?)", (message.from_user.id, recipient_id, video_note_id))  # Выполняем SQL-запрос
    await conn.commit()  # Сохраняем изменения

    # Отправляем видеокружочек получателю
    video_note_message = await bot.send_video_note(chat_id=recipient_id, video_note=video_note_id)
    
    # Создаем кнопку "Ответить"
    reply_markup = InlineKeyboardMarkup()
    reply_button = InlineKeyboardButton("✏ Ответить", callback_data=str(message.from_user.id))
    reply_markup.add(reply_button)
    
    # Отправляем сообщение "У тебя новое сообщение!" с кнопкой "Ответить", отвечая на сообщение со стикером
    await bot.send_message(chat_id=recipient_id, text="<b>🔔 У тебя новое сообщение!</b>\n\n", reply_markup=reply_markup, reply_to_message_id=video_note_message.message_id, parse_mode="HTML")
    
    # Создаем кнопку "Написать еще" и отправляем сообщение пользователю
    again_markup = InlineKeyboardMarkup()
    again_button = InlineKeyboardButton("📨 Написать ещё", callback_data="send_again")
    again_markup.add(again_button)
    
    await bot.send_message(message.from_user.id, "Сообщение отправлено, ожидайте ответ!", reply_markup=again_markup)
    await state.finish()

@dp.message_handler(content_types=['video_note'], state=Form.anonymous_reply)
async def process_anonymous_reply_video_note(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        sender_id = data.get('sender_id')  # Получаем sender_id из данных
    video_note_id = message.video_note.file_id  # Получаем идентификатор файла видеокружочка

    conn = await get_connection()  # Создаем соединение с базой данных
    async with conn.cursor() as cursor:  # Создаем курсор
        await cursor.execute("INSERT INTO anonymous_messages (sender_id, recipient_id, message) VALUES (?, ?, ?)", (message.from_user.id, sender_id, video_note_id))  # Выполняем SQL-запрос
    await conn.commit()  # Сохраняем изменения

    # Создаем кнопку "Написать еще" и отправляем сообщение отправителю
    again_markup = InlineKeyboardMarkup()
    again_button = InlineKeyboardButton("📨 Написать ещё", callback_data="send_again")
    again_markup.add(again_button)
    
    await message.answer(f"Сообщение отправлено, ожидайте ответ!", reply_markup=again_markup)
    
    # Создаем кнопку "Ответить" и отправляем видеокружочек получателю
    reply_markup = InlineKeyboardMarkup()
    reply_button = InlineKeyboardButton("✏ Ответить", callback_data=str(message.from_user.id))
    reply_markup.add(reply_button)
    
    video_note_message = await bot.send_video_note(chat_id=sender_id, video_note=video_note_id)
    
    # Отправляем сообщение "У тебя новое сообщение!" с кнопкой "Ответить", отвечая на сообщение со стикером
    await bot.send_message(chat_id=sender_id, text="<b>🔔 У тебя новое сообщение!</b>\n\n", reply_markup=reply_markup, reply_to_message_id=video_note_message.message_id, parse_mode="HTML")
    
    await state.finish()


@dp.message_handler(content_types=['sticker'], state=Form.anonymous_message)
async def process_anonymous_sticker(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        recipient_id = data['recipient_id']
    sticker_id = message.sticker.file_id  # Получаем идентификатор файла стикера

    conn = await get_connection()  # Создаем соединение с базой данных
    async with conn.cursor() as cursor:  # Создаем курсор
        await cursor.execute("INSERT INTO anonymous_messages (sender_id, recipient_id, message) VALUES (?, ?, ?)", (message.from_user.id, recipient_id, sticker_id))  # Выполняем SQL-запрос
    await conn.commit()  # Сохраняем изменения
    
    # Отправляем стикер получателю
    sticker_message = await bot.send_sticker(chat_id=recipient_id, sticker=message.sticker.file_id)
    
    # Создаем кнопку "Ответить"
    reply_markup = InlineKeyboardMarkup()
    reply_button = InlineKeyboardButton("✏ Ответить", callback_data=str(message.from_user.id))
    reply_markup.add(reply_button)
    
    # Отправляем сообщение "У тебя новое сообщение!" с кнопкой "Ответить", отвечая на сообщение со стикером
    await bot.send_message(chat_id=recipient_id, text="<b>🔔 У тебя новое сообщение!</b>\n\n", reply_markup=reply_markup, reply_to_message_id=sticker_message.message_id, parse_mode="HTML")
    
    # Создаем кнопку "Написать еще" и отправляем сообщение пользователю
    again_markup = InlineKeyboardMarkup()
    again_button = InlineKeyboardButton("📨 Написать ещё", callback_data="send_again")
    again_markup.add(again_button)
    
    await bot.send_message(message.from_user.id, "Сообщение отправлено, ожидайте ответ!", reply_markup=again_markup)
    await state.finish()

@dp.message_handler(content_types=['sticker'], state=Form.anonymous_reply)
async def process_anonymous_reply_sticker(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        sender_id = data.get('sender_id')  # Получаем sender_id из данных
    sticker_id = message.sticker.file_id  # Получаем идентификатор файла стикера

    conn = await get_connection()  # Создаем соединение с базой данных
    async with conn.cursor() as cursor:  # Создаем курсор
        await cursor.execute("INSERT INTO anonymous_messages (sender_id, recipient_id, message) VALUES (?, ?, ?)", (message.from_user.id, sender_id, sticker_id))  # Выполняем SQL-запрос
    await conn.commit()  # Сохраняем изменения
    
    # Создаем кнопку "Написать еще" и отправляем сообщение отправителю
    again_markup = InlineKeyboardMarkup()
    again_button = InlineKeyboardButton("📨 Написать ещё", callback_data="send_again")
    again_markup.add(again_button)
    
    await message.answer(f"Сообщение отправлено, ожидайте ответ!", reply_markup=again_markup)
    
    # Создаем кнопку "Ответить" и отправляем стикер получателю
    reply_markup = InlineKeyboardMarkup()
    reply_button = InlineKeyboardButton("✏ Ответить", callback_data=str(message.from_user.id))
    reply_markup.add(reply_button)
    
    sticker_message = await bot.send_sticker(chat_id=sender_id, sticker=sticker_id)
    
    # Отправляем сообщение "У тебя новое сообщение!" с кнопкой "Ответить", отвечая на сообщение со стикером
    await bot.send_message(chat_id=sender_id, text="<b>🔔 У тебя новое сообщение!</b>\n\n", reply_markup=reply_markup, reply_to_message_id=sticker_message.message_id, parse_mode="HTML")

    await state.finish()
