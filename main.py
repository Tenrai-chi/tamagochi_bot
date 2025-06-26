""" Основной файл запуска в докере """

from bot.bot import PetBot
from utilites.logger import setup_default_logging

setup_default_logging()

if __name__ == '__main__':
    bot = PetBot()
    bot.run()
