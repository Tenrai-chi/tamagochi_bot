""" Методы базы данных """

import logging

from configparser import ConfigParser
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from telegram import _user
from typing import Union, List

from .models import User, TypeTamagochi, UserTamagochi, TypeFood, Food

config = ConfigParser()
config.read('config.ini')
db_host = config['postgresql']['host']
db_name = config['postgresql']['name']
db_user = config['postgresql']['user']
db_password = config['postgresql']['password']

DATABASE_URL = f'postgresql+pg8000://{db_user}:{db_password}@{db_host}/{db_name}'
engine = create_engine(DATABASE_URL)
Base = declarative_base()
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


def session_local() -> Session:
    """ Создание сессии в SQLAlchemy """

    session = sessionmaker(bind=engine)
    return session()


def create_tables() -> None:
    """ Создание таблиц в базе данных """

    try:
        Base.metadata.create_all(engine)
        logging.info(f'Создание таблиц прошло успешно')
    except Exception as e:
        logging.error(e)


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
