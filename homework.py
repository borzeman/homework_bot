import os
from dotenv import load_dotenv
import telegram
import requests
import time
import logging
import sys
from logging.handlers import RotatingFileHandler

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logging.basicConfig(
    level=logging.DEBUG,
    filename='program.log',
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler('my_logger.log', maxBytes=50000000,
                              backupCount=5)
logger.addHandler(handler)


def check_tokens():
    """Функция проверяет доступность переменных окружения."""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        logging.debug('токены и id чата на месте')
        return True
    return False


def get_api_answer(timestamp):
    """Функция делает запрос к единственному эндпоинту API-сервиса."""
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
        if response.status_code == 200:
            return response.json()
        else:
            logging.error(f'Ошибка запроса к ya. Код: {response.status_code}')
            telegram.Bot.send_message(token=TELEGRAM_TOKEN,
                                      text='Сбой подключения к API')
    except requests.exceptions.RequestException as error:
        logging.error('Ошибка при попытке подключения к эндпоинту')
        telegram.Bot.send_message(token=TELEGRAM_TOKEN, text='Сбой подкл.')
        print(f"Ошибка во время выполнения запроса: {error}")


def check_response(response):
    """Функция проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        logging.error('неверный тип ответа от API')
        telegram.Bot.send_message(token=TELEGRAM_TOKEN,
                                  text='неверный ответ api')
        raise TypeError('В документации написано по-другому!')

    if 'homeworks' not in response:
        logging.error('в словаре отсутствует ключ')
        telegram.Bot.send_message(token=TELEGRAM_TOKEN,
                                  text='отсутствует ключ')
        raise KeyError('В ответе нет ключа homeworks')

    homeworks = response['homeworks']
    if not isinstance(homeworks, list):
        raise TypeError(f'homeworks - не список, {type(homeworks)}')

    if len(homeworks) == 0:
        return None

    return homeworks[0]


def parse_status(homework):
    """Функция извлекает из информации о домашней работе название и статус."""
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    if 'homework_name' not in homework:
        logging.error('нет ключа homework_name в ответе')
        raise KeyError('нет ключа homework_name в ответе')
    if status not in HOMEWORK_VERDICTS:
        logging.error(f'статус {status} отсутствует')
        raise ValueError('статус отстутствует')
    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def send_message(bot, message):
    """Функция отправляет сообщение в Telegram чат."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, text=message)
        logging.debug(f'Сообщение "{message}" отправлено')
    except telegram.error.TelegramError as error:
        logging.error(f'"{error}" - ошибка при отправке')


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical("Одна или неск. из переменных окружения отсутствует!")
        sys.exit()

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = 0

    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)
            if homework:
                message = parse_status(homework)
            else:
                message = 'Работа не взята на проверку'
            send_message(bot, message)
            print('пока нормально работает))')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
