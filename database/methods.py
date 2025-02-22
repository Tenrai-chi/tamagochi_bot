""" Функции для запросов к базе данных, не изменяющих состояние питомца """

import logging
import os
import random

import pytz

from datetime import datetime, timedelta
from dotenv import load_dotenv
from sqlalchemy import select, insert, update
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from telegram import _user
from typing import Union, List, Dict

from database.models import User, TypeTamagochi, UserTamagochi, Food, Reaction, HidingPlace

load_dotenv()
db_host = os.getenv('db_host')
db_name = os.getenv('db_name')
db_user = os.getenv('db_user')
db_password = os.getenv('db_password')
DATABASE_URL = f'postgresql+asyncpg://{db_user}:{db_password}@{db_host}/{db_name}'
engine = create_async_engine(DATABASE_URL)

moscow_tz = pytz.timezone('Europe/Moscow')
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


async def session_local() -> AsyncSession:
    """ Создает новую асинхронную сессию для каждого запроса"""
    async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session


async def get_types_pet() -> List[str]:
    """ Возвращает список доступных типов питомцев """

    async for db_sess in session_local():
        result = await db_sess.execute(select(TypeTamagochi.name))
        name_pets_types = [name for name in result.scalars().all()]
        return name_pets_types


async def create_user_tamagochi(user: _user, name: str, type_pet: str) -> UserTamagochi:
    """ Создает питомца у пользователя """

    async for db_sess in session_local():
        user_result = await db_sess.execute(select(User)
                                            .where(User.user_telegram_id == user.id))
        user_info = user_result.scalars().first()
        pet_type_result = await db_sess.execute(select(TypeTamagochi)
                                                .where(TypeTamagochi.name == type_pet))
        pet_type_info = pet_type_result.scalars().first()
        try:
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

            result = await db_sess.execute(stmt)
            pet = result.scalars().one()

            await db_sess.commit()
            logging.info(f'Питомец пользователя {user.id} был записан в базу данных')
        except Exception as e:
            logging.error(e)
        return pet


async def create_user(user: _user) -> User:
    """ Создает пользователя """

    async for db_sess in session_local():
        user = User(user_telegram_id=user.id,
                    username=user.username,
                    last_request=None,)

        db_sess.add(user)
        await db_sess.commit()
        await db_sess.refresh(user)
        return user


async def get_user(user: _user) -> Union[User, None]:
    """ Возвращает пользователя """

    async for db_sess in session_local():
        result = await db_sess.execute(select(User)
                                       .where(User.user_telegram_id == user.id))
        user = result.scalars().first()
        return user


async def get_user_tamagochi(user: _user) -> Union[UserTamagochi, None]:
    """ Возвращает питомца пользователя
        Если питомца нет, то вернет None
    """

    async for db_sess in session_local():
        user_pet_result = await db_sess.execute(select(UserTamagochi)
                                                .join(User)
                                                .where(User.user_telegram_id == user.id)
                                                )
        user_pet = user_pet_result.scalars().first()
        return user_pet


async def rename(user: _user, new_name: str) -> None:
    """ Переименовывает питомца пользователя """

    async for db_sess in session_local():
        pet_result = await db_sess.execute(select(UserTamagochi)
                                           .join(User)
                                           .where(User.user_telegram_id == user.id)
                                           )
        pet = pet_result.scalars().first()
        await db_sess.execute(update(UserTamagochi)
                              .where(UserTamagochi.id == pet.id)
                              .values(name=new_name))
        await db_sess.commit()


async def get_all_foods() -> List[str]:
    """ Возвращает всю доступную еду для питомца """

    async for db_sess in session_local():
        foods_result = await db_sess.execute(select(Food))
        foods = foods_result.scalars().all()
        name_foods = [food.name for food in foods]
        return name_foods


async def update_user_last_request(user: _user) -> None:
    """ Обновляет время последнего запроса у пользователя """

    async for db_sess in session_local():
        current_time = datetime.now(moscow_tz)
        result = await db_sess.execute(select(User)
                                       .where(User.user_telegram_id == user.id))
        user = result.scalars().first()
        user.last_request = current_time
        await db_sess.commit()


async def get_reaction_to_action(action: str) -> str:
    """ Возвращает реакцию питомца на действие пользователя:
        healing - лечение болезни
        playing - игра
        happiness<30 - если упало настроение
        bathing - купание
        energy<10 - если упала энергия
        fed - кормление
        health<30 - если упало здоровье
        grooming<30 - если упала чистота
    """

    async for db_sess in session_local():
        result = await db_sess.execute(select(Reaction.reaction)
                                       .where(Reaction.action == action))
        reactions = result.scalars().all()
        reaction = random.choice(reactions)
        return reaction


async def get_hiding_places() -> List[Dict[str, str]]:
    """ Возвращает все доступные места для пряток """

    async for db_sess in session_local():
        places_result = await db_sess.execute(select(HidingPlace))
        all_places = places_result.scalars().all()
        hiding_places = [
            {'place': place.place, 'reaction': place.reaction_found}
            for place in all_places
        ]
        return hiding_places


async def pet_is_sleep(user: _user) -> dict:
    """ Проверяет спит ли питомец в данный момент
        Если спит, то выводится реакция
    """

    async for db_sess in session_local():
        pet_result = await db_sess.execute(select(UserTamagochi)
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
