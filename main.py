import telebot
from telebot import types
import numpy as np
import sqlite3
import pickle
import re


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
    try:
        return Exams[key]
    except:
        return None


def set_exam(key: int, value: LibBlet.Exam):
    global Exams
    Exams[key] = value


Card: LibBlet.Exam.ExaminationCard

global_edite_mode = False

hideBoard = types.ReplyKeyboardRemove()

re_markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
main_button = types.KeyboardButton('На главную')
return_button = types.KeyboardButton('Назад')
re_markup.add(main_button, return_button)


def remove_inline_keyboard(message):
    # Remove InlineButtons
    bot.edit_message_text(text=message.html_text, chat_id=message.chat.id, message_id=message.message_id, parse_mode='HTML')


# region alert_command
@bot.message_handler(commands=['alert'])
def what_alert(message):
    if message.from_user.id == 542687360:
        bot.send_message(message.chat.id, 'Что говорим?')
        bot.register_next_step_handler(message, alert)
    else:
        bot.send_message(message.chat.id, 'У тебя нет доступа к команде)')


def alert(message):
    users = DataBase.get_user_list()
    for user in users:
        bot.send_message(text=message.html_text, chat_id=user[0], parse_mode='HTML')
# endregion alert_command


@bot.message_handler(commands=['start'])
def hi(message):
    set_state(message.chat.id, 'main')
    try:
        DataBase.add_user(message.from_user.id, message.from_user.username)
    except sqlite3.IntegrityError:
        pass
    # Remove all KeyboardButtons
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
          f'state:{get_state(message.chat.id)}')

    # try:
    #     if get_state() != 'main' or message.text == 'На главную':
    #         bot.delete_message(message.chat.id, message.message_id - 1)
    # except:
    #     pass

    if get_state(message.chat.id) is None:
        users_list = np.array(DataBase.get_user_list())
        try:
            index = np.where(users_list == str(message.chat.id))[0][0]
            bot.send_message(message.chat.id, 'Бот был перезагружен)')
        except:
            bot.send_message(message.chat.id, 'Привет)')
        hi(message)
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

    state = get_state(call.message.chat.id)
    global Card
    global progress
    global score

    message = call.message

    print(f'{call.message.from_user.username} {call.message.chat.id}:    button: {call.data}   state: {state}')

    if state is None:
        remove_inline_keyboard(message)
        users_list = np.array(DataBase.get_user_list())
        try:
            index = np.where(users_list == str(message.chat.id))[0][0]
            bot.send_message(message.chat.id, 'Бот был перезагружен)')
        except:
            bot.send_message(message.chat.id, 'Привет)')
        hi(message)
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
            if state != 'add_exam':
                remove_inline_keyboard(message)
                return
            remove_inline_keyboard(message)
            bot.send_message(message.chat.id, 'Пришлите мне файл')
            bot.register_next_step_handler(message, add_exam_from_file)

        case 'create_exam':
            if state != 'add_exam':
                remove_inline_keyboard(message)
                return

            set_exam_name(message)

        case 'yes' | 'no':
            if state != 'Result':
                remove_inline_keyboard(message)
                return

            remove_inline_keyboard(call.message)
            all_right(call)

        case 'edit_exam_name':
            if state != 'exam':
                remove_inline_keyboard(message)
                return

            remove_inline_keyboard(call.message)
            edit_exam_name(call.message)

        case 'cards_list':
            if state != 'exam':
                remove_inline_keyboard(message)
                return

            remove_inline_keyboard(call.message)
            cards_list(call.message)

        case 'card_edit':
            if state != 'card_menu':
                remove_inline_keyboard(message)
                return

            set_state(message.chat.id, 'edit_card')
            remove_inline_keyboard(message)

            reply_markup = types.InlineKeyboardMarkup(row_width=1)
            name = types.InlineKeyboardButton('Вопрос', callback_data='edit_card_name')
            s_answer = types.InlineKeyboardButton('Краткий ответ', callback_data='edit_card_short_answer')
            f_answer = types.InlineKeyboardButton('Развернутый ответ', callback_data='edit_card_full_answer')
            reply_markup.add(name, s_answer, f_answer)

            bot.send_message(call.message.chat.id, 'А что изменить?', reply_markup=reply_markup)

        case 'edit_card_name':
            if state != 'edit_card':
                remove_inline_keyboard(message)
                return

            remove_inline_keyboard(message)

            bot.send_message(text='Введите вопрос', chat_id=message.chat.id)
            set_state(message.chat.id, 'edit_question_name')
            bot.register_next_step_handler(message, set_value_in_edite_mode)

        case 'edit_card_short_answer':
            if state != 'edit_card':
                remove_inline_keyboard(message)
                return

            remove_inline_keyboard(message)

            bot.send_message(text='Введите тезисный (краткий) ответ', chat_id=message.chat.id)
            set_state(message.chat.id, 'edit_short_answer')
            bot.register_next_step_handler(message, set_value_in_edite_mode)

        case 'edit_card_full_answer':
            if state != 'edit_card':
                remove_inline_keyboard(message)
                return

            remove_inline_keyboard(message)

            bot.send_message(text='Введите развернутый ответ', chat_id=message.chat.id)
            set_state(message.chat.id, 'edit_full_answer')
            bot.register_next_step_handler(message, set_value_in_edite_mode)

        case 'card_delete':
            if state != 'card_menu':
                remove_inline_keyboard(message)
                return

            remove_inline_keyboard(call.message)
            get_exam(message.chat.id).delete_examination_card(Card)
            bot.send_message(call.message.chat.id, 'Удалено.')
            cards_list(call.message)

        case 'do_task':
            if state != 'exam':
                return

            remove_inline_keyboard(message)
            start_examination(message)

        case 'ok':
            remove_inline_keyboard(message)
            if state == 'examination':
                bot.send_message(message.chat.id, 'Правильно!')
                bot.send_message(message.chat.id, 'Развернутый ответ билета:\n' +
                                 Card.full_answer, parse_mode='HTML')
                progress += 1
                score += 1
                examination(message)

        case 'not_ok':
            remove_inline_keyboard(message)
            if state == 'examination':
                bot.send_message(message.chat.id, 'Неверно(((')
                bot.send_message(message.chat.id, 'Правильный ответ:\n' +
                                 f'{Card.short_answer}\n\n{Card.full_answer}', parse_mode='HTML')
                progress += 1
                examination(message)

        case _:

            if state == 'my_exams':
                remove_inline_keyboard(call.message)
                set_exam(message.chat.id, LibBlet.Exam.load_exam(call.data))
                exam_menu(call.message)
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
                # bot.send_message(message.chat.id, 'Пока не доступно. (либо бот был перезагружен)')
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
        param = r'[\'\]\'\[]'
        text += f'{i}. {re.sub(param, "", re.sub(f"{message.chat.id}", "", re.sub(r"[_]", " ", str(elem))))}\n'
        buttons.append(types.InlineKeyboardButton(i, callback_data=re.sub(param, "", str(elem))))

    markup.add(*buttons)
    try:
        bot.send_message(message.chat.id, text, reply_markup=markup)
    except telebot.apihelper.ApiTelegramException:
        bot.send_message(message.chat.id, 'Здесь пока ничего нет')


