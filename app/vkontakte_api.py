from typing import Dict, Any
import logging
import requests


class VkAPI:
    def __init__(self, vk_token: str, domain_vk: str, logger: logging.Logger):
        """Инициализируем VK API.

        Args:
            vk_token (str): Токен доступа ВК.
            domain_vk (str): Домен группы ВК.
            logger (logging.Logger): Логгер для вывода сообщений.
        """
        self.vk_token = vk_token
        self.domain_vk = domain_vk
        self.logger = logger

    def get_data(self, count_vk: int) -> Dict[str, Any]:
        """Получаем посты из ВК.

        Args:
            count_vk (int): Количество постов для загрузки.

        Returns:
            Dict[str, Any]: Данные постов из VK API.

        Raises:
            requests.RequestException: Если запрос к API не удался.
        """
        try:
            url = 'https://api.vk.ru/method/wall.get'
            params = {
                'access_token': self.vk_token,
                'domain': self.domain_vk,
                'extended': 1,
                'count': count_vk,
                'v': '5.199'
            }
            response = requests.get(url, params=params).json()
            if 'response' not in response:
                self.logger.error(f"Ошибка VK API: {response.get('error', 'Неизвестная ошибка')}")
                return {'items': []}
            return response['response']
        except requests.RequestException as e:
            self.logger.error(f"Ошибка запроса к VK API: {e}")
            return {'items': []}


    def get_little_data(self, posts: str) -> Dict[str, Any]:
        """Получаем выборочные посты из ВК.

        Args:

        Returns:
            Dict[str, Any]: Данные постов из VK API.

        Raises:
            requests.RequestException: Если запрос к API не удался.
        """
        try:
            url = 'https://api.vk.ru/method/wall.getById'
            params = {
                'access_token': self.vk_token,
                'posts': posts,
                'extended': 1,
                'v': '5.199'
            }
            response = requests.get(url, params=params).json()
            if 'response' not in response:
                self.logger.error(f"Ошибка VK API: {response.get('error', 'Неизвестная ошибка')}")
                return {'items': []}
            return response['response']
        except requests.RequestException as e:
            self.logger.error(f"Ошибка запроса к VK API: {e}")
            return {'items': []}


    def get_owner_name_by_id(self, owner_id: int) -> str:
        """Получаем имя владельца поста по ID.

        Args:
            owner_id (int): ID владельца (положительный для пользователей, отрицательный для групп).

        Returns:
            str: Имя владельца.
        """
        try:
            if owner_id > 0:
                url = 'https://api.vk.ru/method/users.get'
                params = {
                    'access_token': self.vk_token,
                    'user_ids': owner_id,
                    'fields': 'first_name, last_name',
                    'v': '5.199'
                }
                response = requests.get(url, params=params).json()['response'][0]
                return f"{response['first_name']} {response['last_name']}"

            else:
                url = 'https://api.vk.ru/method/groups.getById'
                params = {
                    'access_token': self.vk_token,
                    'group_id': (-1) * owner_id,
                    'v': '5.199'
                }
                response = requests.get(url, params=params).json()['response']['groups'][0]
                return response['name']
        except (requests.RequestException, KeyError) as e:
            self.logger.error(f"Ошибка получения имени владельца {owner_id}: {e}")
            return  "Unknown"


    def get_video(self, video):
        """Получаем видео (пока не работает на стороне ВК)

        Args:
            video (str): Блок видео.

        Returns:
            str: Ссылка на видео.
        """
        try:
            url = 'https://api.vk.ru/method/video.get'
            params = {
                'access_token': self.vk_token,
                'videos': f'{video["owner_id"]}_{video["id"]}_{video["access_key"]}',
                'v': '5.199',
                'scope': ''
            }

            response = requests.get(url, params=params).json()
            return response['response']['items'][0]['player']
        except (requests.RequestException, KeyError) as e:
            self.logger.error(f"Ошибка получения видео  {video}: {e}")
            return  "Unknown"   
