# -*- coding: utf-8 -*-
from cpapi import cpapi_celery_app
import datetime
from goods.models import SKU
from .api import create_thirdapp_order
from thirdapp.models import ThirdAppOrder
from thirdapp import write_log
import os
import sys
import time
sys.path.append(os.getcwd() + os.path.sep + 'thirdapp')
from cpapi.common import get_huaji_logger
logger = get_huaji_logger()


#有赞订单入库
@cpapi_celery_app.task()
def consumer_youzan_order(tid, access_token=None):
    from thirdapp.youzan import yz
    objs = yz.api.TradeFullinfoGetRequest()
    objs.fields = "tid,price,total_fee,payment,created,pay_time,orders,status,receiver_city,num_iid,title,receiver_state,receiver_name, \
                   receiver_district,receiver_mobile,receiver_address,trade_memo,sub_trades,type,fans_info"
    objs.tid = tid
    try:
        result = objs.getResponse()
        trade = result['response'].get('trade', {})

        skus = _get_skus(trade.get("orders", []),("outer_sku_id","outer_item_id"))
        if not skus:
            return True
        
        account_uid = trade.get('fans_info').get('buyer_id',0)
        _create_order(
                      data={
                      "account_uid" : account_uid ,
                      "order_no": trade.get("tid", 0),
                      "status": trade.get("status", 0),
                      "buyer_nick": 0,
                      "buyer_message": trade.get("buyer_message", ""),
                      "buyer_memo": trade.get("buyer_memo", ""),
                      "total_fee": trade.get("total_fee", 0),
                      "payment": trade.get("payment", 0),
                      "seller_memo": trade.get("seller_memo", ""),
                      "receiver_name": trade.get("receiver_name", ""),
                      "receiver_province": trade.get("receiver_state", ""),
                      "receiver_city": trade.get("receiver_city", 0),
                      "receiver_town": trade.get("receiver_district", 0),
                      "receiver_address": trade.get("receiver_address", 0),
                      "receiver_mobile": trade.get("receiver_mobile", 0),
                      "receiver_phone": trade.get("receiver_phone", 0),
                      "seller_id": trade.get("seller_id", 0),
                      "channel_id": ThirdAppOrder.ORDER_SOURCE_YOUZAN,
                      "audit_status": 0,
                      }, skus=skus
                      )
        
    except Exception as err:
        write_log(err_from=1,content="%s tid:%s"%(err,tid))
        print(err)
        
    return True


#淘宝订单入库
@cpapi_celery_app.task()
def consumer_taobao_order(tid, access_token):
    import top.api
    objs = top.api.TradeFullinfoGetRequest()
    objs.fields = "tid,status,created,pay_time,modified,consign_time,buyer_nick,buyer_message, buyer_memo,post_fee,total_fee, payment, \
                seller_flag,seller_memo,consign_time,title, \
                receiver_name, receiver_state,receiver_city, receiver_district, receiver_address, receiver_mobile, \
                receiver_phone,receiver_zip, \
                orders.adjust_fee,orders.buyer_rate,orders.discount_fee,orders.end_time,orders.num,orders.num_iid,orders.oid, \
                orders.order_from,orders.outer_iid,orders.outer_sku_id,orders.payment,orders.pic_path,orders.price,orders.refund_status, \
                orders.seller_rate,orders.seller_type,orders.sku_properties_name,orders.status,orders.title, \
                orders.total_fee,discount_fee, \
                promotion_details" 
    objs.tid = tid
    
    try:
        result = objs.getResponse(access_token)
        trade = result['trade_fullinfo_get_response'].get('trade', {})
        skus = _get_skus(trade["orders"].get("order", []),("outer_sku_id","outer_iid"))
        if not skus:
            return True

        _create_order(
                      data={
                      "order_no": trade.get("tid", 0),
                      "status": trade.get("status", 0),
                      "buyer_nick": 0,
                      "buyer_message": trade.get("buyer_message", ""),
                      "buyer_memo": trade.get("buyer_memo", ""),
                      "total_fee": trade.get("total_fee", 0),
                      "payment": trade.get("payment", 0),
                      "seller_memo": trade.get("seller_memo", ""),
                      "receiver_name": trade.get("receiver_name", ""),
                      "receiver_province": trade.get("receiver_state", ""),
                      "receiver_city": trade.get("receiver_city", 0),
                      "receiver_town": trade.get("receiver_district", 0),
                      "receiver_address": trade.get("receiver_address", 0),
                      "receiver_mobile": trade.get("receiver_mobile", 0),
                      "receiver_phone": trade.get("receiver_phone", 0),
                      "seller_id": trade.get("seller_id", 0),
                      "channel_id": ThirdAppOrder.ORDER_SOURCE_TAOBAO,
                      "audit_status": 0,
                      }, skus=skus
                      )

    except Exception as err:
        write_log(err_from=2,content="%s tid:%s"%(err,tid))
        print(err)
        
    return True

    
def _create_order( ** kwargs):
    
    order_data = kwargs.get('data')
    order_skus = kwargs.get('skus')
    if not order_skus:
        return False
    
    if order_data.get("order_no",None):
        ThirdAppOrder.objects.filter(order_no=order_data.get("order_no")).delete()
        create_thirdapp_order( ** kwargs)
        
  
def _get_skus(outer_skus, items=("outer_sku_id")):  
    skus = []
    for s in outer_skus:
        for item in items:
            sku_code = s.get(item)
            if sku_code:
                break
                
        skus.append({
            "sku_id" : s.get('sku_id',''),
            "sku_name" : s.get('sku_properties_name',''),
            "sku_image" : s.get('pic_path',''),
            "outer_iid" : sku_code,
            "price" : s.get('price','0'),
            "nums" : s.get('num','1'),
        })
        
    return skus
        