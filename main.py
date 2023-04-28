import telebot
from telebot import types
import numpy as np
import sqlite3
import pickle
import re
import time
from datetime import datetime
import os


import LibBlet
import config
import DataBase

bot = config.bot


states = {}


def set_state(key: int, value: str):
    global states
    states[key] = value


def get_state(key: int):
    global states
    return states.get(key)


Exams = {}


def get_exam(key: int):
    global Exams
    return Exams.get(key)


def set_exam(key: int, value: LibBlet.Exam):
    global Exams
    Exams[key] = value


Cards = {}


def get_card(key: int):
    global Cards
    return Cards.get(key)


def set_card(key: int, value: LibBlet.Exam.ExaminationCard):
    global Cards
    Cards[key] = value


hideBoard = types.ReplyKeyboardRemove()

re_markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
main_button = types.KeyboardButton('На главную')
return_button = types.KeyboardButton('Назад')
re_markup.add(main_button, return_button)


def remove_inline_keyboard(message):
    # Remove InlineButtons
    bot.edit_message_text(text=message.html_text, chat_id=message.chat.id, message_id=message.message_id, parse_mode='HTML')


# region alert_commands
@bot.message_handler(commands=['alert'])
def what_alert(message):
    if message.from_user.id == 542687360:
        bot.send_message(message.chat.id, 'Что говорим?')
        bot.register_next_step_handler(message, alert)
    else:
        bot.send_message(message.chat.id, 'У тебя нет доступа к команде)')


def alert(message):
    if message.text == 'На главную' or message.text == 'Назад':
        hi(message)

    users = DataBase.get_user_list()
    for user in users:
        try:
            bot.send_message(text=message.html_text, chat_id=user[0], parse_mode='HTML')
        except:
            pass


@bot.message_handler(commands=['alert_to'])
def what_alert_to(message):
    if message.from_user.id == 542687360:
        bot.send_message(message.chat.id, 'Кому: что говорим?')
        bot.register_next_step_handler(message, alert_to)
    else:
        bot.send_message(message.chat.id, 'У тебя нет доступа к команде)')


def alert_to(message):
    if message.text == 'На главную' or message.text == 'Назад':
        hi(message)

    try:
        bot.send_message(text=message.text.split(':')[1:], chat_id=message.text.split(':')[0], parse_mode='HTML')
    except:
        pass
# endregion alert_commands


def bot_was_restarted(message):
    if get_state(message.chat.id) is None:
        users_list = np.array(DataBase.get_user_list())
        try:
            # Эта шляпа для того, чтобы вылетало исключение, если в базе нет пользователя.
            index = np.where(users_list == str(message.chat.id))[0][0]
            bot.send_message(message.chat.id, 'Бот был перезагружен)')
        except:
            bot.send_message(message.chat.id, 'Привет)')
        hi(message)
        return True
    else:
        return False


@bot.message_handler(commands=['start'])
def hi(message):
    set_state(message.chat.id, 'main')
    try:
        DataBase.delete_user(message.from_user.id)
        DataBase.add_user(message.from_user.id, message.from_user.username)
    except sqlite3.IntegrityError:
        pass

    set_global_edite_mode(message.chat.id, False)
    set_first_question_flag(message.chat.id, True)

    bot.send_message(text='Мы на главной', chat_id=message.chat.id, reply_markup=re_markup)

    markup = types.InlineKeyboardMarkup(row_width=1)
    my_exam = types.InlineKeyboardButton('Мои экзамены', callback_data='my_exam')
    add_exam = types.InlineKeyboardButton('Добавить экзамен', callback_data='add_exam')
    settings = types.InlineKeyboardButton('Настройки', callback_data='settings')
    markup.add(my_exam, add_exam, settings)

    bot.send_message(text='Меню', chat_id=message.chat.id, reply_markup=markup)


@bot.message_handler(content_types=['text'])
def answer(message):
    print(f'{message.from_user.username} {message.chat.id}:    text: {message.text}     '
          f'state:{get_state(message.chat.id)}      {datetime.now()}')

    # Проверка на рестарт бота.
    if bot_was_restarted(message):
        return

    if message.text == 'На главную':
        hi(message)

    elif message.text == 'Назад':
        match get_state(message.chat.id):
            case 'Result':
                full_answer(message)
            case 'my_exams':
                hi(message)
            case 'exam':
                my_exams_menu(message)
            case 'add_exam':
                hi(message)
            case 'ended_add':
                hi(message)
            case 'card_menu':
                cards_list(message)
            case 'cards_list':
                card_menu(message)
            case 'edit_card':
                cards_list(message)
            case 'examination':
                exam_menu(message)
            case 'edit_exam_name':
                my_exams_menu(message)
            case _:
                pass


