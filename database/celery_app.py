from celery import Celery
from models import UserTamagochi
from methods import session_local

app = Celery('tasks', broker='pyamqp://guest@localhost//')

@app.task
def decrease_pet_stats():
    with session_local() as sess:
        pets = sess.query(UserTamagochi).all()
        for pet in pets:
            # Уменьшение статов
            pass
        sess.commit()
