import sqlite3 as sq

CREATE_QUERY = """CREATE TABLE patient(
                    patient_id INTEGER,
                    name TEXT,
                    last_name TEXT, 
                    middle_name TEXT,
                    polis INTEGER,
                    birthday_date TEXT,
                    polis_series INTEGER NULL
                    ) """


CREATE_TABLE_APPOINTMENTS = """CREATE TABLE appointments(
                                    appointment_id INTEGER,
                                    patient_id INTEGER,
                                    visit_datetime TEXT, 
                                
                                    birthday_date TEXT,
                                    polis_series INTEGER NULL
                                    ) """


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
        self.create_conn()

    def create_patient(self, command, params=tuple()):
        self.execute_command(command, params)

    def update_patient(self):
        pass


db_client = SQLiteClient('patient.db')
db_client.create_conn()
db_client.execute_command(CREATE_QUERY)