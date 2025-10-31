from __future__ import annotations
from typing import Tuple, List, Dict, Any, TYPE_CHECKING
import re
import logging

if TYPE_CHECKING:
    from app.vkontakte_api import VkAPI
    from app.telegram_api import TelegramBot


class PostProcessor:
    def __init__(
        self,
        bot: TelegramBot,
        vk_api: VkAPI,
        include_link: bool,
        preview_link: bool,
        reposts: bool,
        logger: logging.Logger
    ):
        """Инициализируем обработчик постов.

        Args:
            bot (TelegramBot): Telegram-бот.
            vk_api (VkAPI): VK API клиент.
            include_link (bool): Включать ли ссылки в посты.
            preview_link (bool): Включать ли предпросмотр ссылок.
            reposts (bool): Разрешать ли репосты.
            logger (logging.Logger): Логгер для вывода сообщений.
        """
        self.bot = bot
        self.vk_api = vk_api
        self.include_link = include_link
        self.preview_link = preview_link
        self.reposts = reposts
        self.logger = logger

    def process_post(self, post: Dict[str, Any]) -> Tuple[str, List[Dict]]:
        """Обрабатываем пост ВК и возвращаем текст и изображения для отправки.

        Args:
            post (Dict[str, Any]): Данные поста из VK API.

        Returns:
            Tuple[str, List[Dict]]: Текст сообщения и список изображений.
        """
        text = post.get('text', '')
        copy_history_text = ''
        images = []
        links = []

        # Проверка, есть ли аттачи к посту
        if 'attachments' in post:
            have_video = False
            for attach in post['attachments']:
                if attach['type'] == 'photo':
                    images.append(attach['photo'])
                elif attach['type'] == 'video' and not have_video:
                    links.insert(0, '# Для просмотра видео, пожалуйста, перейдите по ссылке ниже ')
                    have_video = True
                    if 'player' in attach['video']:
                        links.append(video['player'])
                else:
                    for (key, value) in attach.items():
                        if key != 'type' and 'url' in value:
                            links.append(value['url'])

        post_url = f"https://vk.ru/{self.vk_api.domain_vk}?w=wall{str(post['owner_id'])}_{str(post['id'])}"

        # Есть соавторство поста
        if 'coowners' in post:
            text = ""
            copy_history_text = post['text']

            # Добавление строки с савторами поста
            owner_list = post['coowners']['list']
            owner_names = [self.vk_api.get_owner_name_by_id(x['owner_id']) for x in owner_list]
            owners = " & ".join(owner_names)
            
            copy_history_text = f"\n \N{speech balloon} {owners}:\n{copy_history_text}"
                    
        # Это репост другой записи
        if 'copy_history' in post:
            copy_history = post['copy_history'][0]
            copy_history_text = copy_history['text']

            # Добавление строки с автором репоста
            owner_id = int(copy_history['owner_id'])
            owner_name = self.vk_api.get_owner_name_by_id(owner_id)
            copy_history_text = f"\n \N{speech balloon} {owner_name}:\n{copy_history_text}"

            # Проверка, есть ли аттачи у репоста
            if 'attachments' in copy_history:
                have_video = False
                for attach in copy_history['attachments']:
                    if attach['type'] == 'photo':
                        images.append(attach['photo'])
                    elif attach['type'] == 'video' and have_video is False:
                        video = attach['video']
                        if 'player' in video:
                            links.append(video['player'])
                        elif self.include_link:
                            # пока с видео бяда у ВК, player не у всех есть
                            links.append('# Для просмотра видео, пожалуйста, перейдите по ссылке ниже ')
                            have_video = True

                    elif self.include_link:
                        if attach['type'] == 'link':
                            links.append(attach['link']['url'])
                        else:
                            for key, value in attach.items():
                                if key != 'type' and 'url' in value:
                                    links.append(value['url'])

        # Добавление ссылок, если надо
        if self.include_link:
            links.append(f"\n ВК: {post_url} \n")

        # Сборка всего текста
        text = '\n'.join([text] + [copy_history_text] + links)
        self.logger.info(f"Обработан пост: {post_url}")

        return text, images

    @staticmethod
    def clean_text(text: str) -> str:
        """Очищаем текст от ВК-ссылок вида [id123| ] и [club123| ].

        Args:
            text (str): Исходный текст.

        Returns:
            str: Очищенный текст.
        """
        str_id = "\[id"  # noqa: W605
        str_club = "\[club"  # noqa: W605
        str_end = "|"
        result = [_.start() for _ in re.finditer(str_id, text)]
        result = result + [_.start() for _ in re.finditer(str_club, text)]
        result.sort()
        correct = 0
        for ind in result:
            ind = ind - correct
            res = text.find(str_end, ind)
            correct = correct + (res - ind + 2)
            text = text[:int(ind)] + text[int(res) + 1:]
            text = text.replace(']', '', 1)

        return text

    @staticmethod
    def split_text(text: str) -> List[str]:
        """Разделяем текст на части, соответствующие ограничениям Telegram.

        Args:
            text (str): Исходный текст.

        Returns:
            List[str]: Список частей текста.
        """
        message_breakers = [':', '\n']
        max_message_length = 4096

        if len(text) <= max_message_length:
            return [text]
        
        last_index = max(
            map(lambda separator: text.rfind(separator, 0, max_message_length), message_breakers))
        good_part = text[:last_index]
        bad_part = text[last_index + 1:]
        return [good_part] + PostProcessor.split_text(bad_part)
