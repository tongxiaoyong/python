# -*- coding: utf-8 -*-
import datetime
import math
import os
import sys
from thirdapp import write_log
sys.path.append(os.getcwd() + os.path.sep + 'thirdapp')
#有赞应用配置
import yz.api
yz.setDefaultAppInfo("有赞应用ＩＤ", "有赞应用秘密")

#同步增量订单(<= 1天)
def sync_incre_order_youzan(yz, access_token = None, start_modified = "", end_modified = ""):
    from thirdapp.tasks import consumer_youzan_order
    
    is_succ = False
    if not start_modified:
        start_modified = days_ago(1)
    if not end_modified:
        end_modified = days_ago(0)

    objs = yz.api.TradesSoldIncrementGetRequest()
    objs.fields = "tid"
    objs.start_update = start_modified
    objs.end_update = end_modified
    objs.status = "WAIT_SELLER_SEND_GOODS"
    objs.page_no = 1
    objs.page_size = 50
    try:
        while True:
            print("当前page=============%s%s%s" % (objs.page_no, objs.start_update, objs.end_update))

            f = objs.getResponse()
            trades = f['response'].get('trades',[])
            total_results = f['response'].get('total_results',0)
            total_pages = math.ceil(int(total_results) / objs.page_size)

            for trade in trades:
                if trade.get("tid"):
                    print(trade.get("tid"))
                    consumer_youzan_order.delay(trade['tid'])
                    is_succ = True
                
            objs.page_no += 1
            if objs.page_no > total_pages: 
                break
                
    except Exception as err:
        write_log(err_from=1,content="%s"%(err))
        print(err)        
    return {"is_succ": is_succ, "start_modified": start_modified, "end_modified": end_modified}


#同步订单（<3个月）
def sync_order_youzan(yz, access_token = None, start_modified = "", end_modified = ""):
    from thirdapp.tasks import consumer_youzan_order
    
    is_succ = False
    if not start_modified:
        start_modified = days_ago(1)
    if not end_modified:
        end_modified = days_ago(0)

    objs = yz.api.TradesSoldGetRequest()
    objs.fields = "tid"
    objs.start_created = start_modified
    objs.end_created = end_modified
    objs.status = "WAIT_SELLER_SEND_GOODS"
    objs.page_no = 1
    objs.page_size = 50
    try:
        while True:
            print("当前page=============%s%s%s" % (objs.page_no, objs.start_created, objs.end_created))
            f = objs.getResponse()
            trades = f['response'].get('trades',[])
            total_results = f['response'].get('total_results',0)
            total_pages = math.ceil(int(total_results) / objs.page_size)

            for trade in trades:
                if trade.get("tid"):
                    consumer_youzan_order.delay(trade['tid'])
                    is_succ = True
                
            objs.page_no += 1
            if objs.page_no > total_pages: 
                break    
            
    except Exception as err:
        write_log(err_from=1,content="%s"%(err))
        print(err)   
    return {"is_succ": is_succ, "start_modified": start_modified, "end_modified": end_modified}
            
def days_ago(days=1):
    return (datetime.datetime.now() - datetime.timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")

