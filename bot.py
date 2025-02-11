""" Логика работы бота """

import logging
from database.methods import (get_user,
                              create_user,
                              create_user_tamagochi,
                              get_user_tamagochi,
                              get_types_pet,
                              rename,
                              get_all_foods)

from database.pet_condition_update import feed_pet
import utilites
from database import pet_condition_update
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


def check_user_registered(func):
    """ Проверяет пользователя на наличие в базе, если его нет, то создает """

    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = await get_user(update.effective_user)
        if user is None:
            await create_user(update.effective_user)
            logging.info(f'Был создан профиль пользователя {update.effective_user.id}')
        return await func(update, context)
    return wrapper


def check_pet_exists(func):
    """ Проверяет есть ли у пользователя питомец """

    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        pet = await get_user_tamagochi(update.effective_user)
        if pet is None:
            await update.message.reply_text('У вас нет питомца')
            logging.info(f'Запрос к питомцу от пользователя {update.effective_user.id}, который его не имеет')
        else:
            return await func(update, context)
    return wrapper


@check_user_registered
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ /start """

    user_pet = await get_user_tamagochi(update.effective_user)
    if user_pet:
        answer = (f'Привет! Я соскучился\n'
                  f'Вот как ты можешь со мной взаимодействовать:\n'
                  f'1. Кормить меня - /feed 🍽️\n'
                  f'2. Играть со мной - /play 🎾\n'
                  f'3. Укладывать спать - /sleep 💤\n'
                  f'4. Лечить меня, если я заболею - /heal 💊\n'
                  f'5. Поменять мне имя - /rename ✏️\n'
                  f'6. Узнать как я себя чувствую - /check ❤️\n'
                  f'Я с нетерпением жду, чтобы провести время с тобой!')
        await update.message.reply_text(answer)
    else:
        await update.message.reply_text('Привет! Используйте команду /create_pet для создания питомца.')
    logging.info(f'Пользователь {update.effective_user.id} /start')


@check_user_registered
async def create_pet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ /create_pet.
        Инициализация создания питомца.
        Пользователю предлагается на выбор тип питомца
    """

    user_pet = await get_user_tamagochi(update.effective_user)
    if user_pet:
        await update.message.reply_text(f'Хей, у тебя уже есть я, {user_pet.name}')
    else:
        type_pets = await get_types_pet()
        keyboard = []
        for type_pet in type_pets:
            keyboard.append([InlineKeyboardButton(type_pet, callback_data=f'pet_{type_pet}')])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text('Выберите питомца:', reply_markup=reply_markup)
        logging.info(f'Пользователь {update.effective_user.id} инициировал создание питомца')


async def choose_pet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ Сохранение выбора типа питомца.
        Удаляет варианты выбора из диалога.
        Запускает ожидание ввода имени в context
    """

    pet = await get_user_tamagochi(update.effective_user)
    if pet is not None:
        await update.message.reply_text(f'Хей, у тебя уже есть я, {pet.name}')
    else:
        query = update.callback_query
        await query.answer()
        await query.edit_message_reply_markup(reply_markup=None)

        pet_type = query.data.split('_')[1]
        context.user_data['pet_type'] = pet_type

        await query.message.reply_text('Выберите имя для вашего питомца:')

        logging.info(f'Пользователь {update.effective_user.id} создал питомца {pet_type}')

    context.user_data['waiting_for_name'] = True


@check_user_registered
async def rename_pet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Как ты меня хочешь назвать?')
    context.user_data['rename'] = True


@check_pet_exists
async def feed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ /feed """
    # await pet_condition_update.feed(update.effective_user, 'Овощной салат')
    foods = await get_all_foods()
    keyboard = []
    for food in foods:
        keyboard.append([InlineKeyboardButton(food, callback_data=f'food_{food}')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Чем ты меня покормишь?', reply_markup=reply_markup)


async def choose_food(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ Сохранение выбора еды.
        Удаляет варианты ответа из диалога.
        Запускает обновление характеристик питомца
    """

    query = update.callback_query
    await query.answer()
    await query.edit_message_reply_markup(reply_markup=None)

    my_food = query.data.split('_')[1]
    user_pet = await feed_pet(update.effective_user, my_food)
    answer = (f'Я себя чувствую вот так:\n'
              f'Здоровье: {user_pet["health"]}\n'
              f'Настроение: {user_pet["happiness"]}\n'
              f'Чистота: {user_pet["grooming"]}\n'
              f'Энергия: {user_pet["energy"]}\n'
              f'Голод: {user_pet["hunger"]}\n'
              )
    if user_pet['sick']:
        answer += 'Я заболел('
    else:
        answer += 'Я здоров)'
    await query.message.reply_text(answer)

    logging.info(f'Пользователь {update.effective_user.id} покормил питомца')


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

    await create_user_tamagochi(update.effective_user.id,
                                pet_name,
                                pet_type)
    answer = (f'Привет! Я твой новый питомец {pet_type} по имени {pet_name} 🐾\n!'
              f'Вот как ты можешь со мной взаимодействовать:\n'
              f'1. Кормить меня - /feed 🍽️\n'
              f'2. Играть со мной - /play 🎾\n'
              f'3. Укладывать спать - /sleep 💤\n'
              f'4. Лечить меня, если я заболею - /heal 💊\n'
              f'5. Поменять мне имя - /rename ✏️\n'
              f'6. Узнать как я себя чувствую - /check ❤️\n'
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
    await rename(update.effective_user, new_name)
    await update.message.reply_text(f'Теперь меня зовут {new_name}')
    del context.user_data['rename']
    logging.info(f'Пользователь {update.effective_user.id} переименовал питомца')


@check_pet_exists
async def check_pet_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """ Выдает состояние питомца """

    pet = await get_user_tamagochi(update.effective_user)
    answer = (f'Я себя чувствую вот так:\n'
              f'Здоровье: {pet.health}\n'
              f'Настроение: {pet.happiness}\n'
              f'Чистота: {pet.grooming}\n'
              f'Энергия: {pet.energy}\n'
              f'Голод: {pet.hunger}\n'
              )
    if pet.sick:
        answer += 'Я заболел('
    else:
        answer += 'Я здоров)'
    await update.message.reply_text(answer)
    logging.info(f'Пользователь {update.effective_user.id} проверил состояние питомца')


def main():
    application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('create_pet', create_pet))
    application.add_handler(CommandHandler('rename', rename_pet))
    application.add_handler(CommandHandler('feed', feed))
    application.add_handler(CommandHandler('check', check_pet_stats))
    application.add_handler(CallbackQueryHandler(choose_pet, pattern=r'pet_.*$'))
    application.add_handler(CallbackQueryHandler(choose_food, pattern=r'food_.*$'))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, process_user_message))

    application.run_polling()


# Запуск бота из проекта
if __name__ == '__main__':
    main()
