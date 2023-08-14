import os
import telebot.types
from telebot import TeleBot
from client import *
import re

TOKEN = os.environ.get('BOT_TOKEN')
ADMIN_ID = os.environ.get('ADMIN_ID')
patients = []


class Validator:
    regex_fio = re.compile(3*r'[а-яА-яЁё]+\s+')

    @classmethod
    def validate_fio(cls, fio: str):
        return cls.regex_fio.fullmatch(fio.strip())

    @staticmethod
    def validate_birthdate(st: str):
        try:
            year, month, day = [int(value.strip()) for value in st.split('.')]
            return 1900 < year <= 2023 and 1 <= month <= 12 and 1 <= day <= 31
        except:
            return False

    @staticmethod
    def validate_polis_numb(polis: str):
        polis = polis.strip()
        return len(polis) == 16 and polis.isdigit()


bot = TeleBot(TOKEN)


@bot.message_handler(commands=['start'])
def start(message):
    patients.append(Patient(message.from_user.id))
    user_id = message.from_user.id
    username = message.from_user.username
    chat_id = message.chat.id
    bot.send_message(chat_id, text='Введите вашу ФИО с разделителем ";" : Фамилия;Имя;Отчество')
    bot.register_next_step_handler(message, get_full_name)


def get_full_name(message: telebot.types.Message):
    message_text = message.text
    if Validator.validate_fio(message_text):
        fio = message_text.split()
    else:
        bot.send_message(message.chat.id, text='Введены неккоректные данные! ')
    patient = find_patient(message.from_user.id)
    patient.last_name = fio[0]
    patient.name = fio[1]
    patient.middle_name = fio[2]
    bot.send_message(message.chat.id, 'Введите вашу дату рождения:')
    bot.register_next_step_handler(message, get_birthdate)


def get_birthdate(message: telebot.types.Message):
    message_text = message.text
    patient = find_patient(message.from_user.id)
    patient.birthdate = message_text
    bot.send_message(message.chat.id, 'Введите ваш полис:')
    bot.register_next_step_handler(message, get_polis)


def find_patient(patient_id) -> Patient:
    for patient in patients:
        if patient_id == patient.patient_id:
            return patient


def get_polis(message: telebot.types.Message):
    message_text = message.text
    patient = find_patient(message.from_user.id)
    patient.polis = message_text
    text = patient.get_available_polycs()[0]
    bot.send_message(message.chat.id, str(text))

#
# while True:
#     try:
#         bot.polling()
#     except Exception as err:
#         print(err)

