""" Изменение состояния питомца """

from sqlalchemy import select
from sqlalchemy.orm import joinedload
from telegram import _user

from .methods import session_local, get_reaction_to_action
from .models import UserTamagochi, User, Food


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
        current_value = getattr(user_pet, food_type.up_state_name, 0)
        new_value = current_value + food_type.up_state_point
        setattr(user_pet, food_type.up_state_name, new_value)

        # Уменьшение характеристик
        current_value = getattr(user_pet, food_type.down_state_name, 0)
        new_value = current_value + food_type.down_state_point
        setattr(user_pet, food_type.down_state_name, new_value)
        await db_sess.commit()
        await db_sess.refresh(user_pet)
        reaction = await get_reaction_to_action('fed')
        return {'health': user_pet.health,
                'happiness': user_pet.happiness,
                'grooming': user_pet.grooming,
                'energy': user_pet.energy,
                'hunger': user_pet.hunger,
                'sick': user_pet.sick,
                'reaction': reaction
                }


async def play_hide_and_seek(user: _user) -> dict:
    """ Игра в прятки с питомцем.
        Увеличивает настроение и уменьшает энергию питомца
    """

    async for db_sess in session_local():
        user_pet_result = await db_sess.execute(select(UserTamagochi)
                                                .join(User)
                                                .filter(User.user_telegram_id == user.id))
        user_pet = user_pet_result.scalars().first()
        user_pet.energy -= 10
        user_pet.happiness += 15
        await db_sess.commit()
        await db_sess.refresh(user_pet)
        reaction = await get_reaction_to_action('playing')
        return {'health': user_pet.health,
                'happiness': user_pet.happiness,
                'grooming': user_pet.grooming,
                'energy': user_pet.energy,
                'hunger': user_pet.hunger,
                'sick': user_pet.sick,
                'reaction': reaction
                }


async def grooming_pet(user: _user) -> dict:
    """ Мытье питомца.
        Увеличивает чистоту питомца
    """

    async for db_sess in session_local():
        user_pet_result = await db_sess.execute(select(UserTamagochi)
                                                .join(User)
                                                .filter(User.user_telegram_id == user.id))
        user_pet = user_pet_result.scalars().first()
        user_pet.grooming += 100
        await db_sess.commit()
        await db_sess.refresh(user_pet)
        reaction = await get_reaction_to_action('grooming')
        return {'health': user_pet.health,
                'happiness': user_pet.happiness,
                'grooming': user_pet.grooming,
                'energy': user_pet.energy,
                'hunger': user_pet.hunger,
                'sick': user_pet.sick,
                'reaction': reaction
                }


async def therapy(user: _user) -> dict:
    """ Лечение питомца.
        Полностью восстанавливает здоровье питомца и исцеляет болезнь
    """

    async for db_sess in session_local():
        user_pet_result = await db_sess.execute(select(UserTamagochi)
                                                .join(User)
                                                .filter(User.user_telegram_id == user.id))
        user_pet = user_pet_result.scalars().first()
        user_pet.sick = False
        user_pet.health += 100
        await db_sess.commit()
        await db_sess.refresh(user_pet)
        reaction = await get_reaction_to_action('grooming')
        return {'health': user_pet.health,
                'happiness': user_pet.happiness,
                'grooming': user_pet.grooming,
                'energy': user_pet.energy,
                'hunger': user_pet.hunger,
                'sick': user_pet.sick,
                'reaction': reaction
                }


async def sleep():
    """ Сон. Питомец должен уходить в инактив
        на какое-то время и быть недоступным для взаиодействие.
        Во время сна восстанавливается энергия
    """
    pass


async def reduction_stats():
    """ Уменьшение характеристик питомца о временем """
    pass
