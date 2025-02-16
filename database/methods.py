""" Методы базы данных """
import asyncio
import logging
import json
import os
import threading
import time

from dotenv import load_dotenv
from sqlalchemy import create_engine, text, MetaData, Table, Column, Integer, String, Identity
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from telegram import _user
from typing import Union, List

from database.models import User, TypeTamagochi, UserTamagochi, TypeFood, Food, Reaction, HidingPlace

load_dotenv()
db_host = os.getenv('db_host')
db_name = os.getenv('db_name')
db_user = os.getenv('db_user')
db_password = os.getenv('db_password')


DATABASE_URL = f'postgresql+asyncpg://{db_user}:{db_password}@{db_host}:5432/{db_name}'
# engine = create_engine(DATABASE_URL)
engine = create_async_engine(DATABASE_URL)
Base = declarative_base()
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


async def session_local() -> AsyncSession:
    """Создает новую асинхронную сессию для каждого запроса."""
    async_session = sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    async with async_session() as session:
        yield session


async def get_types_pet() -> List[str]:
    """ Возвращает список доступных типов питомцев """

    with session_local() as db_sess:
        pets_types = db_sess.query(TypeTamagochi.name).all()
        name_pets_types = [name for (name,) in pets_types]

        return name_pets_types


async def create_user_tamagochi(user_telegram_id: int, name: str, type_pet: str) -> UserTamagochi:
    """ Создает питомца у пользователя """

    with session_local() as db_sess:
        user = db_sess.query(User).filter(User.user_telegram_id == user_telegram_id).first()
        pet_type_info = db_sess.query(TypeTamagochi).filter(TypeTamagochi.name == type_pet).first()
        pet = UserTamagochi(owner=user,
                            name=name,
                            type_pet=pet_type_info,
                            health=pet_type_info.health_max,
                            happiness=pet_type_info.happiness_max,
                            grooming=pet_type_info.grooming_max,
                            energy=pet_type_info.energy_max,
                            hunger=pet_type_info.hunger_max,
                            sick=False,)
        db_sess.add(pet)
        db_sess.commit()
        db_sess.refresh(pet)
        return pet


async def create_user(user: _user) -> User:
    """ Возвращает пользователя. Если его нет, то создает """

    with session_local() as db_sess:
        user = User(user_telegram_id=user.id,
                    username=user.username,
                    last_request=None,)

        db_sess.add(user)
        db_sess.commit()
        db_sess.refresh(user)
        return user


async def get_user(user: _user) -> Union[User, None]:
    """ Возвращает пользователя """

    with session_local() as db_sess:
        user = db_sess.query(User).filter(User.user_telegram_id == user.id).first()

        return user


async def get_user_tamagochi(user: _user) -> Union[UserTamagochi, None]:
    """ Возвращает питомца пользователя
        Если питомца нет, то вернет None
    """

    with session_local() as db_sess:
        user_pet = db_sess.query(UserTamagochi).join(User).filter(User.user_telegram_id == user.id).first()

        return user_pet


async def rename(user: _user, new_name: str) -> None:
    """ Переименовывает питомца пользователя """

    with session_local() as db_sess:
        pet = db_sess.query(UserTamagochi).join(User).filter(User.user_telegram_id == user.id).first()
        pet.name = new_name
        db_sess.commit()


async def get_all_foods() -> List[str]:
    """ Возвращает всю доступную еду для питомца """

    with session_local() as db_sess:
        foods = db_sess.query(Food).all()
        name_foods = []
        for food in foods:
            name_foods.append(food.name)
        return name_foods


async def create_tables() -> None:
    """ Создание таблиц в базе данных """

    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all, tables=[TypeFood.__table__,
                                                                  User.__table__,
                                                                  TypeTamagochi.__table__,
                                                                  UserTamagochi.__table__,
                                                                  Food.__table__,
                                                                  Reaction.__table__,
                                                                  HidingPlace.__table__])
        logging.info('Таблицы успешно созданы')
    except Exception as e:
        logging.error(f"Ошибка при создании триггера: {e}")


