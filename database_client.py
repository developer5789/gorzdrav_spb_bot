import sqlite3 as sq

PATIENT_FIELDS = {'имя': 'name',
                  'фамилия': 'last_name',
                  'отчество': 'middle_name',
                  'дата рождения': 'birthday_date',
                  'номер полиса': 'polis',
                  'серия полиса': 'polis_series'
}

CREATE_QUERY = """CREATE TABLE patient(
                    patient_id INTEGER,
                    name TEXT,
                    last_name TEXT, 
                    middle_name TEXT,
                    polis TEXT,
                    birthday_date TEXT,
                    polis_series TEXT 
                    ) """

CREATE_PATIENT = """ INSERT INTO patient 
                     VALUES(?, ?, ?, ?, ?, ?, ?)
"""

FIND_QUERY = """SELECT * FROM patient
                 WHERE patient_id=%d
"""


UPDATE_QUERY = """
                    UPDATE patient
                    SET %s='%s'
                    WHERE patient_id=%d
"""

DEL_PATIENT = """DELETE FROM patient
                    WHERE patient_id=%d"""


class SQLiteClient:

    def __init__(self, filepath: str):
        self.filepath = filepath
        self.conn = None

    def create_conn(self):
        self.conn = sq.connect(self.filepath, check_same_thread=False)

    def close_con(self):
        self.conn.close()

    def execute_command(self, command: str, params=tuple()):
        if self.conn is not None:
            self.conn.execute(command, params)
            self.conn.commit()
        else:
            raise ConnectionError('you need to create connection to databasse')

    def execute_select_command(self, command):
        if self.conn is not None:
            cursor = self.conn.cursor()
            cursor.execute(command)
            return cursor.fetchall()
        else:
            raise ConnectionError('you need to create connection to database')


class DatabaseUser(SQLiteClient):
    def __init__(self, file_path: str):
        super().__init__(file_path)

    def create_patient(self, patient):
        attrs = tuple(value for key, value in patient.__dict__.items() if key != 'api_client')
        self.execute_command(CREATE_PATIENT, params=attrs)

    def update_patient(self, user_id: int, field: str, new_value: str):
        command = UPDATE_QUERY % (field, new_value, user_id)
        self.execute_command(command)

    def find_patient(self, user_id: int):
        command = FIND_QUERY % user_id
        res = self.execute_select_command(command)
        return res[0] if res else res

    def del_patient(self, user_id: int):
        command = DEL_PATIENT % user_id
        self.execute_command(command)



