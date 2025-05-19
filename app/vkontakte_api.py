import requests


class VkAPI:
    def __init__(self, vk_token, domain_vk, logger):
        self.vk_token = vk_token
        self.domain_vk = domain_vk
        self.logger = logger

    def get_data(self, count_vk):
        # Получение данных из ВКонтакте
        url = 'https://api.vk.com/method/wall.get'
        params = {
            'access_token': self.vk_token,
            'domain': self.domain_vk,
            'extended': 1,
            'count': count_vk,
            'v': '5.199'
        }

        response = requests.get(url, params=params).json()['response']

        return response

    def get_owner_name_by_id(self, owner_id):
        # Получение имени пользователя ВК, сделавшего перепост
        if owner_id > 0:
            url = 'https://api.vk.com/method/users.get'
            params = {
                'access_token': self.vk_token,
                'user_ids': owner_id,
                'fields': 'first_name, last_name',
                'v': '5.199'
            }
            response = requests.get(url, params=params).json()['response'][0]
            owner_name = response['first_name'] + ' ' + response['last_name']

        else:
            url = 'https://api.vk.com/method/groups.getById'
            params = {
                'access_token': self.vk_token,
                'group_id': (-1) * owner_id,
                'v': '5.199'
            }
            owner_name = requests.get(url, params=params).json()['response']['groups'][0]['name']

        return owner_name

    def get_video(self, video):
        # Получение видео (пока не работает)
        url = 'https://api.vk.com/method/video.get'
        params = {
            'access_token': self.vk_token,
            'videos': f'{video["owner_id"]}_{video["id"]}_{video["access_key"]}',
            'v': '5.199',
            'scope': ''
        }

        response = requests.get(url, params=params).json()
        print(response)
        response = response['response']['items'][0]['player']

        return response
