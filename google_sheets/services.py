from datetime import datetime
import time
from typing import List, Tuple
import requests
import xml.etree.cElementTree as ElementTree
import httplib2

from apiclient import discovery
from oauth2client.service_account import ServiceAccountCredentials

# the following lines are required to work with django models
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "google_sheets.settings")
django.setup()
from sheet_to_db.models import Order


class SheetParser:
    """
    Class for parsing Google Sheets. Google Sheets page -> list of lists (table)
    """

    def __init__(self, cred_json_path: str, spreadsheet_id: str, name_of_list: str):
        """
        Prepare request to get google sheets page
        Args:
            cred_json_path (str): path of google credential, example: 'creds/cred.json'
            spreadsheet_id (str): id of spreadsheet, can be taken from url of spreadsheet
            name_of_list (str): name of list in google sheets document, example: 'Page1'
        """
        credentials = ServiceAccountCredentials.from_json_keyfile_name(cred_json_path,
                                                                       ['https://www.googleapis.com/auth/spreadsheets',
                                                                        'https://www.googleapis.com/auth/drive'])
        httpauth = credentials.authorize(httplib2.Http())
        service = discovery.build('sheets', 'v4', http=httpauth)

        self.reader = service.spreadsheets().values().get(spreadsheetId=spreadsheet_id,
                                                          range=name_of_list,
                                                          majorDimension='ROWS')

    def get_sheet(self) -> List[list]:
        """
        This method is used to query a Google Sheets page.

        Returns: (List[list]) Google Sheets page in form of table (list of lists),
                 example: [
                           ['A1', 'B1', 'C1', 'D1'],
                           ['A2', 'B2', 'C2', 'D2'],
                           ['A3', 'B3', 'C3', 'D3']
                          ]
        """
        sheet = self.reader.execute()['values']
        return sheet


class UsdExchangeRate:
    """
    Class for parsing USD exchange rate once a day.
    """

    def __refresh_value(self):
        """
        Private method to refresh exchange rate value at private attribute __value.
        """
        today_date = datetime.today()
        today_date_str = today_date.strftime('%d/%m/%Y')
        data_from_cbr = requests.get(f'https://www.cbr.ru/scripts/XML_daily.asp?date_req={today_date_str}')
        tree = ElementTree.fromstring(data_from_cbr.content)
        search_result = tree.find('Valute[CharCode="USD"]')
        self.__value = (float(search_result.find('Value').text.replace(',', '.')), today_date.date())

    def __init__(self):
        self.__refresh_value()

    @property
    def value(self) -> float:
        """
        Property getter method for getting 'fresh' exchange rate value.
        Returns: (float) today exchange rate value
        """
        if datetime.today().date() > self.__value[1]:
            self.__refresh_value()
            return self.__value[0]
        return self.__value[0]


class SheetToDatabase:

    @staticmethod
    def full_filling(list_of_obj_list: List[list], usd_rub: UsdExchangeRate):
        Order.objects.all().delete()

        for obj_list in list_of_obj_list:
            order_obj = SheetToDatabase.create_object_by_list(obj_list, usd_rub.value)
            order_obj.save()

    @staticmethod
    def update_or_add_and_delete(differences: tuple[list[list], set], usd_rub: UsdExchangeRate):
        if not differences[0]:
            for ord_list in differences[0]:
                try:
                    ord_obj = Order.objects.get(id_from_sheet=ord_list[0])
                    update_ord_obj = SheetToDatabase.update_object_by_list(ord_list, usd_rub.value, ord_obj)
                    update_ord_obj.save()

                except Order.DoesNotExist:
                    new_ord_object = SheetToDatabase.create_object_by_list(ord_list, usd_rub.value)
                    new_ord_object.save()
        for id_del in differences[1]:
            obj_to_delete = Order.objects.get(id_from_sheet=id_del)
            obj_to_delete.delete()

    @staticmethod
    def create_object_by_list(obj_list: list, usd_to_rub_value: float) -> Order:
        order_obj = Order()
        res_obj = SheetToDatabase.update_object_by_list(obj_list, usd_to_rub_value, order_obj)
        return res_obj

    @staticmethod
    def update_object_by_list(obj_list: list, usd_to_rub_value: float, obj: Order) -> Order:
        obj.id_from_sheet = int(obj_list[0])
        obj.number_of_order = int(obj_list[1])
        obj.price_usd = float(obj_list[2])
        obj.delivery_time = datetime.strptime(obj_list[3], '%d.%m.%Y')
        obj.price_rub = obj.price_usd * usd_to_rub_value
        return obj

    @staticmethod
    def difference_between_two_sheet(prev_sheet: list[list], sheet: list[list]) -> tuple[list[list], set]:
        id_of_orders_prev = set([inner_list[0] for inner_list in prev_sheet if inner_list != []])
        id_of_orders_new = set([inner_list[0] for inner_list in sheet if inner_list != []])
        id_to_create = id_of_orders_new - id_of_orders_prev
        id_to_delete = id_of_orders_prev - id_of_orders_new

        differences_plus = []
        if len(prev_sheet) < len(sheet):
            for i in range(len(sheet) - len(prev_sheet)):
                prev_sheet.append([])
        elif len(sheet) < len(prev_sheet):
            for i in range(len(prev_sheet) - len(sheet)):
                sheet.append([])
        for line1, line2 in zip(prev_sheet, sheet):
            if (line2 != [] and (line2[0] in id_to_create)) or line1 != line2:
                differences_plus.append(line2)
        return differences_plus, id_to_delete


usd_to_rub = UsdExchangeRate()

my_sheet = SheetParser('cred.json', '13BC668h2hJNn4K4UlyTd1CxlHghBoxxba8uhNu4Sd2Q', 'Лист1').get_sheet()[1:]

SheetToDatabase.full_filling(my_sheet, usd_to_rub)

while True:
    time_point1 = time.time()
    try:
        my_sheet_2 = SheetParser('cred.json', '13BC668h2hJNn4K4UlyTd1CxlHghBoxxba8uhNu4Sd2Q', 'Лист1').get_sheet()[1:]
        if my_sheet != my_sheet_2:
            diff = SheetToDatabase.difference_between_two_sheet(my_sheet, my_sheet_2)
            SheetToDatabase.update_or_add_and_delete(diff, usd_to_rub)
            my_sheet = my_sheet_2.copy()

    except Exception as Ex:  # Bare exception -> bad     # TODO validation instead of this
        print(Ex, Ex.__cause__, Ex.__context__)

    time_point2 = time.time()
    if time_point2 - time_point1 < 2:
        time.sleep(2 - (time_point2 - time_point1))