@bot.callback_query_handler(func=lambda call: True)
def buttons(call):
    message = call.message

    state = get_state(message.chat.id)
    card = get_card(message.chat.id)

    global progress
    global score

    print(f'{call.message.from_user.username} {call.message.chat.id}:    button: {call.data}   state: {state}'
          f'    {datetime.now()}')

    if bot_was_restarted(message):
        return

    match call.data:
        case 'my_exam':
            set_state(message.chat.id, 'my_exams')
            remove_inline_keyboard(call.message)
            my_exams_menu(call.message)

        case 'add_exam':
            remove_inline_keyboard(call.message)
            where_add(call.message)

        case 'add_exam_from_file':
            remove_inline_keyboard(message)
            if state != 'add_exam':
                return

            bot.send_message(message.chat.id, 'Пришлите мне файл')
            bot.register_next_step_handler(message, add_exam_from_file)

        case 'create_exam':
            remove_inline_keyboard(message)
            if state != 'add_exam':
                return

            set_exam_name(message)

        case 'yes' | 'no':
            remove_inline_keyboard(message)
            if state != 'Result':
                return

            all_right(call)

        case 'edit_exam_name':
            remove_inline_keyboard(message)
            if state != 'exam':
                return

            edit_exam_name(message)

        case 'cards_list':
            remove_inline_keyboard(message)
            if state != 'exam':
                return

            cards_list(message)

        case 'card_edit':
            remove_inline_keyboard(message)
            if state != 'card_menu':
                return

            set_state(message.chat.id, 'edit_card')

            reply_markup = types.InlineKeyboardMarkup(row_width=1)
            name = types.InlineKeyboardButton('Вопрос', callback_data='edit_card_name')
            s_answer = types.InlineKeyboardButton('Краткий ответ', callback_data='edit_card_short_answer')
            f_answer = types.InlineKeyboardButton('Развернутый ответ', callback_data='edit_card_full_answer')
            reply_markup.add(name, s_answer, f_answer)

            bot.send_message(call.message.chat.id, 'А что изменить?', reply_markup=reply_markup)

        case 'edit_card_name':
            remove_inline_keyboard(message)
            if state != 'edit_card':
                return

            bot.send_message(text='Введите вопрос', chat_id=message.chat.id)
            set_state(message.chat.id, 'edit_question_name')
            bot.register_next_step_handler(message, set_value_in_edite_mode)

        case 'edit_card_short_answer':
            remove_inline_keyboard(message)
            if state != 'edit_card':
                return

            bot.send_message(text='Введите тезисный (краткий) ответ', chat_id=message.chat.id)
            set_state(message.chat.id, 'edit_short_answer')
            bot.register_next_step_handler(message, set_value_in_edite_mode)

        case 'edit_card_full_answer':
            remove_inline_keyboard(message)
            if state != 'edit_card':
                return

            bot.send_message(text='Введите развернутый ответ', chat_id=message.chat.id)
            set_state(message.chat.id, 'edit_full_answer')
            bot.register_next_step_handler(message, set_value_in_edite_mode)

        case 'card_delete':
            remove_inline_keyboard(message)
            if state != 'card_menu':
                return

            get_exam(message.chat.id).delete_examination_card(card)
            set_global_edite_mode(message.chat.id, True)
            save_exam(message)
            cards_list(call.message)

        case 'do_task':
            remove_inline_keyboard(message)
            if state != 'exam':
                return

            start_examination(message)

        case 'ok':
            remove_inline_keyboard(message)
            if state == 'examination':
                bot.send_message(message.chat.id, 'Правильно!')
                bot.send_message(message.chat.id, 'Развернутый ответ билета:\n' +
                                 card.full_answer, parse_mode='HTML')
                progress[message.chat.id] += 1
                score[message.chat.id] += 1
                examination(message)

        case 'not_ok':
            remove_inline_keyboard(message)
            if state == 'examination':
                bot.send_message(message.chat.id, 'Неверно(((')
                bot.send_message(message.chat.id, 'Правильный ответ:\n' +
                                 f'{card.short_answer}\n\n{card.full_answer}', parse_mode='HTML')
                progress[message.chat.id] += 1
                examination(message)

        case 'settings':
            remove_inline_keyboard(message)

            for i in range(10):
                bot.send_message(message.chat.id, 'До взрыва ' + str(10 - i))
                time.sleep(1)
            bot.send_message(message.chat.id, 'оп, нихуя')

        case _:

            if state == 'my_exams':
                remove_inline_keyboard(message)
                set_exam(message.chat.id, LibBlet.Exam.load_exam(call.data))
                exam_menu(message)
            elif state == 'exam':
                data = call.data.split('&&')
                if data[0] == 'delete_':
                    remove_inline_keyboard(call.message)
                    DataBase.delete_exam(data[1])
                    bot.send_message(call.message.chat.id, 'Удалено.')
                    my_exams_menu(call.message)

                elif data[0] == 'share_':
                    with open(f'Exams/{data[1]}.dat', 'rb') as f:
                        bot.send_document(call.message.chat.id, types.InputFile(f))
            else:
                bot.send_message(message.chat.id, 'Не доступно.')
                return


