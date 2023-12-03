import sys
from decouple import config
from get_docker_secret import get_docker_secret
from time import sleep
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

# Считываем переменных окружения
VK_TOKEN = get_docker_secret('token_vk', default="")
BOT_TOKEN = get_docker_secret('token_tg', default="")
COUNT_VK = config('COUNT', default=10)
DOMAIN_VK = config('DOMAIN', default="")
CHANNEL = config('CHANNEL', default="")
INCLUDE_LINK = config('INCLUDE_LINK', default=True, cast=bool)
PREVIEW_LINK = config('PREVIEW_LINK', default=False, cast=bool)
REPOSTS = config('REPOSTS', default=True, cast=bool)
last_id = config('LAST_ID', default=0)


# Проверка обязательных переменных окружения
if not VK_TOKEN or not BOT_TOKEN or not CHANNEL:
    logger.critical("Одна или несколько обязательных переменных окружения не установлены!")
    sys.exit(1)


if __name__ == '__main__':
    vk_api = VkAPI(VK_TOKEN, DOMAIN_VK, logger)
    telegram_bot = TelegramBot(BOT_TOKEN, CHANNEL, logger)
    post_processor = PostProcessor(telegram_bot, vk_api, INCLUDE_LINK, PREVIEW_LINK, REPOSTS, logger)

    while True:
        # Получение данных из ВК
        vk_data = vk_api.get_data(COUNT_VK)
        vk_data = reversed(vk_data['items'])
        logger.info("Делаю проверку ВК...")

        # Обработка и отправка постов в Telegram
        for post in vk_data:
            # Пропуск уже опубликованных
            if int(post['id']) <= int(last_id):
                # logger.info(f"Пост уже опубликован  {post['id']}, LAST_ID = {last_id}")
                continue

            # Пропуск перепостов
            if not REPOSTS and 'copy_history' in post:
                logger.info(f"Пропущен пост {post['id']}, так как перепост отключен")
                continue

            logger.info(f"Отправка поста {post['id']}")

            text, images = post_processor.process_post(post, last_id)

            if text:
                telegram_bot.send_text_message(text, PREVIEW_LINK)

            if images:
                telegram_bot.send_image_messages(images)

            # Запись отправленного id в файл
            post_id = str(post['id'])
            last_id = post_id

            with open('.env', 'r') as env_file:
                lines = env_file.readlines()

            with open('.env', 'w') as env_file:
                for line in lines:
                    if line.startswith('LAST_ID'):
                        env_file.write(f'LAST_ID = {last_id}\n')
                        logger.info(f"Обновлён LAST_ID = {last_id}")
                    else:
                        env_file.write(line)

            # Ожидание на отправку следующего нового поста в Telegram
            logger.info("Жду 1 минуту перед следующей проверкой")
            sleep(60)

        # Ожидание на проверку следующего нового поста в ВК
        logger.info("..Сплю 1 час")
        sleep(3600)

