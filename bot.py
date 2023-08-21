import os
from telebot import types
from telebot import TeleBot
from client import *
from validator import Validator
from database_client import DatabaseUser
from typing import Callable


class MyBot(TeleBot):
    COMMANDS = ('/start',)
    __slots__ = ('db_user',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.db_user = DatabaseUser('patient.db')
        self.db_user.create_conn()
        self.buttons = {}

    def create_buttons(self):
        keyboard = types.InlineKeyboardMarkup()
        button1 = types.InlineKeyboardButton('Нового образца', callback_data='new_polis')
        button2 = types.InlineKeyboardButton('Старого образца', callback_data='old_polis')
        keyboard.add(button1, button2)
        self.buttons['policy_types'] = keyboard

    def execute_command(self, command):
        pass


TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = os.environ.get('ADMIN_ID')
patients = {}
bot = MyBot(TOKEN)
bot.create_buttons()


def execute_command_if_exist(func):
    def wrapper(message):
        if message.text not in bot.COMMANDS:
            func(message)
        else:
            command = globals()[message.text.replace('/', '')]
            command(message)
    return wrapper


@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    search_result = bot.db_user.find_patient(user_id)
    if not search_result:
        patients[user_id] = Patient(user_id)
        bot.send_message(user_id, text='Введите ваше ФИО через пробел:')
        bot.register_next_step_handler(message, get_full_name)
    else:
        bot.send_message(user_id, text=f'Здравствуйте {search_result[1]}, вы уже зарегистрированы!')


@execute_command_if_exist
def get_full_name(message: types.Message):
    full_name = Validator.validate_fio(message.text.strip())
    if full_name:
        patient = find_patient(message.from_user.id)
        patient.last_name, patient.name, patient.middle_name = full_name.string.split()
        bot.send_message(message.chat.id, 'Введите вашу дату рождения:')
        bot.register_next_step_handler(message, get_birthdate)
    else:
        bot.send_message(message.chat.id, text='Введены неккоректные данные!Попробуйте еще раз записать ФИО!')
        bot.register_next_step_handler(message, get_full_name)


@execute_command_if_exist
def get_birthdate(message: types.Message):
    res = Validator.validate_birthdate(message.text)
    if res:
        patient = find_patient(message.from_user.id)
        patient.birthdate = message.text.strip()
        bot.send_message(message.chat.id, 'Какого образца ваш'
                                          ' медицинский полис?', reply_markup=bot.buttons['policy_types'])
    else:
        bot.send_message(message.chat.id, text='Введена неккоректная дата рождения!Попробуйте еще раз!')
        bot.register_next_step_handler(message, get_birthdate)


@execute_command_if_exist
def get_series(message: types.Message):
    series = Validator.validate_numb(message.text, len_numb=6)
    if series:
        patient = find_patient(message.from_user.id)
        patient.polis_series = series
        bot.send_message(message.chat.id, 'Введите 10-значный номер полиса:')
        bot.register_next_step_handler(message, get_old_polis)
    else:
        bot.send_message(message.chat.id, 'Введена неккоректная серия полиса!Попробуйте ещё раз.')
        bot.register_next_step_handler(message, get_series)


@execute_command_if_exist
def get_old_polis(message: types.Message):
    polis = Validator.validate_numb(message.text, len_numb=10)
    if polis:
        patient = find_patient(message.from_user.id)
        patient.polis = polis
        bot.db_user.create_patient(patient)
        del patients[message.from_user.id]
        bot.send_message(message.chat.id, 'Вы успешно зарегистрированы!')
    else:
        bot.send_message(message.chat.id, text='Введён неккоректный номер! Давайте попробуем еще раз.'
                                               'Введите номер полиса(10 цифр):')
        bot.register_next_step_handler(message, get_series)


def find_patient(patient_id) -> Patient:
    for id_ in patients:
        if id_ == patient_id:
            return patients[patient_id]


@bot.callback_query_handler(func=lambda call: call.data in ('new_polis', 'old_polis'))
def select_polis(call):
    if call.data == 'new_polis':
        bot.send_message(call.message.chat.id, 'Ввведите 16-значный номер полиса:')
        bot.register_next_step_handler(call.message, get_new_polis)
    else:
        bot.send_message(call.message.chat.id, 'Ввведите серию полиса из 6 цифр:')
        bot.register_next_step_handler(call.message, get_series)

    # удаляем inline-клавиатуру после нажатия на кнопку
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)


@execute_command_if_exist
def get_new_polis(message: types.Message):
    polis = Validator.validate_numb(message.text, len_numb=16)
    if polis:
        patient = find_patient(message.from_user.id)
        patient.polis = polis
        bot.db_user.create_patient(patient)
        del patients[message.from_user.id]
        bot.send_message(message.chat.id, 'Вы успешно зарегистрированы!')
    else:
        bot.send_message(message.chat.id, text='Введен неккоректный номер, попробуйте ещё раз!')
        bot.register_next_step_handler(message, get_new_polis)


while True:
    try:
        bot.polling()
    except Exception as err:
        raise err


