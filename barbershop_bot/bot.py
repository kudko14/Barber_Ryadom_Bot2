"""
Телеграм-бот для парикмахерской
Использует: aiogram 3.x, SQLite, FSM (машина состояний)
"""

import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

# ======================= НАСТРОЙКИ =======================
# ВСТАВЬ СЮДА СВОЙ ТОКЕН, который ты получил от @BotFather
BOT_TOKEN = "8914374111:AAFkP4xqowMK8pxNwVBy5kQb7kL17dt8xg"

# ID администратора (пока заглушка, потом замени на реальный ID своего Telegram)
# Чтобы узнать свой ID, напиши боту @userinfobot
ADMIN_ID = 8409381157 # ЗАМЕНИ НА РЕАЛЬНЫЙ ID!
# =========================================================

# --- Инициализация бота и диспетчера ---
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()  # Хранилище состояний в памяти
dp = Dispatcher(storage=storage)


# ======================= БАЗА ДАННЫХ (SQLite) =======================
def init_db():
    """Создаёт таблицу clients, если её ещё нет"""
    conn = sqlite3.connect('barbershop.db')  # Подключаемся к файлу базы данных
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()  # Сохраняем изменения
    conn.close()   # Закрываем соединение


def save_client(name: str, phone: str):
    """Сохраняет клиента в базу данных"""
    conn = sqlite3.connect('barbershop.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO clients (name, phone) VALUES (?, ?)', (name, phone))
    conn.commit()
    conn.close()


# ======================= КЛАВИАТУРЫ =======================
def get_main_keyboard():
    """Создаёт главную клавиатуру с двумя кнопками"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💰 Цены и услуги")],
            [KeyboardButton(text="✂️ Записаться")]
        ],
        resize_keyboard=True  # Автоматически подгонять размер кнопок
    )
    return keyboard


# ======================= FSM (МАШИНА СОСТОЯНИЙ) =======================
class BookingForm(StatesGroup):
    """Состояния для процесса записи"""
    waiting_for_name = State()   # Ждём имя клиента
    waiting_for_phone = State()  # Ждём телефон клиента


# ======================= ОБРАБОТЧИКИ КОМАНД =======================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    """Обработчик команды /start"""
    await message.answer(
        "👋 Добро пожаловать в нашу парикмахерскую!\n"
        "Выберите действие:",
        reply_markup=get_main_keyboard()  # Показываем главную клавиатуру
    )


@dp.message(F.text == "💰 Цены и услуги")
async def show_prices(message: types.Message):
    """Показывает прайс-лист"""
    prices_text = """
💇‍♂️ *НАШИ УСЛУГИ И ЦЕНЫ* 💇‍♀️

✂️ Стрижка мужская (модельная) — 1200 руб.
💆‍♀️ Стрижка женская (классика) — 1800 руб.
🎨 Окрашивание (тонирование) — 2500 руб.

💈 *Акция:* При первом визите скидка 10%!
    """
    await message.answer(prices_text, parse_mode="Markdown")


@dp.message(F.text == "✂️ Записаться")
async def start_booking(message: types.Message, state: FSMContext):
    """Начинает процесс записи (FSM)"""
    await state.set_state(BookingForm.waiting_for_name)  # Переключаем состояние
    await message.answer(
        "Давайте запишем вас! 📝\n\n"
        "Как я могу к вам обращаться? Напишите ваше имя:",
        reply_markup=ReplyKeyboardRemove()  # Убираем клавиатуру, чтобы не мешала
    )


# ======================= ОБРАБОТЧИКИ СОСТОЯНИЙ FSM =======================
@dp.message(BookingForm.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    """Получаем имя, сохраняем в состояние, спрашиваем телефон"""
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("Пожалуйста, введите настоящее имя (минимум 2 символа)")
        return

    # Сохраняем имя во временное хранилище состояния
    await state.update_data(name=name)
    # Переключаем состояние на ожидание телефона
    await state.set_state(BookingForm.waiting_for_phone)
    await message.answer(
        f"Отлично, {name}! 📞\n"
        "Теперь укажите ваш номер телефона для связи (например: +7 123 456-78-90):"
    )


@dp.message(BookingForm.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    """Получаем телефон, сохраняем всё в БД, уведомляем админа"""
    phone = message.text.strip()
    if len(phone) < 5:  # Простая проверка, что номер введён
        await message.answer("Пожалуйста, введите корректный номер телефона")
        return

    # Получаем ранее сохранённое имя из состояния
    user_data = await state.get_data()
    name = user_data.get("name")

    # 1. Сохраняем в базу данных
    save_client(name, phone)

    # 2. Отправляем сообщение клиенту
    await message.answer(
        f"✅ Спасибо, {name}! Вы успешно записаны.\n"
        f"Мы перезвоним вам по номеру {phone} в ближайшее время.\n"
        "Ждём вас в нашей парикмахерской! ✨",
        reply_markup=get_main_keyboard()  # Возвращаем главную клавиатуру
    )

    # 3. Уведомляем администратора (заглушка с реальным ADMIN_ID)
    admin_notification = (
        f"📢 *НОВАЯ ЗАПИСЬ!*\n\n"
        f"👤 Имя: {name}\n"
        f"📞 Телефон: {phone}"
    )
    try:
        await bot.send_message(ADMIN_ID, admin_notification, parse_mode="Markdown")
    except Exception as e:
        # Если не удалось отправить админу (например, неправильный ID), просто печатаем ошибку в консоль
        print(f"Не удалось отправить сообщение админу: {e}")

    # Завершаем машину состояний (очищаем состояние)
    await state.clear()


# ======================= ЗАПУСК БОТА =======================
async def main():
    """Главная функция запуска бота"""
    # Инициализируем базу данных (создаём таблицу, если её нет)
    init_db()
    print("✅ Бот запущен и готов к работе!")

    # Запускаем polling (постоянный опрос обновлений от Telegram)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())