""" Функции для запросов к базе данных, не изменяющих состояние питомца """

import logging
import os
import pytz
import random

from datetime import datetime, timedelta
from dotenv import load_dotenv
from sqlalchemy import select, insert, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload
from telegram import _user

from database.models import User, TypeTamagochi, UserTamagochi, Food, Reaction, HidingPlace
from utilites.logger import get_logger

logger = get_logger('methods', file_level=logging.DEBUG, console_level=logging.INFO)

load_dotenv()
db_host = os.getenv('db_host')
db_name = os.getenv('db_name')
db_user = os.getenv('db_user')
db_password = os.getenv('db_password')
DATABASE_URL = f'postgresql+asyncpg://{db_user}:{db_password}@{db_host}/{db_name}'
engine = create_async_engine(url=DATABASE_URL, echo=False)
async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

moscow_tz = pytz.timezone('Europe/Moscow')


def connection(method):
    """ Декоратор для создания и передачи сессии в функции """

    async def wrapper(*args, **kwargs):
        async with async_session() as session:
            try:
                logger.debug('Открытие сессии')
                return await method(*args, session=session, **kwargs)
            except Exception as e:
                await session.rollback()
                logger.fatal(f'Ошибка при работе сессии бд: {e}')
            finally:
                await session.close()
                logger.debug(f'Закрытие сессии')
    return wrapper


@connection
async def get_types_pet(session: AsyncSession) -> list[str]:
    """ Возвращает список доступных типов питомцев """

    try:
        result = await session.execute(select(TypeTamagochi.name))
        name_pets_types = [name for name in result.scalars().all()]
        return name_pets_types
    except Exception as e:
        logger.error(f'Ошибка в get_types_pet: {e}')


@connection
async def create_user_tamagochi(user: _user, name: str, type_pet: str, session: AsyncSession) -> UserTamagochi:
    """ Создает питомца у пользователя """

    try:
        user_result = await session.execute(select(User)
                                            .where(User.user_telegram_id == user.id))
        user_info = user_result.scalars().first()
        pet_type_result = await session.execute(select(TypeTamagochi)
                                                .where(TypeTamagochi.name == type_pet))
        pet_type_info = pet_type_result.scalars().first()

        stmt = insert(UserTamagochi).values(
            owner_id=user_info.id,
            name=name,
            type_id=pet_type_info.id,
            health=pet_type_info.health_max,
            happiness=pet_type_info.happiness_max,
            grooming=pet_type_info.grooming_max,
            energy=pet_type_info.energy_max,
            hunger=pet_type_info.hunger_max,
            sick=False,
            sleep=False
        ).returning(UserTamagochi)

        result = await session.execute(stmt)
        pet = result.scalars().one()

        await session.commit()
        await session.refresh(pet, attribute_names=['type_pet'])
        logger.info(f'Питомец пользователя {user.id} был записан в базу данных')
        logger.debug(f'Создан питомец {pet.id} пользователя {user_info.id}')
        return pet

    except Exception as e:
        logger.error(f'Ошибка в create_user_tamagochi: {e}')


@connection
async def create_user(user: _user, session: AsyncSession) -> User:
    """ Создает пользователя """

    try:
        new_user = User(user_telegram_id=user.id,
                        username=user.username,
                        last_request=None)
        session.add(new_user)
        await session.commit()
        await session.refresh(new_user)
        logger.debug(f'Создан пользователь {new_user.id}')
        return user
    except Exception as e:
        logger.error(f'Ошибка в create_user: {e}')


@connection
async def get_user(user: _user, session: AsyncSession) -> User | None:
    """ Возвращает пользователя
        Если его нет, вернет None
    """

    try:
        result = await session.execute(select(User)
                                       .where(User.user_telegram_id == user.id))
        user = result.scalars().one_or_none()
        return user
    except Exception as e:
        logger.error(f'Ошибка в get_user: {e}')


@connection
async def get_user_tamagochi(user: _user, session: AsyncSession) -> UserTamagochi | None:
    """ Возвращает питомца пользователя
        Если питомца нет, вернет None
    """

    try:
        user_pet_result = await session.execute(select(UserTamagochi)
                                                .options(selectinload(UserTamagochi.type_pet))
                                                .join(User)
                                                .where(User.user_telegram_id == user.id)
                                                )
        user_pet = user_pet_result.scalars().one_or_none()
        return user_pet
    except Exception as e:
        logger.error(f'Ошибка в get_user_tamagochi: {e}')


