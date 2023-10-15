import os
from telebot import types
from telebot import TeleBot
from client import *
from validator import Validator
from database_client import DatabaseUser, PATIENT_FIELDS
from telebot_calendar import Calendar, CallbackData, RUSSIAN_LANGUAGE
import datetime

calendar = Calendar(language=RUSSIAN_LANGUAGE)
calendar_1 = CallbackData('calendar_1', 'action', 'year', 'month', 'day')
now = datetime.datetime.now()
users_sessions = {}


class MyBot(TeleBot):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.api_client = ApiClient()
        self.db_user = DatabaseUser('patient.db')
        self.db_user.create_conn()
        self.buttons = {}
        self.commands = tuple((com.command for com in self.get_my_commands()))

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
    def wrapper(message, *args):
        if message.text.strip('/') not in bot.commands:
            func(message, *args)
        else:
            command = globals()[message.text.replace('/', '')]
            command(message)

    return wrapper


def get_patient_from_db(func):
    def wrapper(message: types.Message):
        user_id = message.from_user.id
        search_result = bot.db_user.find_patient(user_id)
        if search_result and message.text != '/start':
            func(message, search_result)
        elif not search_result and message.text == '/start':
            func(message, search_result)
        elif search_result and message.text == '/start':
            bot.send_message(user_id, text=f'Здравствуйте, {search_result[1]}, вы уже зарегистрированы!')
        else:
            bot.send_message(message.chat.id, 'Для выполнения команды нужно пройти регистрацию!'
                                              'Воспользуйтесь командой /start для регистрации.')

    return wrapper


@bot.message_handler(commands=['start'])
@get_patient_from_db
def start(message, *args):
    user_id = message.from_user.id
    patients[user_id] = Patient(user_id)
    bot.send_message(user_id, text='Введите ваше ФИО через пробел:')
    bot.register_next_step_handler(message, get_full_name)


@bot.message_handler(commands=['show_my_profile'])
@get_patient_from_db
def show_my_profile(message, search_result):
    profile = f"""
                Ваш профиль:
                Имя: {search_result[1]}
                Фамилия: {search_result[2]}
                Отчество: {search_result[3]}
                Дата рождения: {search_result[5]}
                Номер полиса : {search_result[4]}
                {'Серия полиса: ' + str(search_result[6]) if search_result[6] else ''}
                Для редактирования профиля используйте команду /edit_my_profile
                """.replace(4 * ' ', '')
    bot.send_message(message.chat.id, profile)


@bot.message_handler(commands=['edit_my_profile'])
@get_patient_from_db
def edit_my_profile(message, *args):
    bot.send_message(message.chat.id, 'Введите название поля, которое хотите изменить:')
    bot.register_next_step_handler(message, get_editable_field)


@execute_command_if_exist
def get_editable_field(message: types.Message):
    field = message.text.strip().lower()
    if field in PATIENT_FIELDS:
        bot.send_message(message.chat.id, 'Введите новое значение:')
        bot.register_next_step_handler(message, get_new_value, field)
    else:
        bot.send_message(message.chat.id, 'Такого поля не существует. Попробуйте ещё раз:')
        bot.register_next_step_handler(message, get_editable_field)


@execute_command_if_exist
def get_new_value(message: types.Message, field):
    if field in ('имя', 'фамилия', 'отчество'):
        new_value = Validator.validate_word(message.text)
    elif field == 'дата рождения':
        new_value = Validator.validate_birthdate(message.text)
    elif field == 'номер полиса':
        old_value = bot.db_user.find_patient(message.from_user.id)[4]
        new_value = Validator.validate_numb(message.text, len_numb=len(str(old_value)))
    else:
        new_value = Validator.validate_numb(message.text, len_numb=6)
    if new_value:
        bot.db_user.update_patient(message.from_user.id, PATIENT_FIELDS[field], new_value)
        bot.send_message(message.chat.id, 'Изменения успешно внесены!')
    else:
        bot.send_message(message.chat.id, 'Введено неверное значение!Попробуйте ещё раз.')
        bot.register_next_step_handler(message, get_new_value, field)


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
        patient.birthdate = res
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


