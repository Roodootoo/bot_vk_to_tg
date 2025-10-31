import os
import sys
from typing import Optional
from decouple import config
from time import sleep
from datetime import datetime
import logging

from app.vkontakte_api import VkAPI
from app.telegram_api import TelegramBot
from app.post_processor import PostProcessor


def setup_logger() -> logging.Logger:
    """Настраиваем логгер для приложения.

    Returns:
        logging.Logger: Настроенный логгер.
    """
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    logger_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(logger_format)
    logger.addHandler(console_handler)
    return logger


def read_tokens(file_path: str, token_name: str, logger: logging.Logger) -> str:
    """ Читаем токены из файлов

    Args:
        file_path (str): Путь к файлу с токеном.
        token_name (str): Имя токена для логирования.
        logger (logging.Logger): Логгер для вывода сообщений.

    Returns:
        str: Содержимое файла токена.

    Raises:
        SystemExit: Если файл не удалось прочитать.
    """
    try:
        with open(file_path, 'r') as file:
            return file.read().strip()
    except IOError as e:
        logger.critical(f"Не удалось прочитать {token_name}: {e}")
        sys.exit()


def read_last_date(file_path: str, logger: logging.Logger) -> Optional[int]:
    """Читаем дату последнего опубликованного поста 
    
    Args:
        file_path (str): Путь к файлу.
        logger (logging.Logger): Логгер для вывода сообщений.

    Returns:
        Optional (int): Unix timestamp последней даты или None, если файл пустой или недоступен.
    """
    try:
        with open(file_path, 'r') as file:
            content = file.read().strip()
            return int(content) if content else None
    except (IOError, ValueError) as e:
        logger.warning(f"Не удалось прочитать дату последнего поста: {e}")
        return None


def read_posts_list(file_path: str, logger: logging.Logger) -> Optional[str]:
    """Читаем список постов для загрузки
    
    Args:
        file_path (str): Путь к файлу.
        logger (logging.Logger): Логгер для вывода сообщений.

    Returns:
        Optional (str): Cтроку со списком постов для загрузки
    """
    try:
        with open(file_path, 'r') as file:
            return file.read().strip()
    except (IOError, ValueError) as e:
        logger.warning(f"Не удалось прочитать дату последнего поста: {e}")
        return None


def write_last_date(file_path: str, date: int, logger: logging.Logger) -> None:
    """Записываем дату последнего поста в файл.

    Args:
        file_path (str): Путь к файлу.
        date (int): Unix timestamp для записи
        logger (logging.Logger): Логгер для вывода сообщений.
    """
    try:
        _write_file(file_path, str(date), logger, success_msg=f"Обновлена дата последнего поста: {date}")
    except IOError as e:
        logger.error(f"Не удалось записать файл {file_path} : {e}")


def write_posts_list(file_path: str, posts_list: str, logger: logging.Logger) -> None:
    """Записываем дату последнего поста в файл.

    Args:
        file_path (str): Путь к файлу.
        posts (str): Пустая строка
        logger (logging.Logger): Логгер для вывода сообщений.
    """
    try:
        _write_file(file_path, posts_list, logger, f"Загрузили список постов, очищаем файл: {posts_list}")
    except IOError as e:
        logger.error(f"Не удалось записать файл {file_path} : {e}")


def _write_file(
    file_path: str,
    content: str,
    logger: logging.Logger,
    success_msg: str
) -> None:
    """Внутренняя функция записи с единым обработчиком ошибок."""
    try:
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(content)
            logger.info(success_msg)
    except IOError as e:
        logger.error(f"Не удалось записать файл {file_path}: {e}")



