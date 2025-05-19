import os
import sys
from decouple import config
from time import sleep
from datetime import datetime
import logging

from app.vkontakte_api import VkAPI
from app.telegram_api import TelegramBot
from app.post_processor import PostProcessor

# Настройка логгера
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(logger_format)
logger.addHandler(console_handler)

# Читаем токены из файлов
VK_TOKEN = BOT_TOKEN = ""
with open(os.environ.get('TOKEN_VK_FILE'), 'r') as f:
    VK_TOKEN = f.read().strip()
with open(os.environ.get('TOKEN_TELEGRAM_FILE'), 'r') as f:
    BOT_TOKEN = f.read().strip()

# Считываем переменных окружения
COUNT_VK = config('COUNT', default=10)
DOMAIN_VK = config('DOMAIN', default="")
CHANNEL = config('CHANNEL', default="")
INCLUDE_LINK = config('INCLUDE_LINK', default=True, cast=bool)
PREVIEW_LINK = config('PREVIEW_LINK', default=False, cast=bool)
REPOSTS = config('REPOSTS', default=True, cast=bool)
WAIT_TIME = int(config('WAIT_TIME', default=3600))

# Дата последнего опубликованного поста
with open('last_post/date', 'r') as date_file:
    last_date = date_file.read().strip()


# Проверка обязательных переменных окружения
if not VK_TOKEN or not BOT_TOKEN or not CHANNEL:
    try:
        with open("tokens/token_vk", 'r') as token_vk:
            VK_TOKEN = token_vk.read().rstrip('\n')
    except IOError as e:
        logger.critical("Одна или несколько обязательных переменных окружения не установлены!")
        sys.exit(1)

    try:
        with open("tokens/token_tg", 'r') as token_tg:
            BOT_TOKEN = token_tg.read().rstrip('\n')
    except IOError as e:
        logger.critical("Одна или несколько обязательных переменных окружения не установлены!")
        sys.exit(1)


def check_post(post):
    # Пропуск уже опубликованных
    if int(post['date']) <= int(last_date):
        logger.info(f"Пост уже опубликован  {post['id']}")
        return 0

    # Пропуск перепостов
    if not REPOSTS and 'copy_history' in post:
        logger.info(f"Пропущен пост {post['id']}, так как перепост отключен")
        return 0

    logger.info(f"Отправка поста {post['id']}")

    text, images = post_processor.process_post(post)
    print(f'{text}')
    
    if text:
        telegram_bot.send_text_message(text, PREVIEW_LINK)
    
    if images:
        telegram_bot.send_image_messages(images)

    return 1



if __name__ == '__main__':

    vk_api = VkAPI(VK_TOKEN, DOMAIN_VK, logger)
    telegram_bot = TelegramBot(BOT_TOKEN, CHANNEL, logger)
    post_processor = PostProcessor(telegram_bot, vk_api, INCLUDE_LINK, PREVIEW_LINK, REPOSTS, logger)

    while True:
        # Получение данных из ВК
        vk_data = vk_api.get_data(COUNT_VK)['items']

        if 'is_pinned' in vk_data[0]:
            check_post(vk_data[0])

        vk_data = reversed(vk_data)
        logger.info("Делаю проверку ВК...")

        # Обработка и отправка постов в Telegram
        for post in vk_data:
            post_date = int(post['date'])
            logger.info(f"Проверяю загруженные посты...  {datetime.fromtimestamp(post_date).strftime('%d.%m.%Y')}")

            result = check_post(post)
            
            # Если пост был опубликован, то перезаписываем date опубликованных постов в файл
            if result:
                last_date = str(post_date)
                with open('last_post/date', 'w') as date_file:
                    date_file.write(last_date)
                    logger.info(f"Обновлён LAST_DATE = {last_date}")

                # Ожидание на отправку следующего нового поста в Telegram
                logger.info("Жду 1 минуту перед следующей проверкой")
                sleep(60)

        # Ожидание на проверку следующего нового поста в ВК
        logger.info("..Сплю " + str(WAIT_TIME) + " секунд")
        sleep(WAIT_TIME)