@bot.callback_query_handler(func=lambda call: call.data.startswith('spec'))
def get_doctors(call):
    clinic_id, spec_id = call.data.split(';')[1:]
    doctors = bot.api_client.get_doctors(clinic_id, spec_id)
    keaboard = types.InlineKeyboardMarkup()
    for doctor in doctors:
        name, count_free_tickets, = doctor['name'], doctor["freeTicketCount"]
        callback_data = ';'.join(['doc', clinic_id, doctor["id"]])
        button = types.InlineKeyboardButton(f"{name} Талонов: {count_free_tickets} ", callback_data=callback_data)
        keaboard.add(button)
    bot.send_message(call.message.chat.id, 'Выберите врача:', reply_markup=keaboard)


@bot.callback_query_handler(func=lambda call: call.data.startswith('doc'))
def get_appointments(call):
    clinic_id, doctor_id = call.data.split(';')[1:]
    appointments = bot.api_client.get_appointments(clinic_id, doctor_id)
    users_sessions[call.message.chat.id] = {

        'clinic_id': clinic_id,
        'appointments': appointments
    }
    bot.send_message(call.message.chat.id, 'Выберите дату', reply_markup=calendar.create_calendar(
        name=calendar_1.prefix,
        year=now.year,
        month=now.month)
                     )


def show_appointments(chat_id, date):
    appointments = users_sessions[chat_id]['appointments']
    if 'result' in appointments:
        keyboard = types.InlineKeyboardMarkup(row_width=6)
        buttons = []
        appointments = list(filter(lambda a: a["visitStart"].startswith(date), appointments['result']))
        if not appointments:
            bot.send_message(chat_id, 'Нет свободных талонов на выбранный день \U0001F61E')
            return
        for appointment in appointments:
            time = appointment['visitStart'].split('T')[1][:5]
            appointment_id = f"ticket|{appointment['id']}|{time}"
            buttons.append(
                types.InlineKeyboardButton(time, callback_data=appointment_id)
            )
        keyboard.add(*buttons)
        bot.send_message(chat_id, f'Cвободные талоны на {date} :', reply_markup=keyboard)
    else:
        bot.send_message(chat_id, appointments['message'])


@bot.callback_query_handler(func=lambda call: call.data.startswith('ticket'))
def make_appointment_or_not(call):
    keyboard = types.InlineKeyboardMarkup()
    ticket_id, appointment_time = call.data.split('|')[1:]
    yes_button = types.InlineKeyboardButton('Да', callback_data=f'yes_ap_{ticket_id}')
    no_button = types.InlineKeyboardButton('Нет', callback_data=f'no_ap_{ticket_id}')
    keyboard.add(yes_button, no_button)
    bot.send_message(call.message.chat.id, f'Хотите записаться на {appointment_time} ?', reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data.startswith(('yes_ap', 'no_ap')))
def callback_make_appointment_or_not(call):
    bot.delete_message(call.message.chat.id, call.message.id)
    if call.data.startswith('yes_ap'):
        clinic_id = users_sessions[call.message.chat.id]['clinic_id']
        patient_inf = bot.db_user.find_patient(call.message.chat.id)
        patient_id = bot.api_client.search_patient(clinic_id, patient_inf)
        if patient_id:
            appointment_id = call.data[7:]
            res = bot.api_client.make_appointment(patient_id, patient_inf, clinic_id, appointment_id)
            if res:
                del users_sessions[call.message.chat.id]
                bot.send_message(call.message.chat.id, 'Вы успешно записаны \u2705\nДля просмотра записей '
                                                       'воспользуйтесь командой /see_appointments'
                                 )
            else:
                bot.send_message(call.message.chat.id, 'Упс!Что-то пошло не так. Попробуйте записаться ещё раз!')
        else:
            bot.send_message(call.message.chat.id, 'Упс!Что-то пошло не так.Проверьте корректность данных профиля.')


