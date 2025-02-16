""" Изменение состояния питомца """

import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.orm import joinedload
from telegram import _user
from .models import UserTamagochi, User, Food, TypeFood
from .methods import session_local


async def feed_pet(user: _user, food: str) -> dict:
    """ Кормление питомца.
        В зависимости от выбора еды,
        повышает и понижает соответствующие характеристики питомца
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
        print(user_pet.health, user_pet.happiness, user_pet.grooming, user_pet.energy, user_pet.hunger)
        current_value = getattr(user_pet, food_type.up_state_name, 0)
        new_value = current_value + food_type.up_state_point
        setattr(user_pet, food_type.up_state_name, new_value)
        print(user_pet.health, user_pet.happiness, user_pet.grooming, user_pet.energy, user_pet.hunger)

        # Уменьшение характеристик
        print(user_pet.health, user_pet.happiness, user_pet.grooming, user_pet.energy, user_pet.hunger)
        current_value = getattr(user_pet, food_type.down_state_name, 0)
        new_value = current_value + food_type.down_state_point
        setattr(user_pet, food_type.down_state_name, new_value)
        print(user_pet.health, user_pet.happiness, user_pet.grooming, user_pet.energy, user_pet.hunger)
        await db_sess.commit()
        await db_sess.refresh(user_pet)
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