def my_exams_menu(message):
    bot.send_message(message.chat.id, 'Список экзаменов', reply_markup=re_markup)
    set_state(message.chat.id, 'my_exams')
    data = np.array(DataBase.get_exam_list(message.chat.id))
    text = ''

    markup = types.InlineKeyboardMarkup(row_width=8)
    buttons = []
    i = 0
    for elem in data:
        i += 1
        # Здесь происходят ужасы парсинга записей в базе и преобразования их в читаемый вид для пользователя
        param = r'[\'\]\'\[]'
        text += f'{i}. {re.sub(param, "", re.sub(f"{message.chat.id}", "", re.sub(r"[_]", " ", str(elem))))}\n'
        buttons.append(types.InlineKeyboardButton(i, callback_data=re.sub(param, "", str(elem))))

    markup.add(*buttons)
    try:
        bot.send_message(message.chat.id, text, reply_markup=markup)
    except telebot.apihelper.ApiTelegramException:
        bot.send_message(message.chat.id, 'Здесь пока ничего нет')


# region AddCard

global_edite_mode = {}


def set_global_edite_mode(key: int, value: bool):
    global global_edite_mode
    global_edite_mode[key] = value


def get_global_edite_mode(key: int):
    global global_edite_mode
    return global_edite_mode.get(key)


first_question_flag = {}


def set_first_question_flag(key: int, value: bool):
    global first_question_flag
    first_question_flag[key] = value


def get_first_question_flag(key: int):
    global first_question_flag
    return first_question_flag.get(key)


def where_add(message):
    set_state(message.chat.id, 'add_exam')
    reply_markup = types.InlineKeyboardMarkup()
    from_file = types.InlineKeyboardButton('Из файла', callback_data='add_exam_from_file')
    create = types.InlineKeyboardButton('Создать', callback_data='create_exam')
    reply_markup.add(from_file, create)

    bot.send_message(message.chat.id, 'Как добавить?', reply_markup=reply_markup)


def add_exam_from_file(message):
    if message.text == 'Назад':
        where_add(message)
        return

    if message.text == 'На главную':
        hi(message)
        return
    try:
        file_info = bot.get_file(message.document.file_id)
        set_exam(message.chat.id, pickle.loads(bot.download_file(file_info.file_path)))
        save_exam(message)
    except:
        bot.send_message(message.chat.id, 'Как-то это не похоже на файл, который я могу распознать((')
        where_add(message)


def set_value(message):

    card = get_card(message.chat.id)

    if message.text == 'Назад':

        match get_state(message.chat.id):
            case 'set_exam_name':
                where_add(message)

            case 'set_question_name':
                if get_first_question_flag(message.chat.id):
                    set_exam_name(message)
                else:
                    question_name(message)

            case 'set_short_answer':
                question_name(message)

            case 'set_full_answer':
                short_answer(message)

            case _:
                return
        return

    if message.text == 'На главную':
        hi(message)
        return

    match get_state(message.chat.id):
        case 'set_exam_name':
            if message.text is None:
                bot.send_message(message.chat.id, 'Я принимаю только текст')
                set_exam_name(message)
                return

            set_exam(message.chat.id, LibBlet.Exam(message.text))

            question_name(message)

        case 'set_question_name':
            if message.text is None:
                bot.send_message(message.chat.id, 'Я принимаю только текст')
                question_name(message)
                return

            set_card(message.chat.id, LibBlet.Exam.ExaminationCard())

            get_card(message.chat.id).name = message.text

            short_answer(message)

        case 'set_short_answer':
            if message.text is None:
                bot.send_message(message.chat.id, 'Я принимаю только текст')
                short_answer(message)
                return

            set_first_question_flag(message.chat.id, False)

            card.short_answer = message.text

            full_answer(message)

        case 'set_full_answer':
            if message.text is None:
                bot.send_message(message.chat.id, 'Я принимаю только текст')
                full_answer(message)
                return

            card.full_answer = message.html_text

            write_card(message)

            markup = types.InlineKeyboardMarkup(row_width=2)
            yes = types.InlineKeyboardButton(text='Да', callback_data='yes')
            no = types.InlineKeyboardButton(text='Нет', callback_data='no')
            markup.add(yes, no)

            bot.send_message(text='Будут еще билеты?', chat_id=message.chat.id, reply_markup=markup)

        case _:
            return