# функция получает список специальностей по id клиники и выводит их в чат под видом кнопок
def show_specialities(message: types.Message, clinic: dict, search_result):
    specialities = bot.api_client.get_specialities(clinic['id'])
    keaboard = types.InlineKeyboardMarkup()
    for spec in specialities:
        name, count_free_tickets, = spec['name'], spec['countFreeTicket']
        callback_data = ';'.join(['spec', str(clinic["id"]), spec['id']])
        button = types.InlineKeyboardButton(f"{name} Талонов: {count_free_tickets} ", callback_data=callback_data)
        keaboard.add(button)
    bot.send_message(message.chat.id, 'Выберите специальность:', reply_markup=keaboard)



@execute_command_if_exist
def check_numb_clinic(message: types.Message, available_clinics, numb_clinics, next_step_func, search_result):
    numb = message.text.strip()
    if numb.isdigit() and int(numb) in range(1, numb_clinics + 1):
        selected_clinic = available_clinics[int(numb) - 1]
        next_step_func(message, selected_clinic, search_result)
    else:
        bot.send_message(message.chat.id, 'Введён неверный номер, попробуйте ещё раз:')
        bot.register_next_step_handler(message, check_numb_clinic, available_clinics, numb_clinics,
                                       next_step_func, search_result)


@bot.callback_query_handler(func=lambda call: call.data.startswith(('cancelApp', 'dont_cancelApp')))
def cancel_callback(call):
    command, numb = call.data.split('|')
    if command == 'cancelApp':
        appointment = users_sessions[call.message.chat.id]['appointments'][int(numb)-1]
        res = bot.api_client.cancel_appointment(appointment)
        if res:
            bot.send_message(call.message.chat.id, 'Запись к врачу удалена!')
        else:
            bot.send_message(call.message.chat.id, 'Не получилось удалить запись.Попробуйте еще раз')
    bot.delete_message(call.message.chat.id, call.message.message_id)


def download_ticket(user_id, numb):
    patient_inf = bot.db_user.find_patient(user_id)
    appointment = users_sessions[user_id]['appointments'][numb-1]
    res = bot.api_client.download_ticket(appointment, patient_inf)
    file_name = appointment["appointmentId"].replace(';', '_')
    with open(fr'documents/{user_id}.pdf', 'wb') as f:
        f.write(res)
    with open(fr'documents/{user_id}.pdf', 'rb') as f:
        bot.send_document(user_id, f)


@bot.callback_query_handler(func=lambda call: call.data.startswith(('cancel_', 'next_', 'previous_', 'download_')))
def appointment_callback(call):
    command, numb = call.data.split('_')
    appointments = users_sessions[call.message.chat.id]['appointments']
    max_amount = len(appointments)
    if command == 'cancel':
        keyboard_cancel = types.InlineKeyboardMarkup()
        yes_button = types.InlineKeyboardButton('Да', callback_data=f'cancelApp|{numb}')
        no_button = types.InlineKeyboardButton('Нет', callback_data=f'dont_cancelApp|{numb}')
        keyboard_cancel.add(yes_button, no_button)
        bot.send_message(call.message.chat.id, 'Хотите отменить запись??', reply_markup=keyboard_cancel )
    elif command == 'next' and int(numb) + 1 <= max_amount:
        text, keyboard = create_message_appointment(appointments, int(numb) + 1)
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                              reply_markup=keyboard, parse_mode='html')
    elif command == 'previous' and int(numb) - 1 >= 1:
        text, keyboard = create_message_appointment(appointments, int(numb) - 1)
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id,
                              reply_markup=keyboard, parse_mode='html')
    elif command == 'download':
        download_ticket(call.message.chat.id, int(numb))


def create_message_appointment(appointments, numb=1):
    appointment = appointments[numb-1]
    keyboard = types.InlineKeyboardMarkup()
    next_button = types.InlineKeyboardButton('\u27A1', callback_data=f'next_{numb}')
    previous_button = types.InlineKeyboardButton('\u2B05', callback_data=f'previous_{numb}')
    cancel_button = types.InlineKeyboardButton('Отменить запись \u274C', callback_data=f'cancel_{numb}')
    download_ticket = types.InlineKeyboardButton('Скачать талон \U0001F4BE ', callback_data=f'download_{numb}')
    keyboard.add(cancel_button)
    keyboard.add(download_ticket)
    keyboard.add(previous_button, next_button)
    visit_start = appointment['visitStart'].split('T')
    date_visit = visit_start[0]
    time_visit = visit_start[1][:5]
    text = f"""
<i>Дата: {date_visit}</i>\n
<i>Время: {time_visit}</i>\n
<i>Специализация: </i><b>{appointment['specialityRendingConsultation']['name']}</b>\n
<i>Врач: {appointment['doctorRendingConsultation']['name']}</i>\n
<i>{appointment['lpuFullName']}</i>\n
<i>{appointment['lpuAddress']}</i>\n
<i>Телефон: </i><code>{'+7' + appointment['lpuPhone']}</code>\n
                        Запись <b>{numb}</b> из <b>{len(appointments)}</b>
"""
    return text, keyboard


