""" Модели базы данных """

from sqlalchemy import Column, Integer, String, BigInteger, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import declarative_base, relationship
Base = declarative_base()


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

    user_pet = relationship('UserTamagochi',
                            back_populates='owner',
                            uselist=False)


class TypeTamagochi(Base):
    """ Таблица type_tamagochi.
        Хранит информацию о типах тамагочи:
            - name - название
            - health_max - максимальное здоровье
            - happiness_max - максимальное настроение
            - grooming_max - максимальная чистота
            - energy_max - максимальная энергия
            - hunger_max - максимальная сытость
            - image_url - картинка питомца
    """

    __tablename__ = 'type_tamagochi'
    id = Column(Integer, primary_key=True)
    name = Column(String(30), nullable=False)
    health_max = Column(Integer, nullable=False)
    happiness_max = Column(Integer, nullable=False)
    grooming_max = Column(Integer, nullable=False)
    energy_max = Column(Integer, nullable=False)
    hunger_max = Column(Integer, nullable=False)
    image_url = Column(String(500), nullable=True)

    pet = relationship('UserTamagochi', back_populates='type_pet')


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
    owner_id = Column(Integer, ForeignKey('user.id'), unique=True)
    name = Column(String(50), nullable=True)
    type_id = Column(Integer, ForeignKey('type_tamagochi.id'))
    health = Column(Integer, nullable=False)
    happiness = Column(Integer, nullable=False)
    grooming = Column(Integer, nullable=False)
    energy = Column(Integer, nullable=False)
    hunger = Column(Integer, nullable=False)
    sick = Column(Boolean, nullable=True)

    owner = relationship('User', back_populates='user_pet')
    type_pet = relationship('TypeTamagochi', back_populates='pet')


class TypeFood(Base):
    """ Таблица type_food.
        Хранит информацию о типах еды:
            - name - тип еды
            - up_stat_name - какую характеристику повышает
            - up_stat_point - на сколько повышает
            - down_stat_name - какую характеристику понижает
            - down_stat_point - на сколько понижает
    """

    __tablename__ = 'type_food'
    id = Column(Integer, primary_key=True)
    name = Column(String(70), nullable=True)
    up_state_name = Column(String(20), nullable=False)
    up_state_point = Column(Integer, nullable=False)
    down_state_name = Column(String(20), nullable=False)
    down_state_point = Column(Integer, nullable=False)

    food = relationship('Food', back_populates='type_food')


class Food(Base):
    """ Таблица food.
        Хранит информацию о еде:
            - name - название
            - type_food - тип еды (type_food)
    """

    __tablename__ = 'food'
    id = Column(Integer, primary_key=True)
    name = Column(String(70), nullable=True)
    type_food_id = Column(Integer, ForeignKey('type_food.id'))

    type_food = relationship('TypeFood', back_populates='food')


class Reaction(Base):
    """ Таблица reaction.
        Хранит реплики питомца на различные действия:
            - action - какое действие
            - reaction - сообщение реакция
    """

    __tablename__ = 'reaction'
    id = Column(Integer, primary_key=True)
    action = Column(String(100), nullable=True)
    reaction = Column(String(300), nullable=True)


class HidingPlace(Base):
    """ Таблица hiding_place.
        Хранит места для пряток и реакцию на поиск:
            - place - место для пряток
            - reaction - реакция на поимку
    """

    __tablename__ = 'hiding_place'
    id = Column(Integer, primary_key=True)
    place = Column(String(100), nullable=True)
    reaction_found = Column(String(300), nullable=True)

