import re
from aiogram import types
from aiogram.dispatcher import FSMContext
import aiosqlite
import random
import string

# Путь к базе данных
DATABASE = 'database.db'

# Генерация уникального ID
def generate_anonymous_id():
    random_part = ''.join(random.choices(string.ascii_letters + string.digits, k=10))
    return f"_{random_part}"

# проверка ника на валидность
def is_valid_nick(nick):
    pattern = r"^[a-zA-Z0-9_]+$"
    if 7 <= len(nick) <= 30 and re.match(pattern, nick):
        return True
    return False

# подключение к базе данных
async def get_connection():
    return await aiosqlite.connect(DATABASE)

# сохранение ника в базу данных
async def save_nick(user_id, nick):
    conn = await get_connection()
    async with conn.cursor() as cursor:
        await cursor.execute("UPDATE users SET anonymous_id = ? WHERE id = ?", (nick, user_id))
    await conn.commit()
    await conn.close()

# получение ника из базы данных
async def get_nick(user_id):
    conn = await get_connection()
    async with conn.cursor() as cursor:
        await cursor.execute("SELECT anonymous_id FROM users WHERE id = ?", (user_id,))
        result = await cursor.fetchone()
    await conn.close()
    return result[0] if result else None

# обработчик команды /nick
async def cmd_nick(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    new_nick = message.get_args()

    if new_nick:
        if is_valid_nick(new_nick):
            await save_nick(user_id, new_nick)
            # создаем новую клавиатуру с кнопкой "Поделиться ссылкой"
            markup = types.InlineKeyboardMarkup()
            share_button = types.InlineKeyboardButton(
                "🔗 Поделиться ссылкой",
                url=f"https://t.me/share/url?url=%D0%97%D0%B0%D0%B4%D0%B0%D0%B9%20%D0%BC%D0%BD%D0%B5%20%D0%B0%D0%BD%D0%BE%D0%BD%D0%B8%D0%BC%D0%BD%D1%8B%D0%B9%20%D0%B2%D0%BE%D0%BF%D1%80%D0%BE%D1%81%0A%F0%9F%91%89%20http://t.me/Ietsqbot?start={new_nick}"
            )
            markup.add(share_button)

            await message.answer(
                "<i>Готово! ✅</i>\n\n"
                "<i>Твоя новая ссылка:</i>\n"
                f"🔗 <code><a href='t.me/Ietsqbot?start={new_nick}'>t.me/Ietsqbot?start={new_nick}</a>\n\n</code>"
                "<i>Чтобы скопировать ссылку, просто кликни на неё. Затем размести в Instagram или других соц. сетях</i>",
                disable_web_page_preview=True,
                parse_mode="HTML",
                reply_markup=markup
            )
        else:
            await message.answer(
                "<b>📛 Неверный формат ника.</b>\n\n"
                "<i>Ник должен содержать только латинские буквы, цифры и знак подчеркивания, "
                "а также иметь длину от 7 до 30 символов.</i>\n\n"
                "<i>Например:</i> `<code>/nick MrDurov</code>` <i>или</i> `<code>/nick Alexandr</code>`",
                disable_web_page_preview=True,
                parse_mode="HTML"
            )
    else:
        current_nick = await get_nick(user_id)
        # Создаем кнопку "Сбросить"
        reset_button = types.InlineKeyboardButton("🔄 Сбросить ссылку", callback_data="reset_nick")
        markup = types.InlineKeyboardMarkup().add(reset_button)

        await message.answer(
            f"<i>Сейчас ваша ссылка для получения анонимных сообщений выглядит так:</i> <code>t.me/Ietsqbot?start={current_nick}</code>\n\n"
            "<i>Чтобы изменить ссылку, напишите</i> <code>/nick [text]</code>, <i>например</i> <code>/nick MrDurov</code>\n\n"
            "<i> ❗ Обратите внимание, что при смене ссылки, старая ссылка перестанет быть активной!</i>",
            disable_web_page_preview=True,
            parse_mode="HTML",
            reply_markup=markup
        )

# Обработчик нажатия на кнопку "Сбросить"
async def reset_nick_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    new_nick = generate_anonymous_id()
    await save_nick(user_id, new_nick)

    await callback_query.answer("Ссылка успешно сброшена!", show_alert=True)

    # Обновляем сообщение с новой ссылкой и полным текстом
    await callback_query.message.edit_text(
        f"<i>Сейчас ваша ссылка для получения анонимных сообщений выглядит так:</i> <code>t.me/Ietsqbot?start={new_nick}</code>\n\n"
        "<i>Чтобы изменить ссылку, напишите</i> <code>/nick [text]</code>, <i>например</i> <code>/nick MrDurov</code>\n\n"
        "<i> ❗ Обратите внимание, что при смене ссылки, старая ссылка перестанет быть активной!</i>",
        disable_web_page_preview=True,
        parse_mode="HTML",
        reply_markup=callback_query.message.reply_markup  # Сохраняем кнопку
    )