def set_exam_name(message):
    bot.send_message(text='Введите название экзамена', chat_id=message.chat.id, reply_markup=re_markup)

    set_state(message.chat.id, 'set_exam_name')
    bot.register_next_step_handler(message, set_value)


def question_name(message):
    bot.send_message(text='Введите вопрос', chat_id=message.chat.id)
    set_state(message.chat.id, 'set_question_name')
    bot.register_next_step_handler(message, set_value)


def short_answer(message):
    bot.send_message(text='Введите тезисный (краткий) ответ', chat_id=message.chat.id)
    set_state(message.chat.id, 'set_short_answer')
    bot.register_next_step_handler(message, set_value)


def full_answer(message):
    bot.send_message(text='Введите развернутый ответ', chat_id=message.chat.id)
    set_state(message.chat.id, 'set_full_answer')
    bot.register_next_step_handler(message, set_value)


def save_exam(message):
    exam = get_exam(message.chat.id)
    file_second_name = re.sub(r'\W', r'_', str(exam.name))
    try:
        exam.file_name = f'{message.chat.id}_{file_second_name}'
        pickle.dump(exam, open(f'./Exams/{message.chat.id}_{file_second_name}.dat', 'wb'),
                    protocol=pickle.HIGHEST_PROTOCOL)
        test = pickle.dumps(exam)
        out = pickle.loads(test)
        if not get_global_edite_mode(message.chat.id):
            DataBase.add_exam(message.chat.id, f'{message.chat.id}_{file_second_name}')
        else:
            set_global_edite_mode(message.chat.id, False)
        bot.send_message(text='Экзамен сохранен.', chat_id=message.chat.id)
        return True
    except Exception as inst:
        print(inst)
        bot.send_message(text=f'Бля, что-то пошло не так\n\n{inst}', chat_id=message.chat.id)
        return False


def all_right(call):
    card = get_card(call.message.chat.id)

    if call.data == 'yes':
        question_name(call.message)
        get_exam(call.message.chat.id).add_examination_card(card)
    else:
        get_exam(call.message.chat.id).add_examination_card(card)
        save_exam(call.message)

        set_first_question_flag(call.message.chat.id, True)

        set_state(call.message.chat.id, 'ended_add')


def write_card(message):
    bot.send_message(message.chat.id, 'ПроверОчка')
    set_state(message.chat.id, 'Result')
    card = get_card(message.chat.id)
    card_text = f'<b>{card.name}</b>\n{card.short_answer}\n\n{card.full_answer}'

    bot.send_message(message.chat.id, card_text, parse_mode='HTML')
# endregion AddCard


# region switch exam
def exam_menu(message):
    set_state(message.chat.id, 'exam')

    exam = get_exam(message.chat.id)
    markup = types.InlineKeyboardMarkup(row_width=1)
    test = types.InlineKeyboardButton('Решать экзамен', callback_data='do_task')
    edit = types.InlineKeyboardButton('Изменить название', callback_data='edit_exam_name')
    card_list = types.InlineKeyboardButton('Список билетов', callback_data='cards_list')
    delete = types.InlineKeyboardButton('Удалить', callback_data=f'delete_&&{str(exam.file_name)}')
    share_btn = types.InlineKeyboardButton('Поделиться', callback_data=f'share_&&{str(exam.file_name)}')

    markup.add(test, edit, card_list, delete, share_btn)

    bot.send_message(message.chat.id, 'Экзамен ' + exam.name, reply_markup=markup)


def edit_exam_name(message):
    set_state(message.chat.id, 'edit_exam_name')
    bot.send_message(message.chat.id, 'Введите название экзамена')
    bot.register_next_step_handler(message, set_new_exam_name)


def set_new_exam_name(message):
    if message.text is None:
        bot.send_message(message.chat.id, 'Я принимаю только текст')
        edit_exam_name(message)
        return

    if message.text == 'Назад':
        exam_menu(message)
        return

    if message.text == 'На главную':
        hi(message)
        return

    file_name = f"{message.chat.id}_" + re.sub(r'\W', r'_', str(get_exam(message.chat.id).name))

    get_exam(message.chat.id).name = message.text
    if save_exam(message):
        DataBase.delete_exam(file_name)


