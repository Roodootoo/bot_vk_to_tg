import os
import sys
import configparser
from time import sleep
import logging

from app.vkontakte_api import VkAPI
from app.telegram_api import TelegramBot
from app.post_processor import PostProcessor

# Настройка логгера
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
file_handler = logging.FileHandler('app.log')
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Считываем переменных окружения
config_path = os.path.join(sys.path[0], '.env')
config = configparser.ConfigParser()
config.read(config_path)
DOMAIN_VK = config.get('VK', 'DOMAIN')
COUNT_VK = config.get('VK', 'COUNT')
VK_TOKEN = config.get('VK', 'TOKEN', fallback=None)
BOT_TOKEN = config.get('Telegram', 'BOT_TOKEN')
CHANNEL = config.get('Telegram', 'CHANNEL')
INCLUDE_LINK = config.getboolean('Settings', 'INCLUDE_LINK')
PREVIEW_LINK = config.getboolean('Settings', 'PREVIEW_LINK')
REPOSTS = config.getboolean('Settings', 'REPOSTS')

# Проверка обязательных переменных окружения
if not VK_TOKEN or not BOT_TOKEN or not CHANNEL:
    logger.critical("Одна или несколько обязательных переменных окружения не установлены.")
    sys.exit(1)


if __name__ == '__main__':
    vk_api = VkAPI(VK_TOKEN, DOMAIN_VK, logger)
    telegram_bot = TelegramBot(BOT_TOKEN, CHANNEL, logger)
    post_processor = PostProcessor(telegram_bot, vk_api, INCLUDE_LINK, PREVIEW_LINK, REPOSTS, logger)

    while True:
        # Получение данных из ВК
        vk_data = vk_api.get_data(COUNT_VK)
        vk_data = reversed(vk_data['items'])

        # Обработка и отправка постов в Telegram
        for post in vk_data:
            text, images = post_processor.process_post(post, config.get('Settings', 'LAST_ID'))
            if not text:
                continue

            telegram_bot.send_text_message(text, PREVIEW_LINK)
            if images:
                telegram_bot.send_image_messages(images)

            # Запись отправленного id в файл
            config.set('Settings', 'LAST_ID', str(post['id']))
            last_id = str(post['id'])
            with open(config_path, "w") as config_file:
                config.write(config_file)

            # Ожидание на отправку следующего нового поста в Telegram
            sleep(60)

        # Ожидание на проверку следующего нового поста в ВК
        sleep(3600)
