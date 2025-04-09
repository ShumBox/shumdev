import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler, CallbackContext
import sqlite3
import re

# Включаем логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Константы для состояний диалога
TYPE_SHOP, SHOP_NAME, SHOP_ADDRESS, DELIVERY_ITEMS, DELIVERY_TIME, PHONE_NUMBER, DELIVERY_ADDRESS = range(7)

# ID администратора (заменено на ваш ID)
ADMIN_ID = 5977892192

# Словарь для временного хранения данных о заказах
user_data = {}

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type TEXT,
            shop_name TEXT,
            shop_address TEXT,
            items TEXT,
            delivery_time TEXT,
            phone TEXT,
            delivery_address TEXT,
            status TEXT DEFAULT 'Новый'
        )
    ''')
    conn.commit()
    conn.close()

# Сохранение заказа в базу данных
def save_order(user_id, data):
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute('''
        INSERT INTO orders (user_id, type, shop_name, shop_address, items, delivery_time, phone, delivery_address)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, data['type'], data['shop_name'], data['shop_address'], data['items'], data['time'], data['phone'], data['address']))
    conn.commit()
    conn.close()

# Отправка уведомления администратору
def notify_admin(update: Update, data):
    admin_message = (
        f"Новый заказ!\n"
        f"Пользователь: {update.message.from_user.first_name} ({update.message.from_user.id})\n"
        f"Тип магазина: {data['type']}\n"
        f"Название магазина: {data['shop_name']}\n"
        f"Адрес магазина: {data['shop_address']}\n"
        f"Товары/услуги: {data['items']}\n"
        f"Время доставки: {data['time']}\n"
        f"Номер телефона: {data['phone']}\n"
        f"Адрес доставки: {data['address']}"
    )
    update.bot.send_message(chat_id=ADMIN_ID, text=admin_message)

# Начало работы с ботом
def start(update: Update, context: CallbackContext) -> int:
    reply_keyboard = [['Продуктовый магазин', 'Строительный магазин'],
                      ['Аптека', 'Другое']]
    update.message.reply_text(
        "Добро пожаловать в сервис доставки 'Доставка в Шумерле'!\n"
        "Выберите тип магазина:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return TYPE_SHOP

# Обработка выбора типа магазина
def choose_shop_type(update: Update, context: CallbackContext) -> int:
    user_data['type'] = update.message.text
    update.message.reply_text("Введите название магазина:")
    return SHOP_NAME

# Обработка названия магазина
def enter_shop_name(update: Update, context: CallbackContext) -> int:
    user_data['shop_name'] = update.message.text
    update.message.reply_text("Введите адрес магазина:")
    return SHOP_ADDRESS

# Обработка адреса магазина
def enter_shop_address(update: Update, context: CallbackContext) -> int:
    user_data['shop_address'] = update.message.text
    update.message.reply_text("Опишите товары или услуги, которые нужно доставить:")
    return DELIVERY_ITEMS

# Обработка списка товаров/услуг
def enter_delivery_items(update: Update, context: CallbackContext) -> int:
    user_data['items'] = update.message.text
    update.message.reply_text("Укажите желаемое время доставки (например, 14:00):")
    return DELIVERY_TIME

# Проверка корректности номера телефона
def validate_phone(phone):
    pattern = r'^\+?[78]\d{10}$'
    return bool(re.match(pattern, phone))

# Обработка времени доставки
def enter_delivery_time(update: Update, context: CallbackContext) -> int:
    user_data['time'] = update.message.text
    update.message.reply_text("Введите ваш номер телефона (например, +79991234567):")
    return PHONE_NUMBER

# Обработка номера телефона
def enter_phone_number(update: Update, context: CallbackContext) -> int:
    phone = update.message.text
    if not validate_phone(phone):
        update.message.reply_text("Неверный формат номера телефона. Пожалуйста, введите заново (например, +79991234567):")
        return PHONE_NUMBER
    user_data['phone'] = phone
    update.message.reply_text("Введите адрес доставки:")
    return DELIVERY_ADDRESS

# Обработка адреса доставки
def enter_delivery_address(update: Update, context: CallbackContext) -> int:
    user_data['address'] = update.message.text

    # Сохранение заказа в базу данных
    save_order(update.message.from_user.id, user_data)

    # Отправка уведомления администратору
    notify_admin(update, user_data)

    # Подтверждение заказа пользователю
    order_summary = (
        f"Ваш заказ:\n"
        f"Тип магазина: {user_data['type']}\n"
        f"Название магазина: {user_data['shop_name']}\n"
        f"Адрес магазина: {user_data['shop_address']}\n"
        f"Товары/услуги: {user_data['items']}\n"
        f"Время доставки: {user_data['time']}\n"
        f"Номер телефона: {user_data['phone']}\n"
        f"Адрес доставки: {user_data['address']}"
    )
    update.message.reply_text(order_summary)
    update.message.reply_text("Заказ успешно создан! Для создания нового заказа нажмите /start.")

    # Очистка данных после завершения заказа
    user_data.clear()
    return ConversationHandler.END

# Отмена заказа
def cancel(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("Создание заказа отменено. Для начала заново нажмите /start.")
    return ConversationHandler.END

# Команда для просмотра истории заказов
def history(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    conn = sqlite3.connect('orders.db')
    c = conn.cursor()
    c.execute('SELECT * FROM orders WHERE user_id = ?', (user_id,))
    orders = c.fetchall()
    conn.close()

    if not orders:
        update.message.reply_text("У вас нет истории заказов.")
        return

    response = "Ваша история заказов:\n"
    for order in orders:
        response += (
            f"Заказ #{order[0]}:\n"
            f"Тип магазина: {order[2]}\n"
            f"Статус: {order[9]}\n\n"
        )

    update.message.reply_text(response)

# Главная функция
def main():
    TOKEN = "8009876547:AAF_ZkS79GCIXNhOyWXvoO5CaPo_dftDlps"  # Ваш токен бота
    updater = Updater(TOKEN)

    dispatcher = updater.dispatcher

    # Инициализация базы данных
    init_db()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            TYPE_SHOP: [MessageHandler(Filters.text & ~Filters.command, choose_shop_type)],
            SHOP_NAME: [MessageHandler(Filters.text & ~Filters.command, enter_shop_name)],
            SHOP_ADDRESS: [MessageHandler(Filters.text & ~Filters.command, enter_shop_address)],
            DELIVERY_ITEMS: [MessageHandler(Filters.text & ~Filters.command, enter_delivery_items)],
            DELIVERY_TIME: [MessageHandler(Filters.text & ~Filters.command, enter_delivery_time)],
            PHONE_NUMBER: [MessageHandler(Filters.text & ~Filters.command, enter_phone_number)],
            DELIVERY_ADDRESS: [MessageHandler(Filters.text & ~Filters.command, enter_delivery_address)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(CommandHandler("history", history))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
