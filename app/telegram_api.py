from typing import List
from time import sleep
import logging
import telebot
from telebot.types import InputMediaPhoto

from app.post_processor import PostProcessor


class TelegramBot:
    def __init__(self, bot_token: str, channel: str, logger: logging.Logger):
        """Инициализируем Telegram-бот.

        Args:
            bot_token (str): Токен Telegram-бота.
            channel (str): ID или имя канала Telegram.
            logger (logging.Logger): Логгер для вывода сообщений.
        """
        self.bot = telebot.TeleBot(bot_token)
        self.channel = channel
        self.logger = logger

    def send_text_message(self, text: str, preview_link: bool) -> None:
        """Отправляем текстовое сообщение в Telegram.

        Args:
            text (str): Текст сообщения.
            preview_link (bool): Включать ли предпросмотр ссылок.
        """
        text = PostProcessor.clean_text(text)

        if not text:
            self.logger.info('Нет текста для отправки')
            return

        # В телеграмме есть ограничения на длину одного сообщения в 4096 символ, разбиваем длинные на части
        for msg in PostProcessor.split_text(text):
            try:
                self.bot.send_message(self.channel, msg, disable_web_page_preview=not preview_link)
                self.logger.info('Текст отправлен')
            except telebot.apihelper.ApiException as e:
                self.logger.error(f"Ошибка отправки текста: {e}")
                sleep(60)

    def send_image_messages(self, images: List[dict]) -> None:
        """Отправляем изображения в Telegram.

        Args:
            images (List[dict]): Список словарей с данными изображений.
        """
        if not images:
            self.logger.info('Нет картинок для отправки')
            return

        image_urls = [self.get_image_url(img) for img in images]

        # При ограничении времени запросов в Telegram включаем ждуна
        success = False

        # Блоки по 10 фотографий максимум
        chunk_size = 10
        image_chunks = [image_urls[i:i + chunk_size] for i in range(0, len(image_urls), chunk_size)]

        for chunk in image_chunks:
            while not success:
                try:
                    self.bot.send_media_group(self.channel, list(map(lambda url: InputMediaPhoto(url), chunk)))
                    success = True
                    self.logger.info('Фото отправлены')
                # except Exception:
                except telebot.apihelper.ApiException as e:
                    self.logger.debug(f"Ошибка при отправке медиа, ждём 60 секунд... {e}")
                    sleep(60)

        if not success:
            self.logger.error(f'Ошибка при отправке медиа, общее количество = {len(image_urls)}')

    def get_image_url(self, image: dict) -> str:
        """Получаем URL изображения наибольшего размера.

        Args:
            image (dict): Данные изображения из VK API.

        Returns:
            str: URL изображения.
        """
        max_size_image = max(image["sizes"], key=lambda size: size["type"])
        return max_size_image["url"]
