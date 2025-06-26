""" Настройка логирования """

import logging
import os

LOG_DIR = 'logs'
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)


def get_logger(name: str, file_level=logging.DEBUG, console_level=logging.INFO) -> logging.Logger:
    """ Создает и возвращает логгер с заданным именем и уровнями логирования """

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    file_handler = logging.FileHandler(os.path.join(LOG_DIR, f"{name}.log"))
    file_handler.setLevel(file_level)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(console_level)
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)

    logger.propagate = False
    return logger


def setup_default_logging():
    """ Устанавливает базовую конфигурацию логирования для всего приложения """

    logging.getLogger('httpx').setLevel(logging.INFO)

    logging.getLogger('sqlalchemy').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.pool').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.dialects').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.orm').setLevel(logging.WARNING)