# region AddCard
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

    file_info = bot.get_file(message.document.file_id)
    try:
        set_exam(message.chat.id, pickle.loads(bot.download_file(file_info.file_path)))
        save_exam(message)
    except:
        bot.send_message(message.chat.id, 'Как-то это не похоже на файл, который я могу распознать((')
        where_add(message)


def set_global_edite_mode(param: bool):
    global global_edite_mode
    global_edite_mode = param


first_question_flag = True


def set_value(message):
    global Card
    global first_question_flag

    if message.text == 'Назад':

        match get_state(message.chat.id):
            case 'set_exam_name':
                where_add(message)

            case 'set_question_name':
                if first_question_flag:
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
            set_exam(message.chat.id, LibBlet.Exam(message.text))

            question_name(message)

        case 'set_question_name':

            Card = LibBlet.Exam.ExaminationCard()

            Card.name = message.text

            short_answer(message)

        case 'set_short_answer':
            first_question_flag = False

            Card.short_answer = message.text

            full_answer(message)

        case 'set_full_answer':
            Card.full_answer = message.html_text

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
    global Card
    exam = get_exam(message.chat.id)
    file_second_name = re.sub(r'\W', r'_', str(exam.name))
    try:
        exam.file_name = f'{message.chat.id}_{file_second_name}'
        pickle.dump(exam, open(f'Exams\\{message.chat.id}_{file_second_name}.dat', 'wb'),
                    protocol=pickle.HIGHEST_PROTOCOL)
        test = pickle.dumps(exam)
        out = pickle.loads(test)
        if not global_edite_mode:
            DataBase.add_exam(message.chat.id, f'{message.chat.id}_{file_second_name}')
        else:
            set_global_edite_mode(False)
        bot.send_message(text='Экзамен сохранен.', chat_id=message.chat.id)
    except Exception as inst:
        print(inst)
        bot.send_message(text=f'Бля, что-то пошло не так\n\n{inst}', chat_id=message.chat.id)


