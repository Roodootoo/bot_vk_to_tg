FROM python:3.10-alpine

# Установка переменных окружения
ENV PYTHONUNBUFFERED 1

# Копируем файлы в контейнер
COPY ./requirements.txt /src/requirements.txt
COPY ./app /scr/app
COPY . /src

# Устанавливаем зависимости
RUN pip3 install --no-cache-dir --upgrade -r /src/requirements.txt

# Установка рабочей директории внутри контейнера
WORKDIR src


CMD ["python", "main.py"]
