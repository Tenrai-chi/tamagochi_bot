""" Настройка Celery. Используется для запуска celery beat и celery worker """

import logging

from celery import Celery
from utilites.logger import get_logger

logger = get_logger('celery_app', file_level=logging.DEBUG, console_level=logging.INFO)

app = Celery('tamagochi_bot',
             broker='amqp://guest:guest@localhost:5672//')

app.conf.update(
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='Europe/Moscow',
    enable_utc=False,
    result_expires=3600,
)

app.conf.broker_connection_retry_on_startup = True

app.conf.beat_schedule = {
    'update-pet-condition-every-30-minutes': {
        'task': 'tasks.update_pet_condition',
        'schedule': 1800.0,  # Каждые 30 минут
    },
}

if __name__ == '__main__':
    logger.info('Запуск celery app')
    app.start()
