import logging
from typing import Union

LOG_FORMAT = "%(name)s - %(levelname)s - %(message)s"


def setup_logger(name: str, level: Union[str, int] = logging.DEBUG) -> logging.Logger:
    """
    Создаёт и настраивает логгер с заданным именем и уровнем логирования.

    Args:
        name (str): Имя логгера.
        level (str | int, optional): Уровень логирования в формате строки ('DEBUG', 'INFO' и т.д.) или числа (10, 20 и т.д.).
            По умолчанию logging.DEBUG.

    Returns:
        logging.Logger: Настроенный логгер.
    """
    # Если передана строка, конвертируем в число
    if isinstance(level, str):
        level = level.upper()
        if level not in logging._nameToLevel:
            raise ValueError(f"Invalid log level: {level}")
        level = logging._nameToLevel[level]

    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(LOG_FORMAT)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    logger.setLevel(level)
    return logger
