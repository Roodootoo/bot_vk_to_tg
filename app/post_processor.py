import re


class PostProcessor:
    def __init__(self, bot, vk_api, include_link, preview_link, reposts, logger):
        self.bot = bot
        self.vk_api = vk_api
        self.include_link = include_link
        self.preview_link = preview_link
        self.reposts = reposts
        self.logger = logger

    def process_post(self, post, last_id):
        text = post['text']
        copy_history_text = ''
        images = []
        links = []

        # Проверка, есть ли аттачи к посту
        if 'attachments' in post:
            have_video = False
            for attach in post['attachments']:
                if attach['type'] == 'photo':
                    image = attach['photo']
                    images.append(image)
                elif attach['type'] == 'video' and not have_video:
                    video = attach['video']
                    links.insert(0, '# Для просмотра видео, поджалуйста, перейдите по ссылке ')
                    have_video = True
                    if 'player' in video:
                        links.append(video['player'])
                else:
                    for (key, value) in attach.items():
                        if key != 'type' and 'url' in value:
                            links.append(value['url'])

        post_url = f"https://vk.com/{self.vk_api.domain_vk}?w=wall{str(post['owner_id'])}_{str(post['id'])}"

        # Проверка, есть ли репост другой записи
        if 'copy_history' in post:
            copy_history = post['copy_history'][0]
            copy_history_text = copy_history['text']

            # Добавление строки с автором репоста
            owner_id = int(copy_history['owner_id'])
            owner_name = self.vk_api.get_owner_name_by_id(owner_id)
            copy_history_text = '\n \N{speech balloon} ' + owner_name + ':\n' + copy_history_text

            # Проверка, есть ли аттачи у репоста
            if 'attachments' in copy_history:
                have_video = False
                for attach in copy_history['attachments']:
                    if attach['type'] == 'photo':
                        image = attach['photo']
                        images.append(image)
                    elif attach['type'] == 'video' and have_video is False:
                        video = attach['video']
                        if 'player' in video:
                            links.append(video['player'])
                        elif self.include_link:
                            # пока с видео бяда у ВК, player не у всех есть
                            links.append('# Для просмотра видео, пожалуйста, перейдите по ссылке ниже ')
                            have_video = True

                    elif attach['type'] == 'link' and self.include_link:
                        links.append(attach['url'])
                    elif self.include_link:
                        for (key, value) in attach.items():
                            if key != 'type' and 'url' in value:
                                links.append(value['url'])

        # Добавление ссылок, если надо
        if self.include_link:
            links.append('\n ВК: ' + post_url + '\n')

        # Сборка всего текста
        text = '\n'.join([text] + [copy_history_text] + links)
        self.logger.info(post_url)

        return text, images

    @staticmethod
    def clean_text(text):
        # Удаление вк-ссылок типа [id123| ] и [club213| ] для красоты текста
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
    def split_text(text):
        # Разделение текста на части, сколько Telegram может взять за один заход
        message_breakers = [':', '\n']
        max_message_length = 4096

        if len(text) >= max_message_length:
            last_index = max(
                map(lambda separator: text.rfind(separator, 0, max_message_length), message_breakers))
            good_part = text[:last_index]
            bad_part = text[last_index + 1:]
            return [good_part] + PostProcessor.split_text(bad_part)
        else:
            return [text]
