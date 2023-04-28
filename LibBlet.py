import pickle
import random
import os


class Exam:
    default_name = 'Unnamed'
    examination_cards = []
    # test_cards = []

    def __init__(self, name=default_name, file_name=None, examination_cards=None):
        if examination_cards is None:
            examination_cards = []
        self.__file_name = file_name
        self.__name = name
        self.examination_cards = examination_cards

    def swap_list(self):
        test_cards = self.examination_cards.copy()
        random.shuffle(test_cards)

        return test_cards

    def answer_list(self, card):
        temp = self.examination_cards.copy()
        random.shuffle(temp)

        if len(temp) > 4:
            temp.remove(card)
            temp = temp[:4]
            temp[random.randint(0, 3)] = card

        return temp

    @property
    def name(self):
        return self.__name

    @name.setter
    def name(self, name):
        self.__name = name

    @property
    def file_name(self):
        return self.__file_name

    @file_name.setter
    def file_name(self, file_name):
        self.__file_name = file_name

    def add_examination_card(self, examination_card):
        self.examination_cards.append(examination_card)

    def delete_examination_card(self, examination_card):
        self.examination_cards.remove(examination_card)

    @staticmethod
    def load_exam(name):
        return pickle.load(open(f'./Exams/{name}.dat', 'rb'))

    class ExaminationCard:
        default_name = 'Unnamed'
        default_question = 'empty'
        default_short_answer = 'empty'
        default_answer = 'empty'

        def __init__(self, name=default_name, short_answer=default_short_answer, full_answer=default_answer):
            if name:
                self.__name = name
            else:
                self.__name = Exam.ExaminationCard.default_name

            if short_answer:
                self.__short_answer = short_answer
            else:
                self.__short_answer = Exam.ExaminationCard.default_short_answer

            if full_answer:
                self.__answer = full_answer
            else:
                self.__answer = Exam.ExaminationCard.default_answer

        @property
        def name(self):
            return self.__name

        @name.setter
        def name(self, name):
            if name:
                self.__name = name
            else:
                self.__name = Exam.ExaminationCard.default_name

        @property
        def short_answer(self):
            return self.__short_answer

        @short_answer.setter
        def short_answer(self, short_answer):
            self.__short_answer = short_answer

        @property
        def full_answer(self):
            return self.__answer

        @full_answer.setter
        def full_answer(self, full_answer):
            self.__answer = full_answer