def check_post(
    post: dict,
    last_date: Optional[int],
    post_processor: PostProcessor,
    telegram_bot: TelegramBot,
    logger: logging.Logger,
    reposts: bool
) -> bool:
    """Проверяем и отправляем пост, если он новый и соответствует настройкам.

    Args:
        post (dict): Данные поста из ВК.
        last_date (Optional[int]): Дата последнего отправленного поста (Unix timestamp).
        post_processor (PostProcessor): Обработчик постов.
        telegram_bot (TelegramBot): Бот для отправки сообщений.
        logger (logging.Logger): Логгер для вывода сообщений.
        reposts (bool): Разрешать ли отправку репостов.

    Returns:
        bool: True, если пост отправлен, иначе False.
    """
    post_date = int(post['date'])
    # Пропуск уже опубликованных
    if last_date and post_date <= last_date:
        logger.info(f"Пост уже опубликован  {post['id']} : {last_date} > {post_date}")
        return False

    # Пропуск перепостов
    if not reposts and 'copy_history' in post:
        logger.info(f"Пропущен пост {post['id']}, так как перепост отключен")
        return False

    logger.info(f"Отправка поста {post['id']}")
    text, images = post_processor.process_post(post)
    
    if text:
        telegram_bot.send_text_message(text, post_processor.preview_link)
    
    if images:
        telegram_bot.send_image_messages(images)

    return True


def main() -> None:
    """Основная функция для запуска бота."""
    logger = setup_logger()

    vk_token = read_tokens(os.environ.get('TOKEN_VK_FILE', ''), 'VK_TOKEN', logger)
    bot_token = read_tokens(os.environ.get('TOKEN_TELEGRAM_FILE', ''), 'BOT_TOKEN', logger)
    channel = config('CHANNEL', default="")
    # Проверка обязательных переменных окружения
    if not all([vk_token, bot_token, channel]):
        logger.critical("Одна или несколько обязательных переменных окружения не установлены!")
        sys.exit(1)

    # Считываем переменных окружения
    count_vk = config('COUNT', default=10, cast=int)
    domain_vk = config('DOMAIN', default='')
    include_link = config('INCLUDE_LINK', default=True, cast=bool)
    preview_link = config('PREVIEW_LINK', default=False, cast=bool)
    reposts = config('REPOSTS', default=True, cast=bool)
    wait_time = config('WAIT_TIME', default=3600, cast=int)

    # Инициализируем API и обработчики
    vk_api = VkAPI(vk_token, domain_vk, logger)
    telegram_bot = TelegramBot(bot_token, channel, logger)
    post_processor = PostProcessor(telegram_bot, vk_api, include_link, preview_link, reposts, logger)

    # Читаем дату последнего поста
    last_date = read_last_date('last_post/date', logger)

    # Если надо загружаем только выборочные посты из файла:
    posts = read_posts_list('last_post/posts', logger)  # Строка вида: -218511206_1625,-218511206_1628,-218511206_1630

    while True:
        try:
            # Получаем список необходимых постов для загрузки
            if posts:
                vk_data = vk_api.get_little_data(posts)['items']
                logger.info("Делаю проверку списка конкретных постов ВК из файла...")

            # Получаем свежие данные из ВК
            else:
                vk_data = vk_api.get_data(count_vk)['items']
                logger.info("Делаю проверку новых постов ВК...")

                if 'is_pinned' in vk_data[0]:
                    check_post(vk_data[0], last_date, post_processor, telegram_bot, logger, reposts)
                    logger.info(f"Пост закреплён {vk_data[0]['id']}")

                vk_data = reversed(vk_data)
            
            # Обработка и отправка постов в Telegram
            for post in vk_data:
                post_date = int(post['date'])
                logger.info(f"Проверяю загруженные посты...  {datetime.fromtimestamp(post_date).strftime('%d.%m.%Y')}")

                # Если пост был опубликован, то перезаписываем date опубликованных постов в файл
                if check_post(post, last_date, post_processor, telegram_bot, logger, reposts):
                    last_date = post_date
                    write_last_date('last_post/date', str(last_date), logger)
                    # Ожидание на отправку следующего нового поста в Telegram
                    if posts:
                        logger.info(f" Для списка постов жду 8 часов, чтобы не спамить в тг старыми постами...")
                        sleep(28800) # чтобы не спамить часто постами ждём 8 часов
                    sleep(60)
            
            if posts:
                posts = ''
                write_posts_list('last_post/posts', posts, logger)

            # Ожидание на проверку следующего нового поста в ВК
            logger.info(f"..Сплю {wait_time} секунд перед следующей проверкой ВК")
            sleep(wait_time)

        except Exception as e:
            logger.error(f"Ошибка в основном цикле: {e}")
            sleep(60)

if __name__ == '__main__':
    main()
