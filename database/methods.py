""" Методы базы данных """
import asyncio
import logging
import json
import os

from dotenv import load_dotenv
from sqlalchemy import (select, create_engine, text, MetaData, Table, Column, Integer, String, Identity)
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

    # with session_local() as db_sess:
    async for db_sess in session_local():
        # pets_types = await db_sess.query(TypeTamagochi.name).all()
        # name_pets_types = [name for (name,) in pets_types]
        result = await db_sess.execute(select(TypeTamagochi.name))
        name_pets_types = [name for name in result.scalars().all()]
        return name_pets_types


async def create_user_tamagochi(user_telegram_id: int, name: str, type_pet: str) -> UserTamagochi:
    """ Создает питомца у пользователя """

    # with session_local() as db_sess:
    async for db_sess in session_local():
        # user = await db_sess.query(User).filter(User.user_telegram_id == user_telegram_id).first()
        user_result = await db_sess.execute(select(User)
                                            .where(User.user_telegram_id == user_telegram_id))
        user = user_result.scalars().first()
        # pet_type_info = await db_sess.query(TypeTamagochi).filter(TypeTamagochi.name == type_pet).first()
        pet_type_result = await db_sess.execute(select(TypeTamagochi)
                                                .where(TypeTamagochi.name == type_pet))
        pet_type_info = pet_type_result.scalars().first()
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
        await db_sess.commit()
        await db_sess.refresh(pet)
        return pet


async def create_user(user: _user) -> User:
    """ Создает пользователя """

    # with session_local() as db_sess:
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

    # with session_local() as db_sess:
    async for db_sess in session_local():
        # user = await db_sess.query(User).filter(User.user_telegram_id == user.id).first()
        result = await db_sess.execute(select(User)
                                       .where(User.user_telegram_id == user.id))
        user = result.scalars().first()
        return user


async def get_user_tamagochi(user: _user) -> Union[UserTamagochi, None]:
    """ Возвращает питомца пользователя
        Если питомца нет, то вернет None
    """

    # with session_local() as db_sess:
    async for db_sess in session_local():
        user_pet_result = await db_sess.execute(select(UserTamagochi)
                                                .join(User)
                                                .where(User.user_telegram_id == user.id)
                                                )
        user_pet = user_pet_result.scalars().first()

        return user_pet


async def rename(user: _user, new_name: str) -> None:
    """ Переименовывает питомца пользователя """

    # with session_local() as db_sess:
    async for db_sess in session_local():
        pet_result = await db_sess.execute(select(UserTamagochi)
                                           .join(User)
                                           .where(User.user_telegram_id == user.id)
                                           )
        pet = pet_result.scalars().first()
        pet.name = new_name
        await db_sess.commit()


async def get_all_foods() -> List[str]:
    """ Возвращает всю доступную еду для питомца """

    async for db_sess in session_local():
        foods_result = await db_sess.execute(select(Food))
        foods = foods_result.scalars().all()
        # name_foods = []
        # for food in foods:
        #     name_foods.append(food.name)
        name_foods = [food.name for food in foods]
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
            logging.info('Таблица food успешно заполнена')
    except Exception as e:
        logging.error(f'Ошибка при заполнении таблицы food: {e}')


async def initialize_database():
    """ Первоначальное создание и заполнение базы данныз для развертывания """

    await create_tables()
    await create_trigger_and_func()
    await populate_type_food_table()
    await populate_food_table()
    await populate_reaction_table()
    await populate_hiding_place_table()
    await populate_type_tamagochi()


async def populate_reaction_table():
    """ Заполняет таблицу reaction """

    file_path = os.path.join(os.path.dirname(__file__), 'pet_reaction.json')
    with open(file_path, 'r', encoding='utf-8') as js:
        data = json.load(js)
    action_and_reaction = data.get('responses', [])

    try:
        async for sess in session_local():
            for act_react in action_and_reaction:
                action = act_react['action']
                reactions = act_react['reaction']
                for react in reactions:
                    new = Reaction(action=action, reaction=react)
                    sess.add(new)
            await sess.commit()
            logging.info('Таблица reaction успешно заполнена')
    except Exception as e:
        logging.error(f'Ошибка при заполнении таблицы reaction: {e}')


async def populate_hiding_place_table():
    """ Заполняет таблицу hiding_place """

    file_path = os.path.join(os.path.dirname(__file__), 'places.json')
    with open(file_path, 'r', encoding='utf-8') as js:
        data = json.load(js)
    places_and_reactions = data.get('hiding_places', [])

    try:
        async for sess in session_local():
            for place_react in places_and_reactions:
                new = HidingPlace(place=place_react['place'], reaction_found=place_react['reaction_found'])
                sess.add(new)
            await sess.commit()
            logging.info('Таблица hiding_place успешно заполнена')
    except Exception as e:
        logging.error(f'Ошибка при заполнении таблицы hiding_place: {e}')


async def populate_type_tamagochi():
    """ Заполняет таблицу type_tamagochi """

    file_path = os.path.join(os.path.dirname(__file__), 'pet_types.json')
    with open(file_path, 'r', encoding='utf-8') as js:
        data = json.load(js)
    pet_types = data.get('types', [])

    try:
        async for sess in session_local():
            for pet_type in pet_types:
                new = TypeTamagochi(name=pet_type['name'],
                                    health_max=pet_type['health_max'],
                                    happiness_max=pet_type['happiness_max'],
                                    grooming_max=pet_type['grooming_max'],
                                    energy_max=pet_type['energy_max'],
                                    hunger_max=pet_type['hunger_max'],
                                    image_url=pet_type['image_url'],
                                    )
                sess.add(new)
            await sess.commit()
            logging.info('Таблица type_tamagochi успешно заполнена')
    except Exception as e:
        logging.error(f'Ошибка при заполнении таблицы type_tamagochi: {e}')
