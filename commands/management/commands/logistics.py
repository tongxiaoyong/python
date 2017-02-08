# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from logistics.models import LogisticsManagement
from cpapi.common.kdniao import ExpressApi
import time
import datetime

class Command(BaseCommand):
     def handle(self, *args, **options):
        try:
            cursor = connections['default'].cursor()
        except ConnectionDoesNotExist as e:
            return None
        
        now = datetime.datetime.now()

        result = cursor.execute("SELECT id,company_id,logistics_no FROM `logistics_management` WHERE  send_status > 0 AND  logistics_status < 2 AND logistics_no <>'' LIMIT 300")
        if not result:
            return None

        rows = cursor.fetchall()
        for row in rows :
            logistic_id = row[0]
            company_id = row[1]
            logistics_no = row[2]
            expressApi = ExpressApi()
            expressApi.getOrderTrace(company_id,logistics_no)
            data = expressApi.get_json()
            
            if 'State' in data and data['State']:
                logistic = LogisticsManagement.objects.get(id=logistic_id)
                logistic.logistics_status = data['State']
                logistic.save()
                
            time.sleep(0.2)

