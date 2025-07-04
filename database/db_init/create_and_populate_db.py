""" Создание и заполнение таблиц в бд """

import json
import logging
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database.methods import engine, connection
from database.models import (TypeTamagochi,
                             TypeFood,
                             Food,
                             Reaction,
                             HidingPlace,
                             Base)

from utilites.logger import get_logger

logger = get_logger('create_and_populate_db', file_level=logging.DEBUG, console_level=logging.INFO)


async def initialize_database() -> None:
    """ Создает таблицы в бд и заполняет их данными для развертывания приложения в Docker """

    await create_tables()
    await create_trigger_and_func()
    await create_trigger_sick()
    await populate_type_food_table()
    await populate_food_table()
    await populate_reaction_table()
    await populate_hiding_place_table()
    await populate_type_tamagochi()


async def create_tables() -> None:
    """ Создает все таблицы в базе данных """

    try:
        async with engine.begin() as conn:
            logger.debug(f'Создание таблиц...')
            await conn.run_sync(Base.metadata.create_all)
        logger.debug('Таблицы успешно созданы')
    except Exception as e:
        logger.debug(f'Ошибка при создании таблиц: {e}')


async def create_trigger_and_func() -> None:
    """ Создает триггер для параметров питомца при первом создании БД """

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
            logger.debug('Триггер для user_tamagochi успешно создан')
    except Exception as e:
        logger.error(f'Ошибка при создании триггера: {e}')


async def create_trigger_sick() -> None:
    """ Создает триггер для здоровья питомца.
        Если здоровье будет ≤ 0, то питомец заболеет
    """

    create_func_sql = """
    CREATE OR REPLACE FUNCTION check_health() 
    RETURNS TRIGGER AS $$ 
    BEGIN 
        IF NEW.health <= 0 THEN 
            NEW.sick = TRUE; 
        END IF; 
        RETURN NEW; 
    END; 
    $$ LANGUAGE plpgsql;
    """

    create_trigger_sql = """
        CREATE TRIGGER check_health_trigger 
        BEFORE UPDATE ON user_tamagochi 
        FOR EACH ROW EXECUTE FUNCTION check_health(); 
        """

    try:
        async with engine.begin() as conn:
            await conn.execute(text(create_func_sql))
            await conn.execute(text(create_trigger_sql))
            logger.debug('Триггер sick для user_tamagochi успешно создан')
    except Exception as e:
        logger.error(f'Ошибка при создании триггера: {e}')


@connection
async def populate_type_food_table(session: AsyncSession) -> None:
    """ Заполняет таблицу type_food при первом создании БД """

    file_path = os.path.join(os.path.dirname(__file__), 'type_food.json')
    with open(file_path, 'r', encoding='utf-8') as js:
        data = json.load(js)
    types_food = data.get('responses', [])

    try:
        for type_food in types_food:
            new = TypeFood(name=type_food['name'],
                           up_state_name=type_food['up_state_name'],
                           up_state_point=type_food['up_state_point'],
                           down_state_name=type_food['down_state_name'],
                           down_state_point=type_food['down_state_point'],)
            session.add(new)
        await session.commit()
        logger.debug('Таблица type_food успешно заполнена')
    except Exception as e:
        logger.error(f'Ошибка при заполнении таблицы type_food: {e}')


@connection
async def populate_food_table(session: AsyncSession) -> None:
    """ Заполняет таблицу food при первом создании БД """

    file_path = os.path.join(os.path.dirname(__file__), 'foods.json')
    with open(file_path, 'r', encoding='utf-8') as js:
        data = json.load(js)
    foods = data.get('responses', [])

    try:
        for food in foods:
            new = Food(name=food['name'], type_food_id=food['type_food_id'])
            session.add(new)
        await session.commit()
        logger.debug('Таблица food успешно заполнена')
    except Exception as e:
        logger.error(f'Ошибка при заполнении таблицы food: {e}')


@connection
async def populate_reaction_table(session: AsyncSession) -> None:
    """ Заполняет таблицу reaction """

    file_path = os.path.join(os.path.dirname(__file__), 'pet_reaction.json')
    with open(file_path, 'r', encoding='utf-8') as js:
        data = json.load(js)
    action_and_reaction = data.get('responses', [])

    try:
        for act_react in action_and_reaction:
            action = act_react['action']
            reactions = act_react['reaction']
            for react in reactions:
                new = Reaction(action=action, reaction=react)
                session.add(new)
        await session.commit()
        logger.debug('Таблица reaction успешно заполнена')
    except Exception as e:
        logger.error(f'Ошибка при заполнении таблицы reaction: {e}')


@connection
async def populate_hiding_place_table(session: AsyncSession) -> None:
    """ Заполняет таблицу hiding_place """

    file_path = os.path.join(os.path.dirname(__file__), 'places.json')
    with open(file_path, 'r', encoding='utf-8') as js:
        data = json.load(js)
    places_and_reactions = data.get('hiding_places', [])

    try:
        for place_react in places_and_reactions:
            new = HidingPlace(place=place_react['place'], reaction_found=place_react['reaction_found'])
            session.add(new)
        await session.commit()
        logger.debug('Таблица hiding_place успешно заполнена')
    except Exception as e:
        logger.error(f'Ошибка при заполнении таблицы hiding_place: {e}')


@connection
async def populate_type_tamagochi(session: AsyncSession) -> None:
    """ Заполняет таблицу type_tamagochi """

    file_path = os.path.join(os.path.dirname(__file__), 'pet_types.json')
    with open(file_path, 'r', encoding='utf-8') as js:
        data = json.load(js)
    pet_types = data.get('types', [])

    try:
        for pet_type in pet_types:
            new = TypeTamagochi(name=pet_type['name'],
                                health_max=pet_type['health_max'],
                                happiness_max=pet_type['happiness_max'],
                                grooming_max=pet_type['grooming_max'],
                                energy_max=pet_type['energy_max'],
                                hunger_max=pet_type['hunger_max'],
                                image_url=pet_type['image_url'],
                                )
            session.add(new)
        await session.commit()
        logger.debug('Таблица type_tamagochi успешно заполнена')
    except Exception as e:
        logger.error(f'Ошибка при заполнении таблицы type_tamagochi: {e}')
