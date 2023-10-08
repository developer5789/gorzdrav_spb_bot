import requests
from pprint import pprint

BASE_URL = 'https://gorzdrav.spb.ru/_api/api/v2/'
headers = {
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                  ' (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
    'X-Requested-With': 'XMLHttpRequest'
}

# url для получения списка поликлинник в районе
URL_LPUS = BASE_URL + 'shared/district/<district_id>/lpus'

# url для получения списка со специальностями
URL_SPECIALITIES = BASE_URL + 'schedule/lpu/<lpu_id>/specialities'

# url для получения списка врачей по специальности
URL_DOCTORS = BASE_URL + 'schedule/lpu/<lpu_id>/speciality/<speciality_id>/doctors'

# url для получения списка свободных талонов к врачу
URL_APPOINTMENTS = BASE_URL + 'schedule/lpu/<lpu_id>/doctor/<doctor_id>/appointments'

URL_AVALAIBLE_POLYCS = BASE_URL + 'oms/attachment/lpus'

URL_DISTRICTS = BASE_URL + 'shared/districts'
URL_CHECK = BASE_URL + 'oms/attachment/check'
URL_CREATE = BASE_URL + 'appointment/create'
URL_MADE_APPOINTMENTS = BASE_URL + 'appointments'
URL_SEARCH = BASE_URL + 'patient/search'

class Patient:
    def __init__(self, patient_id, name=None, last_name=None,
                 middle_name=None, polis=None, birthdate=None, polis_series=''):
        self.api_client = ApiClient()
        self.patient_id = patient_id
        self.name = name
        self.last_name = last_name
        self.middle_name = middle_name
        self.polis = polis
        self.birthdate = birthdate
        self.polis_series = polis_series

    def check(self, polyc_id):
        res = self.api_client.check(self, polyc_id)
        return res

    def get_patient_polycs(self):
        polycs = self.api_client.get_lst_polycs(self)
        return polycs['result']


class ApiClient:

    @staticmethod
    def get(url, params=None):
        resp = requests.get(url, headers=headers, params=params)
        result = resp.json()
        return result

    @staticmethod
    def post(url, json):
        pprint(json)
        resp = requests.post(url, json=json, headers=headers)
        result = resp.json()['success']
        return result

    def get_districts(self):
        districts = self.get(URL_DISTRICTS)
        return districts['result']

    def get_polyclinics(self, name, district_id):
        url = f'{BASE_URL}shared/district/{district_id}/lpus'
        result = self.get(url)
        lst_polycs = []
        for organization in result['result']:
            if name.lower() in organization['lpuFullName'].lower():
                lst_polycs.append(organization)
        return lst_polycs

    def get_appointments(self, clinic_id, doctor_id):
        url = f'{BASE_URL}schedule/lpu/{clinic_id}/doctor/{doctor_id}/appointments'
        result = self.get(url)
        return result

    def get_specialities(self, polyc_id):
        url = f'{BASE_URL}schedule/lpu/{polyc_id}/specialties'
        result = self.get(url)
        return result['result']

    def get_doctors(self, polyc_id, spec_id):
        url = f'{BASE_URL}schedule/lpu/{polyc_id}/speciality/{spec_id}/doctors'
        result = self.get(url)
        return result['result']

    def get_lst_polycs(self, patient: Patient):
        params = {
            'polisN': patient.polis,
            'polisS': patient.polis_series
        }
        res = self.get(URL_AVALAIBLE_POLYCS, params=params)
        return res

    @staticmethod
    def check(patient: Patient, polyc_id):
        data = {
            'birthdate': patient.birthdate,
            'esiaId': None,
            'lastName': patient.last_name,
            'lpuId': polyc_id,
            'polisN': patient.polis,
            'polisS': patient.polis_series
        }
        resp = requests.post(URL_CHECK, json=data, headers=headers)
        result = resp.json()['result']
        return result

    def make_appointment(self, patient_id, patient_inf, clinic_id, appointment_id):
        data = {
            "esiaId": None,
            "lpuId": clinic_id,
            "patientId": patient_id,
            "appointmentId": appointment_id,
            "referralId": None,
            "ipmpiCardId": None,
            "recipientEmail": "",
            "patientLastName": patient_inf[2],
            "patientFirstName": patient_inf[1],
            "patientMiddleName": patient_inf[3],
            "patientBirthdate": '-'.join(patient_inf[5].split('.')[::-1]) + "T00:00:00",
        }
        res = self.post(URL_CREATE, data)
        return res

    def search_patient(self, clinic_id, patient_inf):
        try:
            params = {
                'lpuid': clinic_id,
                'lastName': patient_inf[2],
                'firstName': patient_inf[1],
                'middleName': patient_inf[3],
                'birthdate': '-'.join(patient_inf[5].split('.')[::-1]) + "T00:00:00",
                'birthdateValue': patient_inf[5]
            }
            res = self.get(URL_SEARCH, params)
            if res['success'] and res['result']:
                return res['result']
        except:
            return None

    def get_made_appointments(self, patient_id, clinic_id):
        params = {
            "lpuId": clinic_id,
            'patientId': patient_id
        }
        res = self.get(URL_MADE_APPOINTMENTS, params)
        return res['result']