@connection
async def rename(user: _user, new_name: str, session: AsyncSession) -> None:
    """ Переименовывает питомца пользователя """

    try:
        pet_result = await session.execute(select(UserTamagochi)
                                           .join(User)
                                           .where(User.user_telegram_id == user.id)
                                           )
        pet = pet_result.scalars().one_or_none()
        await session.execute(update(UserTamagochi)
                              .where(UserTamagochi.id == pet.id)
                              .values(name=new_name))
        logger.debug(f'Питомец пользователя {pet.owner_id} был переименован')
        await session.commit()
    except Exception as e:
        logger.error(f'Ошибка в rename: {e}')


@connection
async def get_all_foods(session: AsyncSession) -> list[str]:
    """ Возвращает всю доступную еду для питомца """

    try:
        foods_result = await session.execute(select(Food))
        foods = foods_result.scalars().all()
        name_foods = [food.name for food in foods]
        return name_foods
    except Exception as e:
        logger.error(f'Ошибка в get_all_foods: {e}')


@connection
async def update_user_last_request(user: _user, session: AsyncSession) -> None:
    """ Обновляет время последнего запроса у пользователя """

    try:
        current_time = datetime.now(moscow_tz)
        result = await session.execute(select(User)
                                       .where(User.user_telegram_id == user.id))
        user = result.scalars().first()
        user.last_request = current_time
        logger.debug(f'Время последнего взаимодействия у пользователя {user.id} обновлено')
        await session.commit()
    except Exception as e:
        logger.error(f'Ошибка в update_user_last_request: {e}')


@connection
async def get_reaction_to_action(action: str, session: AsyncSession) -> str:
    """ Возвращает реакцию питомца на действие пользователя:
        healing - после лечения
        playing - после игры
        happiness<30 - если мало настроения
        grooming - после мытья
        energy<10 - если мало энергия
        fed - после кормления
        sick - если питомец болен
        sleep - если на данный момент питомец спит
        sleep_start - после отправления питомца спать
    """

    try:
        result = await session.execute(select(Reaction.reaction)
                                       .where(Reaction.action == action))
        reactions = result.scalars().all()
        reaction = random.choice(reactions)
        return reaction
    except Exception as e:
        logger.error(f'Ошибка в get_reaction_to_action: {e}')


@connection
async def get_hiding_places(session: AsyncSession) -> list[dict]:
    """ Возвращает все доступные места для пряток
        и реакции при правильном выборе места
    """

    try:
        places_result = await session.execute(select(HidingPlace))
        all_places = places_result.scalars().all()
        hiding_places = [
            {'place': place.place, 'reaction': place.reaction_found}
            for place in all_places
        ]
        return hiding_places
    except Exception as e:
        logger.error(f'Ошибка в get_hiding_places: {e}')


@connection
async def check_is_sleep(user: _user, session: AsyncSession) -> dict:
    """ Проверяет спит ли питомец в данный момент
        Если спит, то выводится реакция
        Со спящим питомцем нельзя взаимодействовать
    """

    try:
        pet_result = await session.execute(select(UserTamagochi)
                                           .join(User)
                                           .where(User.user_telegram_id == user.id)
                                           )
        pet = pet_result.scalars().first()
        if pet.sleep is False:
            return {'sleep': False}
        else:
            now = datetime.now(moscow_tz)
            if now - pet.time_sleep >= timedelta(hours=4):
                pet.sleep = False
                pet.time_sleep = None
                return {'sleep': False}
            else:
                reaction = await get_reaction_to_action('sleep')
                return {'sleep': True,
                        'reaction': reaction}
    except Exception as e:
        logger.error(f'Ошибка в check_is_sleep: {e}')


@connection
async def check_is_sick(user: _user, session: AsyncSession) -> dict:
    """ Проверяет болен ли питомец в данный момент
        Если болен, то выводится реакция
        С больным питомцем нельзя играть
    """

    try:
        pet_result = await session.execute(select(UserTamagochi)
                                           .join(User)
                                           .where(User.user_telegram_id == user.id)
                                           )
        pet = pet_result.scalars().first()
        if pet.sick is False:
            return {'sick': False}
        else:
            reaction = await get_reaction_to_action('sick')
            return {'sick': True,
                    'reaction': reaction}
    except Exception as e:
        logger.error(f'Ошибка в check_is_sick: {e}')


@connection
async def check_user_pet_energy(user: _user, session: AsyncSession) -> dict:
    """ Проверяет, хватает ли у питомца энергии для взаимодействия """

    try:
        pet_result = await session.execute(select(UserTamagochi)
                                           .join(User)
                                           .where(User.user_telegram_id == user.id)
                                           )
        pet = pet_result.scalars().first()
        if pet.energy < 10:
            reaction = await get_reaction_to_action('energy<10')
            return {'energetic': False,
                    'reaction': reaction}
        else:
            return {'energetic': True}
    except Exception as e:
        logger.error(f'Ошибка в check_user_pet_energy: {e}')

