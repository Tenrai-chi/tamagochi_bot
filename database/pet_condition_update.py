""" Изменение состояния питомца """

import asyncio

from sqlalchemy.orm import joinedload
from telegram import _user
from .models import UserTamagochi, User, Food, TypeFood
from .methods import session_local


async def feed_pet(user: _user, food: str) -> dict:
    """ Кормление питомца.
        В зависимости от выбора еды,
        повышает и понижает соответствующие характеристики питомца
    """

    with session_local() as db_sess:
        user_pet = db_sess.query(UserTamagochi).join(User).filter(User.user_telegram_id == user.id).first()

        food = db_sess.query(Food).filter(Food.name == food).options(joinedload(Food.type_food)).first()
        food_type = food.type_food

        # Увеличение характеристик
        current_value = getattr(user_pet, food_type.up_state_name, 0)
        new_value = current_value + food_type.up_state_point
        setattr(user_pet, food_type.up_state_name, new_value)

        # Уменьшение характеристик
        current_value = getattr(user_pet, food_type.down_state_name, 0)
        new_value = current_value + food_type.down_state_point
        setattr(user_pet, food_type.down_state_name, new_value)
        db_sess.commit()

        return {'health': user_pet.health,
                'happiness': user_pet.happiness,
                'grooming': user_pet.grooming,
                'energy': user_pet.energy,
                'hunger': user_pet.hunger,
                'sick': user_pet.sick
                }


async def play_hide_and_seek():
    """ Игра в прятки """
    pass


async def cleaning():
    """ Очистка питомца """
    pass


async def sleep():
    """ Сон """
    pass


async def therapy():
    """ Лечение питомца """
    pass


async def reduction_stats():
    """ Уменьшение характеристик питомца о временем """
    pass

# a = asyncio.run(feed('Овощной салат'))
# print(a)
