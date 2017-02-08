#!/usr/bin/env python2
#encoding: UTF-8

# To change this license header, choose License Headers in Project Properties.
# To change this template file, choose Tools | Templates
# and open the template in the editor.
from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from orders.models import OrderInfo
from member.models import Member
import time
import datetime

class Command(BaseCommand):
     def handle(self, *args, **options):
        try:
            cursor = connections['default'].cursor()
        except ConnectionDoesNotExist as e:
            return None
        
        now = datetime.datetime.now()

        result = cursor.execute("SELECT uid,SUM(price) AS total_amount,COUNT(*) AS total_buys,created FROM `orders_info` WHERE  created>='%s' GROUP BY uid " % (now.strftime('%Y-%m-%d 00:00:00')))
        if not result:
            return None

        rows = cursor.fetchall()
        for row in rows :
            user_id = int(row[0])
            total_amount = float(row[1])
            total_buys = int(row[2])
            last_buytime = row[3]
            member = Member.objects.get(user_id=user_id)
            member.buy_amount += total_amount
            member.buy_times += total_buys
            member.last_buy_date = last_buytime
            member.aver_price = int(member.buy_amount/member.buy_times)
            member.save()

