import tasks
from celery import Celery
from utilites.logger import logger

app = Celery('tamagochi_bot',
             broker='amqp://guest:guest@localhost:5672//')

app.conf.update(
    task_serializer='json',
    result_serializer='json',
    accept_content=['json'],
    timezone='Europe/Moscow',  # Замените на ваш часовой пояс
    enable_utc=False,
    result_expires=3600,  # Срок хранения результатов (1 час)
)

app.conf.beat_schedule = {
    'update-pet-condition-every-30-minutes': {
        'task': 'tasks.update_pet_condition',
        'schedule': 30.0,  # Каждые 30 минут (1800.0 секунд)
    },
}

if __name__ == '__main__':
    logger.info("Запуск celery app!")
    app.start()
