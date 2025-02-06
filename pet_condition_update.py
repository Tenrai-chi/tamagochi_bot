""" Изменение состояния питомца """
import asyncio

from telegram import _user
from database import UserTamagochi, User, session_local, Food, TypeFood


async def feed(user: _user, food: str):
    """ Кормление питомца.
        Переделать этот ужас
    """

    with session_local() as db_sess:
        user = db_sess.query(User).filter(User.user_telegram_id == user.id).first()
        user_pet = db_sess.query(UserTamagochi).filter(UserTamagochi.owner == user.id).first()
        food = db_sess.query(Food).filter(Food.name == food).first()
        food_type = db_sess.query(TypeFood).filter(TypeFood.id == food.type_food).first()

        if food_type.up_state_name == 'health':
            user_pet.health += food_type.up_stat_point
        if food_type.down_state_name == 'health':
            user_pet.health += food_type.down_stat_point

        if food_type.up_state_name == 'happiness':
            user_pet.happiness += food_type.up_stat_point
        if food_type.down_state_name == 'happiness':
            user_pet.happiness += food_type.down_stat_point

        if food_type.up_state_name == 'grooming':
            user_pet.grooming += food_type.up_stat_point
        if food_type.down_state_name == 'grooming':
            user_pet.grooming += food_type.down_stat_point

        if food_type.up_state_name == 'energy':
            user_pet.energy += food_type.up_stat_point
        if food_type.down_state_name == 'energy':
            user_pet.energy += food_type.down_stat_point

        if food_type.up_state_name == 'hunger':
            user_pet.hunger += food_type.up_stat_point
        if food_type.down_state_name == 'hunger':
            user_pet.hunger += food_type.down_stat_point
        db_sess.commit()


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
