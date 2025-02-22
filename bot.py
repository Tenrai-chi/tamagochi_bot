""" Логика работы бота """

import asyncio
import logging
import os
from random import sample, choice

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ApplicationBuilder,
                          ContextTypes,
                          filters,
                          CommandHandler,
                          MessageHandler,
                          CallbackQueryHandler)

from database.methods import (get_user,
                              create_user,
                              create_user_tamagochi,
                              get_user_tamagochi,
                              get_types_pet,
                              rename,
                              get_all_foods,
                              update_user_last_request,
                              pet_is_sleep,
                              get_hiding_places,
                              check_is_sick)

from database.create_and_populate_db import initialize_database

from database.pet_condition_update import feed_pet, grooming_pet, therapy, sleep, play_hide_and_seek
from utilites import validation_name


load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv('bot_token')
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

httpx_logger = logging.getLogger("httpx")
httpx_logger.setLevel(logging.WARNING)


def check_user_registered(func):
    """ Декоратор.
        Проверяет пользователя на наличие в базе, если его нет, то создает
    """

    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = await get_user(update.effective_user)
        if user is None:
            await create_user(update.effective_user)
            logging.info(f'Был создан профиль пользователя {update.effective_user.id}')
        return await func(update, context)
    return wrapper


def check_pet_exists(func):
    """ Декоратор
        Проверяет есть ли у пользователя питомец
    """

    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        pet = await get_user_tamagochi(update.effective_user)
        if pet is None:
            await update.message.reply_text('У вас нет питомца')
            logging.info(f'Запрос к питомцу от пользователя {update.effective_user.id}, который его не имеет')
            return
        else:
            return await func(update, context)
    return wrapper


def check_pet_is_sleep(func):
    """ Декоратор
        Проверяет спит ли питомец на данный момент
    """

    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        is_sleep = await pet_is_sleep(update.effective_user)
        if is_sleep['sleep'] is True:
            await update.message.reply_text(is_sleep['reaction'])
            logging.info(f'Запрос к питомцу от пользователя {update.effective_user.id}, пока питомец спит')
        else:
            return await func(update, context)
    return wrapper


def check_pet_sick(func):
    """ Декоратор
        Проверяет болен ли питомец
    """

    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        is_sick = await check_is_sick(update.effective_user)
        if is_sick['sick'] is True:
            await update.message.reply_text(is_sick['reaction'])
            logging.info(f'Запрос к питомцу от пользователя {update.effective_user.id}, пока питомец болен')
        else:
            return await func(update, context)
    return wrapper


