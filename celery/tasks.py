""" Настройка задачи для celery """

import logging

from asgiref.sync import async_to_sync
from celery import shared_task

from database.pet_condition_update import reduction_stats
from utilites.logger import get_logger


logger = get_logger('tasks', file_level=logging.DEBUG, console_level=logging.INFO)


@shared_task
def update_pet_condition():
    try:
        logger.debug('Задача update_pet_condition запущена!')
        async_to_sync(reduction_stats)()
        logger.debug('Задача update_pet_condition завершена!')
    except Exception as e:
        logger.error(f'Ошибка при выполнении задачи update_pet_condition: {e}')
