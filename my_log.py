from datetime import datetime


def make_log(log_path):
    def _make_log(old_function):
        def new_function(*args, **kwargs):
            with open(log_path,'a') as log_file:
                log_file.write(f'{datetime.now()}: Начало вызова функции {old_function.__name__} с аргументами {args} и {kwargs} \n')
                result = old_function(*args, **kwargs)
                log_file.write(f'{datetime.now()}: {old_function.__name__} вернула "{result}" \n')
                return result
        return new_function
    return _make_log
