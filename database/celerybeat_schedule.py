from celery import Celery
from celery.schedules import crontab

app = Celery('tasks', broker='pyamqp://guest@localhost//')

app.conf.beat_schedule = {
    'decrease-pet-stats-every-30-minutes': {
        'task': 'celery_app.decrease_pet_stats',
        'schedule': crontab(minute='*/30'),  # Каждые 30 минут
    },
}