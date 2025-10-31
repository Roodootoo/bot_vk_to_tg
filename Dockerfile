FROM python:3.10-alpine

# Установка переменных окружения
ENV PYTHONUNBUFFERED 1

# Создаем рабочую директорию
WORKDIR /src

# Копируем файлы в контейнер
COPY ./requirements.txt /src/requirements.txt
COPY ./app /srс/app
COPY . /src

# Устанавливаем зависимости
RUN pip3 install --no-cache-dir --upgrade -r /src/requirements.txt


CMD ["python", "main.py"]
