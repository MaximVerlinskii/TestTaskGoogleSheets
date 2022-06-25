from django.db import models


class Order(models.Model):
    """
    Table of orders
    """

    id_from_sheet = models.IntegerField(verbose_name='№')
    number_of_order = models.IntegerField(verbose_name='заказ №')
    price_usd = models.FloatField(verbose_name='стоимость,$')
    delivery_time = models.DateTimeField(verbose_name='срок поставки')
    price_rub = models.FloatField(verbose_name='стоимость в руб.')