def all_right(call):
    global Card

    if call.data == 'yes':
        question_name(call.message)
        get_exam(call.message.chat.id).add_examination_card(Card)
    else:
        get_exam(call.message.chat.id).add_examination_card(Card)
        save_exam(call.message)

        global first_question_flag
        first_question_flag = True

        set_state(call.message.chat.id, 'ended_add')


def write_card(message):
    bot.send_message(message.chat.id, 'ПроверОчка')
    set_state(message.chat.id, 'Result')
    global Card
    card_text = f'<b>{Card.name}</b>\n{Card.short_answer}\n\n{Card.full_answer}'

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
    file_name = f"{message.chat.id}_" + re.sub(r'\W', r'_', str(get_exam(message.chat.id).name))
    DataBase.delete_exam(file_name)

    get_exam(message.chat.id).name = message.text
    save_exam(message)


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
        bot.send_message(message.chat.id, 'Выберите пункт:')

        bot.register_next_step_handler(message, card_menu)
    except telebot.apihelper.ApiTelegramException:
        bot.send_message(message.chat.id, 'Тут как-то пусто')
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
    global Card
    try:
        if int(message.text) == len(exam.examination_cards) + 1:
            set_global_edite_mode(True)
            question_name(message)

        elif 0 <= int(message.text) - 1 <= len(exam.examination_cards):
            Card = exam.examination_cards[int(message.text) - 1]
            card_text = f'<b>{Card.name}</b>\n{Card.short_answer}\n\n{Card.full_answer}'

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
    global Card
    
    if message.text == 'Назад':
        cards_list(message)
        return

    if message.text == 'На главную':
        hi(message)
        return

    match get_state(message.chat.id):
        case 'edit_question_name':
            Card.name = message.text

        case 'edit_short_answer':
            Card.short_answer = message.text

        case 'edit_full_answer':
            Card.full_answer = message.html_text

        case _:
            return
    write_card(message)

    set_global_edite_mode(True)
    save_exam(message)

    cards_list(message)

# endregion switch card
# endregion switch exam


examination_cards = []
progress = 0
score = 0


# region test
def start_examination(message):
    global examination_cards
    global progress
    global Card
    exam = get_exam(message.chat.id)
    progress = 0
    try:
        if len(exam.examination_cards) < 4:
            bot.send_message(message.chat.id, 'Ты добавил(а) как-то мало билетов в экзамен\n'
                                              f'Минимальное кол-во: 4 (имеется: {len(exam.examination_cards)})')
            exam_menu(message)
            return
    except:
        hi(message)
        return

    examination_cards = exam.swap_list()
    examination(message)


def examination(message):
    set_state(message.chat.id, 'examination')
    global examination_cards
    global progress
    global Card
    global score

    if progress < len(examination_cards):
        Card = examination_cards[progress]

        answer_list = get_exam(message.chat.id).answer_list(Card)
        reply_markup = types.InlineKeyboardMarkup(row_width=4)
        btns = []

        text = str(Card.name) + '\n'

        for i in range(4):
            text += f'{i+1}. {answer_list[i].short_answer} \n'
            call_data = 'ok' if answer_list[i].short_answer == Card.short_answer else 'not_ok'
            btns.append(types.InlineKeyboardButton(i + 1, callback_data=call_data))

        reply_markup.add(*btns)

        bot.send_message(message.chat.id, text, reply_markup=reply_markup)
    else:
        bot.send_message(message.chat.id, f'Билеты кончились. Твой результат: {score}/{len(examination_cards)}\n'
                                          f'Ты хорошо поработал(а)!')
        score = 0

# endregion test


bot.polling(none_stop=True, interval=0)
