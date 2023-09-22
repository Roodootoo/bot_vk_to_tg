import os
import re
import sys
from time import sleep

import requests
import telebot
import configparser
from telebot.types import InputMediaPhoto

import my_log


# Считываем настройки
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

# Символы, на которых можно разбить сообщение
message_breakers = [':', '\n']
max_message_length = 4091

# Инициализируем телеграмм бота
bot = telebot.TeleBot(BOT_TOKEN)


def test():
    bot.send_message(CHANNEL, '123')


# Получаем данные из vk.com
def get_data(domain_vk, count_vk):

    url = 'https://api.vk.com/method/wall.get'
    params = {
        'access_token': VK_TOKEN,
        'domain': DOMAIN_VK,
        'extended': 1,
        'count': COUNT_VK,
        'v': '5.131'
    }

    response = requests.get(url, params=params).json()['response']
    return response


def get_owner_name_by_id(owner_id):
    if owner_id > 0:
        url = 'https://api.vk.com/method/users.get'
        params = {
            'access_token': VK_TOKEN,
            'user_ids': owner_id,
            'fields': 'first_name, last_name',
            'v': '5.131'
        }
        response = requests.get(url, params=params).json()['response'][0]
        owner_name = response['first_name'] + ' ' + response['last_name']

    else:
        url = 'https://api.vk.com/method/groups.getById'
        params = {
            'access_token': VK_TOKEN,
            'group_id': (-1) * owner_id,
            'v': '5.131'
        }
        owner_name = requests.get(url, params=params).json()['response'][0]['name']

    return owner_name

# Проверяем данные по условиям перед отправкой
def check_posts_vk():
    global bot
    global config
    global config_path

    response = get_data(DOMAIN_VK, COUNT_VK)
    response = reversed(response['items'])

    # Берём последний загруженный id из сеттингов
    last_id = config.get('Settings', 'LAST_ID')

    for post in response:

        # Сравниваем id, пропускаем уже опубликованные

        if int(post['id']) <= int(last_id):
            continue

        text = post['text']

        # Проверяем аттачи к посту
        if 'attachments' in post:
            images = []
            links = []
            attachments = []
            attaches = post['attachments']
            for attach in attaches:
                if attach['type'] == 'photo':
                    image = attach['photo']
                    images.append(image)
                elif attach['type'] == 'video':
                    video = attach['video']
                    if 'player' in video:
                        links.append(video['player'])
                else:
                    for (key, value) in attach.items():
                        if key != 'type' and 'url' in value:
                            attachments.append(value['url'])

        if INCLUDE_LINK:
            post_url = f"https://vk.com/{DOMAIN_VK}?w=wall{str(post['owner_id'])}_{str(post['id'])}"
            links.insert(0, '\n' + post_url + '\n')
        # text = '\n'.join([text] + links)

        # Проверяем есть ли репост другой записи
        if 'copy_history' in post:
            copy_history = post['copy_history'][0]
            copy_history_text = copy_history['text']

            # Добавляем строку с автором репоста
            owner_id = int(copy_history['owner_id'])
            owner_name = get_owner_name_by_id(owner_id)
            copy_history_text = '\n \N{speech balloon} ' + owner_name + ':\n' + copy_history_text

            text_attach = '\n'.join([text] + [copy_history_text] + links)

            send_posts_text(text_attach)

            # Проверяем есть ли аттачи у другой записи
            if 'attachments' in copy_history:
                copy_add = copy_history['attachments']
                copy_add = copy_add[0]

                # Если это ссылка
                if copy_add['type'] == 'link':
                    link = copy_add['link']
                    text = link['title']
                    send_posts_text(text)
                    # img = link['photo']
                    # send_posts_img(img)
                    url = link['url']
                    send_posts_text(url)

                # Если это картинки
                if copy_add['type'] == 'photo':
                    attach = copy_history['attachments']
                    images = []
                    for img in attach:
                        image = img['photo']
                        images.append(image)
                    send_posts_img(images)

        else:
            text = '\n'.join([text] + links)
            send_posts_text(text)
            if len(images) > 0:
                send_posts_img(images)

        # Записываем id в файл
        config.set('Settings', 'LAST_ID', str(post['id']))
        last_id = str(post['id'])
        with open(config_path, "w") as config_file:
            config.write(config_file)

        print(post_url)
        # break
        sleep(60)


