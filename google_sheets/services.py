import datetime
from typing import List
import requests
import xml.etree.cElementTree as ElementTree
import httplib2
from apiclient import discovery
from oauth2client.service_account import ServiceAccountCredentials


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
        today_date = datetime.date.today()
        today_date_str = today_date.strftime('%d/%m/%Y')
        data_from_cbr = requests.get(f'https://www.cbr.ru/scripts/XML_daily.asp?date_req={today_date_str}')
        tree = ElementTree.fromstring(data_from_cbr.content)
        search_result = tree.find('Valute[CharCode="USD"]')
        self.__value = (float(search_result.find('Value').text.replace(',', '.')), today_date)

    def __init__(self):
        self.__refresh_value()

    @property
    def value(self):
        if datetime.date.today() > self.__value[1]:
            self.__refresh_value()
            return self.__value[0]
        return self.__value[0]