# region switch card
def cards_list(message):
    set_state(message.chat.id, 'cards_list')

    if message.text == 'Назад':
        exam_menu(message)
        return

    if message.text == 'На главную':
        hi(message)
        return

    text = ''
    i = 0

    for elem in get_exam(message.chat.id).examination_cards:
        i += 1
        text += f'{i}. {elem.name}\n'

    text += f'{i + 1}. Добавить новый билет\n'

    try:
        bot.send_message(message.chat.id, text)
        bot.send_message(message.chat.id, 'Напишите пункт пункт:')

        bot.register_next_step_handler(message, card_menu)
    except Exception as inst:
        print(inst)
        bot.send_message(text=f'Бля, что-то пошло не так\n\n{inst}', chat_id=message.chat.id)


def card_menu(message):
    set_state(message.chat.id, 'card_menu')

    if message.text == 'Назад':
        cards_list(message)
        return

    if message.text == 'На главную':
        hi(message)
        return

    exam = get_exam(message.chat.id)

    try:
        if int(message.text) == len(exam.examination_cards) + 1:
            set_global_edite_mode(message.chat.id, True)
            question_name(message)

        elif 0 <= int(message.text) - 1 <= len(exam.examination_cards):
            set_card(message.chat.id, exam.examination_cards[int(message.text) - 1])
            card = get_card(message.chat.id)
            card_text = f'<b>{card.name}</b>\n{card.short_answer}\n\n{card.full_answer}'

            reply_markup = types.InlineKeyboardMarkup(row_width=1)
            edit = types.InlineKeyboardButton('Изменить', callback_data='card_edit')
            delete = types.InlineKeyboardButton('Удалить', callback_data='card_delete')

            reply_markup.add(edit, delete)

            bot.send_message(message.chat.id, card_text, parse_mode='HTML', reply_markup=reply_markup)

        else:
            bot.send_message(message.chat.id, 'Такого билета нет')
            bot.register_next_step_handler(message, card_menu)
    except:
        bot.send_message(message.chat.id, 'Бля, ну и что это за хуйня? Напиши нормально')
        bot.register_next_step_handler(message, card_menu)


def set_value_in_edite_mode(message):
    if message.text is None:
        bot.send_message(message.chat.id, 'Я принимаю только текст')
        cards_list(message)
        return

    card = get_card(message.chat.id)

    if message.text == 'Назад':
        cards_list(message)
        return

    if message.text == 'На главную':
        hi(message)
        return

    match get_state(message.chat.id):
        case 'edit_question_name':
            card.name = message.text

        case 'edit_short_answer':
            card.short_answer = message.text

        case 'edit_full_answer':
            card.full_answer = message.html_text

        case _:
            return
    write_card(message)

    set_global_edite_mode(message.chat.id, True)
    save_exam(message)

    cards_list(message)

# endregion switch card
# endregion switch exam


examination_cards = {}
progress = {}
score = {}


# region test
def start_examination(message):
    global examination_cards
    global progress
    global score

    exam = get_exam(message.chat.id)
    progress[message.chat.id] = 0
    score[message.chat.id] = 0

    try:
        if len(exam.examination_cards) < 4:
            bot.send_message(message.chat.id, 'Ты добавил(а) как-то мало билетов в экзамен\n'
                                              f'Минимальное кол-во: 4 (имеется: {len(exam.examination_cards)})')
            exam_menu(message)
            return
    except:
        hi(message)
        return

    examination_cards[message.chat.id] = exam.swap_list()
    examination(message)


def examination(message):
    set_state(message.chat.id, 'examination')
    global examination_cards
    global progress
    global score

    if progress[message.chat.id] < len(examination_cards[message.chat.id]):
        set_card(message.chat.id, examination_cards[message.chat.id][progress[message.chat.id]])
        card = get_card(message.chat.id)

        answer_list = get_exam(message.chat.id).answer_list(card)
        reply_markup = types.InlineKeyboardMarkup(row_width=4)
        btns = []

        text = str(card.name) + '\n'

        for i in range(4):
            text += f'{i+1}. {answer_list[i].short_answer} \n'
            call_data = 'ok' if answer_list[i].short_answer == card.short_answer else 'not_ok'
            btns.append(types.InlineKeyboardButton(i + 1, callback_data=call_data))

        reply_markup.add(*btns)

        bot.send_message(message.chat.id, text, reply_markup=reply_markup)
    else:
        bot.send_message(message.chat.id, f'Билеты кончились. Твой результат: {score[message.chat.id]}/'
                                          f'{len(examination_cards[message.chat.id])}\n'
                                          f'Ты хорошо поработал(а)!')

# endregion test


bot.polling(none_stop=True, interval=0)
