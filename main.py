""" Основной файл запуска в докере """

import asyncio
import bot
from database.methods import initialize_database

if __name__ == '__main__':
    asyncio.run(initialize_database())
    bot.main()
