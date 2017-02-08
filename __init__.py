# -*- coding: utf-8 -*-
import os
import sys
import datetime,time
import math

sys.path.append(os.getcwd()+os.path.sep+'thirdapp')
#淘宝应用配置
import top.api
top.setDefaultAppInfo("应用ＩＤ", "应用秘密")

#同步增量订单(<= 1天)
def sync_incre_order_taobao(top, access_token, start_modified = "", end_modified = ""):
    from thirdapp.tasks import consumer_taobao_order
    
    is_succ = False
    if not start_modified :
        start_modified = days_ago(1)
    if not end_modified:
        end_modified = days_ago(0)
    
    if diff_seconds(start_modified,end_modified) > 86400 :
        start_modified = days_ago(1)
        
    objs = top.api.TradesSoldIncrementGetRequest()
    objs.fields = "tid"
    objs.start_modified = start_modified
    objs.end_modified = end_modified
    objs.status = "WAIT_SELLER_SEND_GOODS"
    objs.page_no = 1
    objs.page_size = 50
    try:
        while True:
            print("当前page=============%s%s%s"%(objs.page_no,objs.start_modified,objs.end_modified))

            f= objs.getResponse(access_token)
            trades = f['trades_sold_increment_get_response']['trades']['trade']
            total_results = f['trades_sold_increment_get_response']['total_results']
            total_pages = math.ceil(int(total_results)/objs.page_size)

            for trade in trades:
                print("tid %s"%(trade['tid']))
                consumer_taobao_order.delay(trade['tid'],access_token)
                is_succ = True
                
            objs.page_no+=1
            if objs.page_no > total_pages : 
                break
                
    except Exception as err:
        write_log(err_from=2,content="%s"%(err))
        print(err)        
    return {"is_succ" : is_succ,"start_modified" : start_modified, "end_modified" : end_modified}


#同步订单（<3个月）
def sync_order_taobao(top, access_token, start_modified = "", end_modified = ""):
    from thirdapp.tasks import consumer_taobao_order
    
    is_succ = False
    if not start_modified:
        start_modified = days_ago(1)
    if not end_modified:
        end_modified = days_ago(0)

    objs = top.api.TradesSoldGetRequest()
    objs.fields = "tid"
    objs.start_modified = start_modified
    objs.end_modified = end_modified
    objs.status = "WAIT_SELLER_SEND_GOODS"
    objs.page_no = 1
    objs.page_size = 50
    try:
        while True:
            print("当前page=============%s%s%s"%(objs.page_no,objs.start_modified,objs.end_modified))
            f= objs.getResponse(access_token)
            trades = f['trades_sold_get_response']['trades']['trade']
            total_results = f['trades_sold_get_response']['total_results']
            total_pages = math.ceil(int(total_results)/objs.page_size)

            for trade in trades:
                print("tid %s"%(trade['tid']))
                consumer_taobao_order.delay(trade['tid'],access_token)
                is_succ = True
                
            objs.page_no+=1
            if objs.page_no > total_pages : 
                break    
            
    except Exception as err:
        write_log(err_from=2,content="%s"%(err))
        print(err)   
    return {"is_succ" : is_succ,"start_modified" : start_modified, "end_modified" : end_modified}
            
def days_ago(days = 1):
    return (datetime.datetime.now() - datetime.timedelta(days = days)).strftime("%Y-%m-%d %H:%M:%S")

def diff_seconds(s,e):
    s = time.mktime(time.strptime(s,'%Y-%m-%d %H:%M:%S'))
    e = time.mktime(time.strptime(e,'%Y-%m-%d %H:%M:%S'))
    return int(e)-int(s)

def write_log(** kwargs):
    from thirdapp.models import FailedLog
    content = kwargs.get('content') 
    err_from = kwargs.get('err_from')
    if err_from and content:
        return FailedLog.objects.create(err_from=err_from, content=content)
