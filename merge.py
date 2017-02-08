# -*- coding: utf-8 -*-
from cpapi import cpapi_celery_app
import datetime
from goods.models import SKU
from orders.api import create_order
from orders.models import OrderInfo
import os
import sys
from thirdapp import write_log
import time

def merge_into_sys_order(third_order_id):
    from .models import ThirdAppOrder, ThirdAppDetail
    from .serializers import ThirdAppOrderSerializer, ThirdAppDetailSerializer
    try:
        third_order = ThirdAppOrder.objects.filter(id=third_order_id)
        trade = ThirdAppOrderSerializer(third_order, many=True).data[0]
        third_details = ThirdAppDetail.objects.filter(order_no=str(trade.get("order_no")))
        orders = ThirdAppDetailSerializer(third_details, many=True).data
        skus = _get_skus(orders, ("outer_iid"))
        if not skus:
            return True

        province = _out_convert_id(trade.get("receiver_province", ""), 0)
        province_id = province and province.id or 0

        if _is_special_area(trade.get("receiver_city", "")):
            city = _out_convert_id(trade.get("receiver_town", ""), province_id, True)
            city_id = city and city.parent_id or 0
            if city_id < 1:
                city = _out_convert_id("市辖区", province_id)
                city_id = city and city.id or 0
        else:
            city = _out_convert_id(trade.get("receiver_city", ""), province_id)
            city_id = city and city.id or 0

        if _is_special_area(trade.get("receiver_province")):
            town = _out_convert_id(trade.get("receiver_town", ""), city_id, True)
            if city.name != "市辖区":
                town_id = town and town.id or city_id
            else:
                town_id = 0
        else:
            town = _out_convert_id(trade.get("receiver_town", ""), city_id)
            town_id = town and town.id or 0

        payment_price = float(trade.get("payment", 0))*100
        _create_order(
                      data={
                      "uid": _get_uid(trade),
                      "deadline": _calc_deadline(trade.get("trade_memo", "")),
                      "date_type": 0,
                      "province_id": int(province_id),
                      "city_id": int(city_id),
                      "area_id": int(town_id),
                      "consignee_address": trade.get("receiver_address", ""),
                      "consignee_name": trade.get("receiver_name", ""),
                      "consignee_phone": trade.get("receiver_mobile", ""),
                      "source": OrderInfo.ORDER_SOURCE_YOUZAN,
                      "price": payment_price,
                      "outer_order_no": trade.get("order_no", 0),
                      }, skus=skus
                      )

        third_order.update(audit_status=ThirdAppOrder.AUDIT_STATUS_PASS)
    except Exception as err:
        write_log(err_from=1, content="%s third_order_id:%s" % (err, third_order_id))
        return False
        
    return True


def _outer_order_is_exist(outer_order_no):
    order_info = OrderInfo.objects.filter(outer_order_no=outer_order_no)
    if order_info:
        return order_info
    return False
    
    
def _create_order(** kwargs):
    order_data = kwargs.get('data')
    order_skus = kwargs.get('skus')
    if not order_skus:
        return False
    
    outer_order_no = order_data.get('outer_order_no')
    if not _outer_order_is_exist(outer_order_no):
        _paid(create_order(** kwargs))
    else:
        pass
 
def _paid(order_data):
    instance_id = order_data.get("id")
    if instance_id:
        instance = OrderInfo.objects.get(id=instance_id)
        instance.paid(**{
            'uid' : 11,
            'username' : "审核帐号",
            'ip' : '',
        })

def _is_special_area(region_name):
    if not region_name:
        return False
    
    is_special = region_name.find("上海") > -1 or region_name.find("北京") > -1 or region_name.find("重庆") > -1 or region_name.find("天津") > -1
    if is_special:
        return True
    return False


def _get_uid(trade):
    from base.api import register_user
    from base.models import User
    from django.db.models import Q
    channel_id = trade.get("channel_id")
    mobile = ""
    #有赞订单
    if str(channel_id) == "6":
        username = "yz_%s" % (trade.get("account_uid", ""))
    else:
        mobile = trade.get("receiver_mobile", "")
        username = "at_%s" % (mobile)
        
    
    user = User.objects.filter(username=username)
    if not user:
        serializer = register_user({
                                   "username": username,
                                   "password": "123456",
                                   "mobile": mobile
                                   });
        return serializer.data.get("id", 1)
    return user[0].id
    

def _calc_deadline(seller_memo):
    date_str = seller_memo[-11:23]  #卖家备注  带花瓶XXX/XXXX/2016年11月30日
    if date_str:
        dead_time = time.mktime(time.strptime(date_str, '%m月%d日'))
        return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(dead_time))
    
    now_time = datetime.datetime.now()
    days = _near_week_1_6(now_time.weekday())
    week_datetime = (now_time + datetime.timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    return week_datetime


def _near_week_1_6(week_day):
    days = 7-week_day
    i = 1
    while i <= days:
        if (week_day + i) % 7 == 0 or (week_day + i) % 7 == 5:
            return i
        i += 1

        
def _out_convert_id(area_name, parent_id, special=False):
    from base.models import Region
    
    if not area_name:
        return None
    
    if special and  parent_id > 0:
        region = Region.objects.filter(name__contains=area_name.rstrip('省').rstrip('市'), parent_id__in=[110100, 110200, 120100, 120200, 310100, 310200, 500100, 500200])    
    else:
        region = Region.objects.filter(name__contains=area_name.rstrip('省').rstrip('市'), parent_id=parent_id)
        
    if region:
        return region[0]
    
    return None


def _get_skus(outer_skus, items=("outer_iid")):
    skus_id = []
    for s in outer_skus:
        sku_code = s.get("outer_iid")
        sku = SKU.objects.query_by_code(sku_code)
        if not sku:
            raise ValueError("SKU NotExist: %s" % (sku_code))

        skus_id.append(sku.id)
        
    return skus_id

    
    
