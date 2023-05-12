import sqlite3 as sql
import os

# connection = sql.connect('userbase.db')
# cursor = connection.cursor()
#
# cursor.execute("""CREATE TABLE IF NOT EXISTS users(
#    user_id INT PRIMARY KEY,
#    user_name TEXT);
#    """)
# connection.commit()
#
# cursor.execute("""CREATE TABLE IF NOT EXISTS exams(
#     user_id INT,
#     exam_id TEXT PRIMARY KEY
#     )""")
# connection.commit()
# connection.close()


def add_user(user_id: int, user_name: str):
    connection = sql.connect('userbase.db')
    cursor = connection.cursor()

    cursor.execute(f"""insert into users
    values('{user_id}', '{user_name}')""")
    connection.commit()
    connection.close()


def add_exam(user_id: int, exam_id: str):
    connection = sql.connect('userbase.db')
    cursor = connection.cursor()

    cursor.execute(f"""insert into exams
    values('{user_id}', '{exam_id}')""")
    connection.commit()
    connection.close()


def get_exam_list(user_id: int):
    connection = sql.connect('userbase.db')
    cursor = connection.cursor()

    cursor.execute(f"SELECT exam_id FROM exams where user_id = '{user_id}';")
    result = cursor.fetchall()
    connection.close()
    return result


def get_user_list():
    connection = sql.connect('userbase.db')
    cursor = connection.cursor()

    cursor.execute(f"SELECT * FROM users;")
    result = cursor.fetchall()
    connection.close()
    return result


def get_user_name(user_id: int):
    connection = sql.connect('userbase.db')
    cursor = connection.cursor()

    cursor.execute(f"SELECT user_name FROM users where user_id = {user_id};")
    result = cursor.fetchall()
    connection.close()
    if result:
        return result
    else:
        result = [[None], []]
        return result


def delete_exam(exam_id: str):
    connection = sql.connect('userbase.db')
    cursor = connection.cursor()

    cursor.execute(f"DELETE FROM exams where exam_id = '{exam_id}';")
    connection.commit()
    connection.close()
    try:
        os.remove(f'./Exams/{exam_id}.blet')
    except:
        print(f'delete error 404. {exam_id}')


def delete_user(user_id: int):
    connection = sql.connect('userbase.db')
    cursor = connection.cursor()

    cursor.execute(f"DELETE FROM users where user_id = '{user_id}';")
    connection.commit()
    connection.close()