async def create_trigger_and_func():
    """ Создание триггеров для параметров питомца
        при первом создании БД
    """

    create_func_sql = """
    CREATE OR REPLACE FUNCTION enforce_limits() 
    RETURNS TRIGGER AS $$ 
    BEGIN 
        NEW.health = GREATEST(LEAST(NEW.happiness, 100), 0); 
         NEW.happiness = GREATEST(LEAST(NEW.happiness, 100), 0); 
         NEW.grooming = GREATEST(LEAST(NEW.grooming, 100), 0); 
         NEW.energy = GREATEST(LEAST(NEW.energy, 100), 0); 
         NEW.hunger = GREATEST(LEAST(NEW.hunger, 100), 0); 
         RETURN NEW; 
    END; 
    $$ LANGUAGE plpgsql; 
    """

    create_trigger_sql = """
    CREATE TRIGGER enforce_limits_trigger 
    BEFORE INSERT OR UPDATE ON user_tamagochi 
    FOR EACH ROW EXECUTE FUNCTION enforce_limits(); 
    """
    try:
        async with engine.begin() as conn:
            await conn.execute(text(create_func_sql))
            await conn.execute(text(create_trigger_sql))
            logging.info('Триггер для user_tamagochi успешно создан')
    except Exception as e:
        logging.error(f'Ошибка при создании триггера: {e}')


async def populate_type_food_table():
    """ Заполнение таблицы type_food при первом создании БД """

    try:
        async for sess in session_local():
            food_types = [
                TypeFood(name='Полезная',
                         up_state_name='hunger',
                         up_state_point=20,
                         down_state_name='happiness',
                         down_state_point=-5),
                TypeFood(name='Обычная',
                         up_state_name='hunger',
                         up_state_point=25,
                         down_state_name='energy',
                         down_state_point=-10),
                TypeFood(name='Вредная',
                         up_state_name='hunger',
                         up_state_point=35,
                         down_state_name='health',
                         down_state_point=-10),
            ]
            sess.add_all(food_types)
            await sess.commit()
            logging.info('Таблица type_food успешно заполнена')
    except Exception as e:
        logging.error(f'Ошибка при заполнении таблицы type_food: {e}')


async def populate_food_table():
    """ Заполнение таблицы food при первом создании БД """

    try:
        async for sess in session_local():
            food_types = [
                Food(name='Овощной салат', type_food_id=1),
                Food(name='Фрукты', type_food_id=1),
                Food(name='Овсяная каша', type_food_id=1),
                Food(name='Курица', type_food_id=2),
                Food(name='Морская рыба', type_food_id=2),
                Food(name='Бургер', type_food_id=3),
                Food(name='Нагетсы', type_food_id=3),
                Food(name='Шоколадный торт', type_food_id=3),
            ]
            sess.add_all(food_types)
            await sess.commit()
    except Exception as e:
        logging.error(f'Ошибка при заполнении таблицы food: {e}')


async def initialize_database():
    """ Первоначальное создание и заполнение базы данныз для развертывания """

    # await create_tables()
    # await create_trigger_and_func()
    # await populate_type_food_table()
    await populate_food_table()
    # await populate_reaction_table()
    # await populate_hiding_place_table()


# def create_table():
#     """ Создание таблиц reaction и hiding_place"""
#
#     Reaction.__table__.create(engine, checkfirst=True)  # Создание таблицы Reaction
#     HidingPlace.__table__.create(engine, checkfirst=True)


async def populate_reaction_table():
    """ Заполняет таблицу reaction """

    with open('pet_reaction.json', 'r', encoding='utf-8') as js:
        data = json.load(js)
    action_and_reaction = data.get('responses', [])

    with session_local() as sess:
        for act_react in action_and_reaction:
            action = act_react['action']
            reactions = act_react['reaction']
            for react in reactions:
                new = Reaction(action=action, reaction=react)
                sess.add(new)
        sess.commit()


async def populate_hiding_place_table():
    """ Заполняет таблицу hiding_place """

    with open('places.json', 'r', encoding='utf-8') as js:
        data = json.load(js)
    places_and_reactions = data.get('hiding_places', [])

    with session_local() as sess:
        for place_react in places_and_reactions:
            new = HidingPlace(place=place_react['place'], reaction_found=place_react['reaction_found'])
            sess.add(new)
        sess.commit()
