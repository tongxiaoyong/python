# -*- coding: utf-8 -*-
import os
import sys
import datetime
import math
sys.path.append(os.getcwd()+os.path.sep+'thirdapp')
#京东应用配置
import jos.api
jos.setDefaultAppInfo("3C29A89B1FE53D684CDFB4EBEC5AA592", "4561907adc6b452eb91f3a49a897cb03")
objs = jos.api.TradesSoldGetRequest()
objs.order_state = 'WAIT_SELLER_STOCK_OUT,FINISHED_L'
objs.page = 1
objs.page_size = 10
objs.start_date = '2016-11-15 00:00:00'
objs.end_date =  '2016-12-11 00:00:00'
f= objs.getResponse('3a232938-7d79-45f7-8f87-51954288ca75')
print(f)