def clear_text(text):
    # Удаляем вк-ссылки типа [id123| ] и [club213| ] для красоты текста
    str_id = "\[id"
    str_club = "\[club"
    str_end = "|"
    result = [_.start() for _ in re.finditer(str_id, text)]
    result = result + [_.start() for _ in re.finditer(str_club, text)]
    result.sort()
    correct = 0
    for ind in result:
        ind = ind - correct
        res = text.find(str_end, ind)
        correct = correct + (res - ind+2)
        text = text[:int(ind)] + text[int(res)+1:]
        text = text.replace(']', '', 1)

    return text


# Отправка текста
@my_log.make_log('VK_posts.log')
def send_posts_text(text):
    global CHANNEL
    global PREVIEW_LINK
    global bot

    text = clear_text(text)

    if text == '':
        print('no text')
    else:
        # В телеграмме есть ограничения на длину одного сообщения в 4091 символ, разбиваем длинные сообщения на части
        for msg in split(text):
            bot.send_message(CHANNEL, msg, disable_web_page_preview=not PREVIEW_LINK)


def split(text):
    global message_breakers
    global max_message_length

    if len(text) >= max_message_length:
        last_index = max(
            map(lambda separator: text.rfind(separator, 0, max_message_length), message_breakers))
        good_part = text[:last_index]
        bad_part = text[last_index + 1:]
        return [good_part] + split(bad_part)
    else:
        return [text]


# Отправка фото
def send_posts_img(images):
    global bot

    image_urls = list(map(lambda img: max(img["sizes"], key=lambda size: size["type"])["url"], images))
    bot.send_media_group(CHANNEL, map(lambda url: InputMediaPhoto(url), image_urls))


if __name__ == '__main__':
    # text = '14 апреля [id22397540|Юлия Пашкова] и [id2568922|Ольга Миронова] представляли на [club176833970|Форуме Компаньон] секцию социальных и служебных собак. \nВ начале мероприятия Юлия и Светлана Телицына, соруководители Клуба владельцев собак-проводников г. Москвы и МО "Мудрый пес", рассказали и наглядно показали, как работают их собаки-проводники. А заодно дали возможность гостям мероприятия самим оценить возможности собак, пройдя со служебной шлейкой и закрытыми глазами по залу.\nСледом выступила Ольга с рассказом о собаках-помощниках для людей с сахарным диабетом 1 типа. Ее черный лабрадор Джей показал, как работает собачий нос. Ведь на этом и строится дрессировка собак-помощников - они определяют гипогликемию хозяина по запаху.\nТакже на конференции выступили:\n [id138356894|Ирина Зенкина] от [club15195961|Школы собак-помощников] с рассказом об их проекте Солнечный пес и собаках-терапевтах, \nИрина Альбертовна Пономарева рассказала про канистерапию в рамках общеобразовательной школы,\n сотрудники Федеральной таможенной службы,\nначальник поисково-спасательной службы (кинологической) отряда Цетроспас\nи волонтер поисково-спасательного отряда [club20895918|ЛИЗА АЛЕРТ] \n#ЦентрМИРА #МудрыйПес #СлужебныеСобаки #Собакапроводник #Собакаповодырь #непростособака #собакапомощник #сахарныйдиабет #сахарныйнос #кинолог #кинология'
    # clear_text(text)
    check_posts_vk()
    while True:
         check_posts_vk()
         sleep(1800)
