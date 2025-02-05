""" Логика работы бота """

import logging
import database
import utilites
from configparser import ConfigParser
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ApplicationBuilder,
                          ContextTypes,
                          filters,
                          CommandHandler,
                          MessageHandler,
                          CallbackQueryHandler)


config = ConfigParser()
config.read('config.ini')
TELEGRAM_BOT_TOKEN = config['telegram']['bot_token']

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

httpx_logger = logging.getLogger("httpx")
httpx_logger.setLevel(logging.WARNING)


def ensure_user_registered(func):
    """ Проверяет пользователя на наличие в базе, если его нет, то создает """

    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = await database.get_user(update.effective_user)
        if user is None:
            await database.create_user(update.effective_user)
            logging.info(f'Был создан профиль пользователя {update.effective_user.id}')
        return await func(update, context)
    return wrapper


def check_pet_exists(func):
    """ Проверяет есть ли у пользователя питомец """

    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        pet = await database.get_user_tamagochi(update.effective_user)
        if pet is None:
            await update.message.reply_text('У вас нет питомца')
            logging.info(f'Запрос к питомцу от пользователя {update.effective_user.id}, который его не имеет')
        else:
            return await func(update, context)
    return wrapper


@ensure_user_registered
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ /start """

    user_pet = await database.get_user_tamagochi(update.effective_user)
    if user_pet:
        await update.message.reply_text('Привет! Я соскучился')
    else:
        await update.message.reply_text('Привет! Используйте команду /create_pet для создания питомца.')
    logging.info(f'Пользователь {update.effective_user.id} /start')


@ensure_user_registered
async def create_pet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ /create_pet.
        Инициализация создания питомца.
        Пользователю предлагается на выбор тип питомца
    """

    user_pet = await database.get_user_tamagochi(update.effective_user)
    if user_pet:
        await update.message.reply_text(f'Хей, у тебя уже есть я, {user_pet.name}')
    else:
        type_pets = await database.get_types_pet()
        keyboard = []
        for type_pet in type_pets:
            keyboard.append([InlineKeyboardButton(type_pet, callback_data=type_pet)])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text('Выберите питомца:', reply_markup=reply_markup)
        logging.info(f'Пользователь {update.effective_user.id} инициировал создание питомца')


async def choose_pet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ Сохранение выбора типа питомца.
        Сохраняет выбор типа питомца, удаляя варианты выбора из диалога.
        Запускает ожидание ввода имени в context
    """

    pet = await database.get_user_tamagochi(update.effective_user)
    if pet is not None:
        await update.message.reply_text(f'Хей, у тебя уже есть я, {pet.name}')
    else:
        query = update.callback_query
        await query.answer()
        await query.edit_message_reply_markup(reply_markup=None)

        pet_type = query.data
        context.user_data['pet_type'] = pet_type
        await query.message.reply_text('Выберите имя для вашего питомца:')
        logging.info(f'Пользователь {update.effective_user.id} создал питомца {pet_type}')

    context.user_data['waiting_for_name'] = True


@ensure_user_registered
async def rename(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Как ты меня хочешь назвать?')
    context.user_data['rename'] = True


async def process_user_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ Обработчик сообщений.
        Передает управление другим функциям в зависимости от контекста
        Если waiting_for_name = True, то ожидает ввода имени питомца
        Если rename = True, то ожидает ввода нового имени
    """

    if context.user_data.get('waiting_for_name'):
        await input_name(update, context)
    if context.user_data.get('rename'):
        await input_name_for_rename(update, context)


@utilites.validation_name
async def input_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ Ввод имени питомца при создании """

    pet_name = update.message.text
    pet_type = context.user_data.get('pet_type')
    context.user_data['pet_name'] = pet_name

    pet = await database.create_user_tamagochi(update.effective_user.id,
                                               pet_name,
                                               pet_type)
    answer = (f'Привет! Я твой новый питомец {pet_type} по имени {pet_name} 🐾\n!'
              f'Вот как ты можешь со мной взаимодействовать:\n'
              f'1. Кормить меня - /feed 🍽️\n'
              f'2. Играть со мной - /play 🎾\n'
              f'3. Укладывать спать - /sleep 💤\n'
              f'4. Лечить меня, если я заболею - /heal 💊\n'
              f'5. Поменять мне имя - /rename ✏️\n'
              f'Я с нетерпением жду, чтобы провести время с тобой!')
    await update.message.reply_text(answer)
    logging.info(f'Пользователь {update.effective_user.id} выбрал имя питомца {pet_name}')

    del context.user_data['pet_type']
    del context.user_data['pet_name']
    del context.user_data['waiting_for_name']


@utilites.validation_name
async def input_name_for_rename(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ Ввод имени питомца для изменения """

    new_name = update.message.text
    await database.rename(update.effective_user, new_name)
    await update.message.reply_text(f'Теперь меня зовут {new_name}')
    del context.user_data['rename']
    logging.info(f'Пользователь {update.effective_user.id} переименовал питомца')


def main():
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('create_pet', create_pet))
    application.add_handler(CommandHandler('rename', rename))
    application.add_handler(CallbackQueryHandler(choose_pet))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, process_user_message))

    application.run_polling()
