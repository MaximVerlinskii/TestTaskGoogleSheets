
from datetime import datetime



import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "google_sheets.settings")
django.setup()
from sheet_to_db.models import Order




ord = Order()
ord.id_from_sheet = 1
ord.number_of_order = 2828244
ord.price_usd = 7.52
ord.delivery_time = datetime.strptime('22.06.2022', '%d.%m.%Y')
ord.price_rub = ord.price_usd * 55.42
ord.save()