class PetBot:
    """ Telegram-бот """

    def __init__(self):
        self.application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
        self._register_handlers()

    def _register_handlers(self):
        self.application.add_handler(CommandHandler('start', self.start))
        self.application.add_handler(CommandHandler('create', self.create_pet))
        self.application.add_handler(CommandHandler('rename', self.rename_pet))
        self.application.add_handler(CommandHandler('feed', self.feed))
        self.application.add_handler(CommandHandler('sleep', self.sleep_pet))
        self.application.add_handler(CommandHandler('play', self.play_with_pet))
        self.application.add_handler(CommandHandler('therapy', self.therapy))
        self.application.add_handler(CommandHandler('grooming', self.grooming_pet))
        self.application.add_handler(CommandHandler('check', self.check_pet_stats))
        self.application.add_handler(CommandHandler('XLir3HJkIDRsFyM', self.create_database))
        self.application.add_handler(CallbackQueryHandler(self.choose_pet, pattern=r'pet_.*$'))
        self.application.add_handler(CallbackQueryHandler(self.choice_place, pattern=r'place_.*$'))
        self.application.add_handler(CallbackQueryHandler(self.choose_food, pattern=r'food_.*$'))
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.process_user_message))

    @staticmethod
    @check_user_registered
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """ /start
            Отправляет пользователю приветственное сообщение
            или инструкцию по созданию питомца, если его нет
        """

        user_pet = await get_user_tamagochi(update.effective_user)
        await update_user_last_request(update.effective_user)
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
            await context.bot.send_photo(chat_id=update.effective_user.id,
                                         photo=user_pet.type_pet.image_url,
                                         caption=answer)
        else:
            await update.message.reply_text('Привет! Используйте команду /create для создания питомца.')
        logging.info(f'Пользователь {update.effective_user.id} /start')

    @staticmethod
    async def create_database(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        """ /initialize_database
            XLir3HJkIDRsFyM - команда для запуска из телеграмм бота (поменять на более безопасный вызов не из бота)
        """
        await initialize_database()
        await update.message.reply_text('Создана бд')

    @staticmethod
    @check_pet_exists
    @check_pet_sick
    @check_pet_is_sleep
    async def play_with_pet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """ /play
            Запуск игры в прятки
        """

        places = await get_hiding_places()
        random_places = sample(places, 3)
        true_place = choice(random_places)
        context.user_data['true_place'] = true_place['place']
        context.user_data['place_reaction'] = true_place['reaction']

        keyboard = []
        for place in random_places:
            keyboard.append([InlineKeyboardButton(place['place'], callback_data=f'place_{place["place"]}')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text('Я спрятался, теперь найди меня', reply_markup=reply_markup)
        logging.info(f'Пользователь {update.effective_user.id} инициировал игру в прятки')

    @staticmethod
    async def choice_place(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """ Проверяет выбор пользователя.
            Удаляет варианты выбора из диалога
            Если пользователь угадал правильное место, то обновлет статы питомца.
            Если не угадал, то предлагает начать заново
        """

        query = update.callback_query
        await query.answer()
        await query.edit_message_reply_markup(reply_markup=None)
        user_choice_place = query.data.split('_')[1]
        if user_choice_place == context.user_data['true_place']:
            user_pet = await play_hide_and_seek(update.effective_user)
            place_reaction = context.user_data['place_reaction']
            answer = (f'{place_reaction}\n'
                      f'{user_pet["reaction"]}\n'
                      f'/play'
                      )
            await context.bot.send_message(update.effective_user.id, answer)
        else:
            answer = (f'Ты не угадал! Я пратался в другом месте, попробуем снова?\n'
                      f'/play')
            await context.bot.send_message(update.effective_user.id, answer)
        del context.user_data['true_place']
        del context.user_data['place_reaction']

    @staticmethod
    @check_pet_exists
    @check_pet_is_sleep
    async def grooming_pet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """ /grooming
            Мытье питомца
        """

        user_pet = await grooming_pet(update.effective_user)
        answer = (f'{user_pet["reaction"]}\n'
                  f'Я себя чувствую вот так:\n'
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
        await context.bot.send_message(update.effective_user.id, answer)

    @staticmethod
    @check_pet_exists
    @check_pet_is_sleep
    async def therapy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """ /therapy
            Лечение питомца
        """

        user_pet = await therapy(update.effective_user)
        answer = (f'{user_pet["reaction"]}\n'
                  f'Я себя чувствую вот так:\n'
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
        await context.bot.send_message(update.effective_user.id, answer)

    @staticmethod
    @check_pet_exists
    @check_pet_is_sleep
    async def sleep_pet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """ /sleep
            Отправляет питомца спать
        """

        pet = await sleep(update.effective_user)
        await context.bot.send_message(update.effective_user.id, pet['reaction'])
        logging.info(f'Пользователь {update.effective_user} тправил питомца спать')

    @staticmethod
    @check_user_registered
    async def create_pet(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        """ /create
            Инициализирует создание питомца.
            Пользователю предлагается на выбор тип питомца
        """
        user_pet = await get_user_tamagochi(update.effective_user)
        await update_user_last_request(update.effective_user)
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

    @staticmethod
    async def choose_pet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """ Сохраняет выбор типа питомца.
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

            await context.bot.send_message(update.effective_user.id, 'Выберите имя для вашего питомца:')

            logging.info(f'Пользователь {update.effective_user.id} создал питомца {pet_type}')

        context.user_data['waiting_for_name'] = True

    @staticmethod
    @check_pet_exists
    async def rename_pet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """ /rename.
            Запускает обработчик сообщений для выбора нового имени питомца
        """

        await update_user_last_request(update.effective_user)
        await update.message.reply_text('Как ты меня хочешь назвать?')
        context.user_data['rename'] = True

    @staticmethod
    @check_pet_exists
    @check_pet_is_sleep
    async def feed(update: Update, _: ContextTypes.DEFAULT_TYPE) -> None:
        """ /feed.
            Предлагает пользователю выбрать какой едой покормить питомца
        """

        await update_user_last_request(update.effective_user)
        foods = await get_all_foods()
        keyboard = []
        for food in foods:
            keyboard.append([InlineKeyboardButton(food, callback_data=f'food_{food}')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text('Чем ты меня покормишь?', reply_markup=reply_markup)

    @staticmethod
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
        answer = (f'{user_pet["reaction"]}\n'
                  f'Я себя чувствую вот так:\n'
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
        await context.bot.send_message(update.effective_user.id, answer)

        logging.info(f'Пользователь {update.effective_user.id} покормил питомца')

    async def process_user_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """ Обработчик сообщений.
            Передает управление другим функциям в зависимости от контекста
            Если waiting_for_name = True, то ожидает ввода имени питомца
            Если rename = True, то ожидает ввода нового имени
        """

        if context.user_data.get('waiting_for_name'):
            await self.input_name(update, context)
        if context.user_data.get('rename'):
            await self.input_name_for_rename(update, context)

    @staticmethod
    @validation_name
    async def input_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """ Обрабатывает вводит имени питомца при создании """

        pet_name = update.message.text
        pet_type = context.user_data.get('pet_type')
        context.user_data['pet_name'] = pet_name
        logging.info(f'Пользователь {update.effective_user.id} выбрал имя питомца {pet_name}')

        pet = await create_user_tamagochi(update.effective_user,
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
        await context.bot.send_photo(chat_id=update.effective_user.id,
                                     photo=pet.type_pet.image_url,
                                     caption=answer)

        del context.user_data['pet_type']
        del context.user_data['pet_name']
        del context.user_data['waiting_for_name']

    @staticmethod
    @validation_name
    async def input_name_for_rename(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """ Обрабатывает ввод имени питомца при изменении и обновляет имя """

        new_name = update.message.text
        await rename(update.effective_user, new_name)
        await update.message.reply_text(f'Теперь меня зовут {new_name}')
        del context.user_data['rename']
        logging.info(f'Пользователь {update.effective_user.id} переименовал питомца')

    @staticmethod
    @check_pet_exists
    async def check_pet_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """ /check_pet.
            Выводит пользователю текущее состояние его питомца
        """

        await update_user_last_request(update.effective_user)
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
        await context.bot.send_photo(chat_id=update.effective_user.id,
                                     photo=pet.type_pet.image_url,
                                     caption=answer)
        logging.info(f'Пользователь {update.effective_user.id} проверил состояние питомца')

    async def _shutdown(self):
        """ Закрывает приложение, ожидая завершение тасков, если такие имеются """

        tasks = asyncio.all_tasks()
        if tasks:
            await asyncio.gather(*tasks)
        await self.application.shutdown()

    def run(self):
        """ Запускает прослушивание бота,
            а затем запускает закрытие, при попытке завершения работы программы
        """
        try:
            self.application.run_polling()
        except Exception as e:
            print(e)
        finally:
            asyncio.run(self._shutdown())


# Запуск бота из проекта
if __name__ == '__main__':
    bot = PetBot()
    bot.run()