def show_made_appointments(message, appointments):
    if appointments:
        users_sessions[message.chat.id] = {'appointments': appointments}
        text, keyboard = create_message_appointment(appointments)
        bot.send_message(message.chat.id, text, reply_markup=keyboard, parse_mode='html')
    else:
        bot.send_message(message.chat.id, 'У вас нет записей в выбранном мед.учреждении.')


def get_made_appointments(message, selected_clinic, search_result):
    patient_id = bot.api_client.search_patient(selected_clinic['id'], search_result)
    if patient_id:
        made_appointments = bot.api_client.get_made_appointments(patient_id, selected_clinic['id'])
        show_made_appointments(message, made_appointments)
    else:
        bot.send_message(message.chat.id, 'Упс!Что-то пошло не так.Проверьте корректность данных профиля.')


@bot.message_handler(commands=['see_appointments'])
@get_patient_from_db
def see_appointments(message, search_result):
    select_clinic(message, search_result, get_made_appointments)


@bot.message_handler(commands=['make_appointment'])
@get_patient_from_db
def make_appointment(message, search_result):
    select_clinic(message, search_result, show_specialities)


def select_clinic(message: types.Message, search_result, next_step_func):
    patient = Patient(*search_result)
    available_clinics = bot.api_client.get_lst_polycs(patient)['result']
    numb_clinics = len(available_clinics)
    text = 'Доступные мед.учреждения:\n\n'
    for numb, clinic in enumerate(available_clinics):
        address = ','.join(clinic["address"].split(',')[2:])
        text += f'<b>{numb + 1}. {clinic["lpuFullName"]}</b>\n<i>{address}</i>\n\n'
    text += f'Введите порядковый номер мед.учреждения (от 1 до {numb_clinics}):'
    bot.send_message(message.chat.id, text, parse_mode='html')
    bot.register_next_step_handler(message, check_numb_clinic, available_clinics, numb_clinics,
                                   next_step_func, search_result)


@bot.message_handler(commands=['del_my_profile'])
@get_patient_from_db
def del_my_profile(message, *args):
    keyboard = types.InlineKeyboardMarkup()
    yes_button = types.InlineKeyboardButton('Да', callback_data='del_profile')
    no_button = types.InlineKeyboardButton('Нет', callback_data='dont_del_profile')
    keyboard.add(yes_button, no_button)
    bot.send_message(message.chat.id, text='Хотите удалить ваш профиль?', reply_markup=keyboard)


@bot.callback_query_handler(func=lambda call: call.data.startswith('calendar_1'))
def callback_func(call):
    name, action, year, month, day = call.data.split(calendar_1.sep)
    if action == 'DAY':
        appointment_date = f'{year}-{month:>02}-{day:>02}'
        show_appointments(call.message.chat.id, appointment_date)
    else:
        calendar.calendar_query_handler(bot=bot, call=call, name=name, action=action, year=year, month=month, day=day)


@bot.callback_query_handler(func=lambda call: call.data in ('del_profile', 'dont_del_profile'))
def del_callback(call):
    # удаляем inline-клавиатуру после нажатия на кнопку
    bot.edit_message_reply_markup(call.message.chat.id, call.message.message_id)
    if call.data == 'del_profile':
        bot.db_user.del_patient(call.from_user.id)
        bot.send_message(call.message.chat.id, 'Ваш профиль успешно удалён.')
    else:
        bot.send_message(call.message.chat.id, 'Ок, не будем удалять.')


while True:
    try:
        bot.polling()
    except Exception as err:
        raise err
