import re


class Validator:
    regex_fio = re.compile(r'[а-яА-яЁё]+\s+[а-яА-яЁё]+\s+[а-яА-яЁё]+')
    regex_word = re.compile(r'[а-яА-яЁё]+')

    @classmethod
    def validate_fio(cls, fio: str):
        return cls.regex_fio.fullmatch(fio)

    @staticmethod
    def validate_birthdate(st: str):
        try:
            day, month, year = [int(value.strip()) for value in st.split('.')]
            condition = 1900 < year <= 2023 and 1 <= month <= 12 and 1 <= day <= 31
            return f'{day:02}.{month:02}.{year}' if condition else False
        except:
            return False

    @staticmethod
    def validate_numb(numb: str, len_numb):
        numb = numb.strip()
        return numb if len(numb) == len_numb and numb.isdigit() else False

    @classmethod
    def validate_word(cls, word):
        word = word.strip()
        res = cls.regex_word.fullmatch(word)
        return res.string if res else None



