""" Функции для запросов к базе данных для имзенения состояния питомца """

import asyncpg
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.orm import joinedload
from telegram import _user

from .methods import moscow_tz, db_user, db_name, db_host, db_password, session_local, get_reaction_to_action
from .models import UserTamagochi, User, Food
from utilites.logger import logger


async def feed_pet(user: _user, food: str) -> dict:
    """ Кормление питомца
        В зависимости от выбора еды,
        повышает hunger и понижает 1 характеристику питомца
    """

    async for db_sess in session_local():
        user_pet_result = await db_sess.execute(select(UserTamagochi)
                                                .join(User)
                                                .filter(User.user_telegram_id == user.id))
        user_pet = user_pet_result.scalars().first()

        food_results = await db_sess.execute(select(Food)
                                             .where(Food.name == food)
                                             .options(joinedload(Food.type_food))
                                             )
        food = food_results.scalars().first()
        food_type = food.type_food

        # Увеличение характеристик
        current_value = getattr(user_pet, food_type.up_state_name, 0)
        new_value = current_value + food_type.up_state_point
        setattr(user_pet, food_type.up_state_name, new_value)

        # Уменьшение характеристик
        current_value = getattr(user_pet, food_type.down_state_name, 0)
        new_value = current_value + food_type.down_state_point
        setattr(user_pet, food_type.down_state_name, new_value)
        await db_sess.commit()
        await db_sess.refresh(user_pet)
        reaction = await get_reaction_to_action('fed')
        return {'health': user_pet.health,
                'happiness': user_pet.happiness,
                'grooming': user_pet.grooming,
                'energy': user_pet.energy,
                'hunger': user_pet.hunger,
                'sick': user_pet.sick,
                'reaction': reaction
                }


async def play_hide_and_seek(user: _user) -> dict:
    """ Игра в прятки с питомцем
        Увеличивает настроение и уменьшает энергию питомца
    """

    async for db_sess in session_local():
        user_pet_result = await db_sess.execute(select(UserTamagochi)
                                                .join(User)
                                                .filter(User.user_telegram_id == user.id))
        user_pet = user_pet_result.scalars().first()
        user_pet.energy -= 10
        user_pet.happiness += 15
        await db_sess.commit()
        await db_sess.refresh(user_pet)
        reaction = await get_reaction_to_action('playing')
        return {'health': user_pet.health,
                'happiness': user_pet.happiness,
                'grooming': user_pet.grooming,
                'energy': user_pet.energy,
                'hunger': user_pet.hunger,
                'sick': user_pet.sick,
                'reaction': reaction
                }


async def grooming_pet(user: _user) -> dict:
    """ Мытье питомца
        Увеличивает чистоту питомца
    """

    async for db_sess in session_local():
        user_pet_result = await db_sess.execute(select(UserTamagochi)
                                                .join(User)
                                                .filter(User.user_telegram_id == user.id))
        user_pet = user_pet_result.scalars().first()
        user_pet.grooming += 100
        await db_sess.commit()
        await db_sess.refresh(user_pet)
        reaction = await get_reaction_to_action('grooming')
        return {'health': user_pet.health,
                'happiness': user_pet.happiness,
                'grooming': user_pet.grooming,
                'energy': user_pet.energy,
                'hunger': user_pet.hunger,
                'sick': user_pet.sick,
                'reaction': reaction
                }


async def therapy(user: _user) -> dict:
    """ Лечение питомца
        Полностью восстанавливает здоровье питомца и исцеляет болезнь
    """

    async for db_sess in session_local():
        user_pet_result = await db_sess.execute(select(UserTamagochi)
                                                .join(User)
                                                .filter(User.user_telegram_id == user.id))
        user_pet = user_pet_result.scalars().first()
        user_pet.sick = False
        user_pet.health += 100
        await db_sess.commit()
        await db_sess.refresh(user_pet)
        reaction = await get_reaction_to_action('healing')
        return {'health': user_pet.health,
                'happiness': user_pet.happiness,
                'grooming': user_pet.grooming,
                'energy': user_pet.energy,
                'hunger': user_pet.hunger,
                'sick': user_pet.sick,
                'reaction': reaction
                }


async def sleep(user: _user) -> dict:
    """ Сон. Питомец уходит в инактив
        и становится недоступным для взаимодействия на 4 часа
        Время отправки питомца в сон user_pet.time_sleep
        При отправке спать питомец получает 60 энергии
    """

    async for db_sess in session_local():
        user_pet_result = await db_sess.execute(select(UserTamagochi)
                                                .join(User)
                                                .filter(User.user_telegram_id == user.id))
        user_pet = user_pet_result.scalars().first()
        user_pet.energy += 80
        user_pet.sleep = True
        user_pet.time_sleep = datetime.now(moscow_tz)
        await db_sess.commit()
        await db_sess.refresh(user_pet)
        reaction = await get_reaction_to_action('sleep_start')
        return {'reaction': reaction}


async def reduction_stats() -> None:
    """ Уменьшение характеристик питомца о временем """

    try:
        logger.info('Подключаемся к базе данных...')

        # Пришлось работать напрямую через asyncpg, так как обычная сессия с SQLAlchemy отрабатывала с ошибками
        conn = await asyncpg.connect(f'postgresql://{db_user}:{db_password}@{db_host}/{db_name}')

        pets = await conn.fetch('SELECT * FROM user_tamagochi')

        if not pets:
            logger.warning('Нет питомцев в базе данных')
            return

        async with conn.transaction():
            for pet in pets:
                updated_stats = {
                    'health': pet['health'] - 5,
                    'happiness': pet['happiness'] - 5,
                    'grooming': pet['grooming'] - 5,
                    'hunger': pet['hunger'] - 5
                }

                # Обновление данных питомца в базе, используется вставка, а не f-string
                await conn.execute("""
                        UPDATE user_tamagochi
                        SET health = $1, happiness = $2, grooming = $3, hunger = $4
                        WHERE id = $5
                    """,
                                   updated_stats['health'],
                                   updated_stats['happiness'],
                                   updated_stats['grooming'],
                                   updated_stats['hunger'],
                                   pet['id'])
        logger.info('Изменение характеристик питомцев прошло успешно!')

    except Exception as e:
        logger.error(f'Произошла ошибка в reduction_stats: {e}')
    finally:
        if conn:
            logger.info('Закрытие подключения к базе данных...')
            await conn.close()
