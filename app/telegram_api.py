from time import sleep

import telebot
from telebot.types import InputMediaPhoto

from app.post_processor import PostProcessor


class TelegramBot:
    def __init__(self, bot_token, channel, logger):
        self.bot = telebot.TeleBot(bot_token)
        self.channel = channel
        self.logger = logger

    def send_text_message(self, text, preview_link):
        # Отправка текстовых сообщений
        text = PostProcessor.clean_text(text)

        if text == '':
            self.logger.info('Нет текста для отправки')
        else:
            # В телеграмме есть ограничения на длину одного сообщения в 4096 символ, разбиваем длинные на части
            for msg in PostProcessor.split_text(text):
                self.bot.send_message(self.channel, msg, disable_web_page_preview=not preview_link)
            self.logger.info('Текст отправлен')

    def send_image_messages(self, images):
        # Отправка изображений
        if not images:
            self.logger.info('Нет картинок для отправки')

        image_urls = [self.get_image_url(img) for img in images]

        # При ограничении времени запросов в Telegram включаем ждуна
        success = False

        # Блоки по 10 фотографий максимум
        chunk_size = 10
        image_chunks = [image_urls[i:i + chunk_size] for i in range(0, len(image_urls), chunk_size)]

        for chunk in image_chunks:
            while not success:
                try:
                    self.bot.send_media_group(self.channel, map(lambda url: InputMediaPhoto(url), chunk))
                    success = True
                    self.logger.info('Фото отправлены')
                except Exception:
                    self.logger.debug("Ошибка при отправке медиа, ждём 60 секунд...")
                    sleep(60)

        if not success:
            self.logger.error(f'Ошибка при отправке медиа, общее количество = {len(image_urls)}')

    def get_image_url(self, image):
        # Выбор наибольшего размера изображения
        max_size_image = max(image["sizes"], key=lambda size: size["type"])

        # Получение URL выбранного изображения
        image_url = max_size_image["url"]

        return image_url
