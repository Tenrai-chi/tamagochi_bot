""" Логика работы с базой данных """
import logging
from typing import Union
from sqlalchemy import create_engine, Column, Integer, String, BigInteger, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from configparser import ConfigParser
from telegram import _user

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


class User(Base):
    """ Таблица user.
        Хранит информацию о пользователях с питомцем:
            - Телеграм id
            - Username
            - Время последнего взаимодействия
    """

    __tablename__ = 'user'
    id = Column(Integer, primary_key=True)
    user_telegram_id = Column(BigInteger, nullable=False)
    username = Column(String(255), nullable=True)
    last_request = Column(DateTime(timezone=True), nullable=True)


class TypeTamagochi(Base):
    """ Таблица type_tamagochi.
        Хранит информацию о типах тамагочи:
            - name - название
            - health_max - максимальное здоровье
            - happiness_max - максимальное настроение
            - grooming_max - максимальная чистота
            - energy_max - максимальная энергия
            - hunger_max - максимальная сытость
            - image - картинка питомца
    """

    __tablename__ = 'type_tamagochi'
    id = Column(Integer, primary_key=True)
    name = Column(String(30), nullable=False)
    health_max = Column(Integer, nullable=False)
    happiness_max = Column(Integer, nullable=False)
    grooming_max = Column(Integer, nullable=False)
    energy_max = Column(Integer, nullable=False)
    hunger_max = Column(Integer, nullable=False)
    image = Column(String(500), nullable=True)


class UserTamagochi(Base):
    """ Таблица user_tamagochi.
        Хранит информацию о питомцах пользователей:
            - owner (user) - хозяин
            - name - имя
            - type (type_tamagochi) - тип питомца
            - health - текущее здоровье
            - happiness - текущее настроение
            - grooming - текущая чистота
            - energy - текущая энергия
            - hunger - текущая сытость
            - sick - болезнь
    """

    __tablename__ = 'user_tamagochi'
    id = Column(Integer, primary_key=True)
    owner = Column(Integer, ForeignKey('user.id'))
    name = Column(String(50), nullable=True)
    type = Column(Integer, ForeignKey('type_tamagochi.id'))
    health = Column(Integer, nullable=False)
    happiness = Column(Integer, nullable=False)
    grooming = Column(Integer, nullable=False)
    energy = Column(Integer, nullable=False)
    hunger = Column(Integer, nullable=False)
    sick = Column(Boolean, nullable=True)


# class TypeFood(Base):
#     """ Таблица type_food.
#         Хранит информацию о типах еды:
#             - name - тип еды
#             - up_stat_name - какую характеристику повышает
#             - up_stat_point - на сколько повышает
#             - down_stat_name - какую характеристику понижает
#             - down_stat_point - на сколько понижает
#     """
#
#     # __tablename__ = 'type_food'
#
#
# class Food(Base):
#     """ Таблица food.
#         Хранит информацию о еде:
#             - name - название
#             - type_food - тип еды (type_food)
#     """
#
#     # __tablename__ = 'food'
#
#
# class Reaction(Base):
#     """ Таблица reaction.
#         Хранит реплики питомца на различные действия:
#             - active - какое действие
#             - speech - сообщение реакция
#     """
#
#     # __tablename__ = 'reaction'
#
#
# class HidingPlace(Base):
#     """ Таблица hiding_place.
#         Хранит места для пряток и реакцию на поиск:
#             - type_pet - тип питомца, который может здесь прятаться
#             - place - место для пряток
#             - speech - реакция на поимку
#     """
#
#     # __tablename__ = 'hiding_place'


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


async def get_types_pet() -> list:
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
        pet = UserTamagochi(owner=user.id,
                            name=name,
                            type=pet_type_info.id,
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
                    last_request=None, )

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
        user = db_sess.query(User).filter(User.user_telegram_id == user.id).first()
        user_pet = db_sess.query(UserTamagochi).filter(UserTamagochi.owner == user.id).first()

        return user_pet


async def rename(user_: _user, new_name: str) -> None:
    """ Переименовывает питомца пользователя """

    with session_local() as db_sess:
        user = db_sess.query(User).filter(User.user_telegram_id == user_.id).first()
        new = db_sess.query(UserTamagochi).filter(UserTamagochi.owner == user.id).update({'name': new_name})
        db_sess.commit()

# print(get_types_pet())
