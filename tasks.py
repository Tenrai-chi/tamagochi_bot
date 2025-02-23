""" Настройка задачи для celery """

from asgiref.sync import async_to_sync
from celery import shared_task

from database.pet_condition_update import reduction_stats
from utilites.logger import logger


@shared_task
def update_pet_condition():
    try:
        logger.info('Задача update_pet_condition запущена!')
        async_to_sync(reduction_stats)()
        logger.info('Задача update_pet_condition завершена!')
    except Exception as e:
        logger.error(f'Ошибка при выполнении задачи update_pet_condition: {e}')
