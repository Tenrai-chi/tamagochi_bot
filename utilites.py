""" Дополнительные функции """

from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes


def validation_name(func):
    """ Валидатор имени """

    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        name = update.message.text
        if not name:
            await update.message.reply_text('Такое имя не подходит')
            return
        if len(name) > 30:
            await update.message.reply_text('Извините, имя слишком длинное')
            return
        return await func(update, context)  # Вызываем оригинальную функцию, если имя валидно
    return wrapper
