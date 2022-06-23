from datetime import datetime
from typing import List
import requests
import xml.etree.cElementTree as ElementTree
import httplib2

from apiclient import discovery
from oauth2client.service_account import ServiceAccountCredentials

import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "google_sheets.settings")
django.setup()

from sheet_to_db.models import Order


class Sheet:

    def __init__(self, cred_json_path: str, spreadsheet_id: str, name_of_list: str):
        credentials = ServiceAccountCredentials.from_json_keyfile_name(cred_json_path,
                                                                       ['https://www.googleapis.com/auth/spreadsheets',
                                                                        'https://www.googleapis.com/auth/drive'])
        httpauth = credentials.authorize(httplib2.Http())
        service = discovery.build('sheets', 'v4', http=httpauth)

        self.reader = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id,
                                                          range=name_of_list,
                                                          majorDimension='ROWS')

    def get_sheet(self):
        sheet: List[list] = self.reader.execute()['values'][1:]
        return sheet


class UsdCourse:

    def __refresh_value(self):
        today_date = datetime.today()
        today_date_str = today_date.strftime('%d/%m/%Y')
        data_from_cbr = requests.get(f'https://www.cbr.ru/scripts/XML_daily.asp?date_req={today_date_str}')
        tree = ElementTree.fromstring(data_from_cbr.content)
        search_result = tree.find('Valute[CharCode="USD"]')
        self.__value = (float(search_result.find('Value').text.replace(',', '.')), today_date)

    def __init__(self):
        self.__refresh_value()

    @property
    def value(self):
        if datetime.today() > self.__value[1]:
            self.__refresh_value()
            return self.__value[0]
        return self.__value[0]


class SheetToDatabase:

    def __init__(self, list_of_obj_list: List[list]):
        usd_to_rub = UsdCourse()

        for obj_list in list_of_obj_list:
            SheetToDatabase.create_object_by_list(obj_list, usd_to_rub)

    @staticmethod
    def create_object_by_list(obj_list, usd_to_rub):
        order_obj = Order()
        order_obj.id_from_sheet = int(obj_list[0])
        order_obj.number_of_order = int(obj_list[1])
        order_obj.price_usd = float(obj_list[2])
        order_obj.delivery_time = datetime.strptime(obj_list[3], '%d.%m.%Y')
        order_obj.price_rub = order_obj.price_usd * usd_to_rub.value
        order_obj.save()


my_sheet = Sheet('cred.json', '13BC668h2hJNn4K4UlyTd1CxlHghBoxxba8uhNu4Sd2Q', 'Лист1')

SheetToDatabase(my_sheet.get_sheet())

