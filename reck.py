import aiogram
from aiogram import Bot, types
from typing import List
import aiosqlite

# Список ID чатов для физического добавления (можете изменять этот список)
MANUAL_CHAT_IDS = [123456789, 960990229]  # Замените на реальные ID чатов

async def export_ids_to_file(file_name: str = 'chat_ids.txt') -> None:
    """Извлекает ID пользователей из базы данных и сохраняет их в текстовый файл."""
    conn = await get_connection()
    try:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT id FROM users")
            chat_ids = [str(row[0]) for row in await cursor.fetchall()]

        with open(file_name, 'w') as f:
            f.write('\n'.join(chat_ids))
        print(f"ID пользователей экспортированы в файл {file_name}")

    except Exception as e:
        print(f"Ошибка при экспорте ID: {e}")
    finally:
        await conn.close()

async def send_rek_from_file(bot, file_name: str = 'chat_ids.txt') -> None:
    """Отправляет рекламное сообщение пользователям, чьи ID хранятся в текстовом файле."""
    try:
        with open(file_name, 'r') as f:
            chat_ids = [int(line.strip()) for line in f]

        for chat_id in chat_ids:
            try:
                await bot.send_message(chat_id, "Привет Мир!")
                print(f"Реклама отправлена в чат {chat_id}")
            except Exception as e:
                print(f"Ошибка отправки рекламы в чат {chat_id}: {e}")

    except FileNotFoundError:
        print(f"Файл {file_name} не найден.")
    except Exception as e:
        print(f"Ошибка при отправке рекламы: {e}")