# -*- coding: utf-8 -*-
from datetime import datetime
from django.db import models
from django.db.models.signals import post_save
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from orders.models import OrderInfo

import random


class ThirdAppToken(models.Model):
    shop_id = models.BigIntegerField('店铺编码', default=0)
    shop_nick = models.CharField('店铺名称', max_length=100)
    from_app = models.CharField('来源应用,如花集通应用', max_length=20, blank=True)
    created = models.DateTimeField(default=timezone.now)
    access_token = models.CharField('授权access_token', max_length=100, blank=True)
    full_token = models.CharField('授权信息', max_length=2000, blank=True)
    channel_id = models.IntegerField('平台标记,1淘宝，2京东', default=1)
    
    class Meta:
        db_table = 'thirdapp_token'

    def __unicode__(self):
        return self.name   

     
class FailedLog(models.Model):
    FROM_YOUZAN = 1 #有赞
    FROM_TAOBAO = 2 #淘宝
    
    content = models.TextField('失败信息', max_length=30)
    err_from = models.SmallIntegerField('来源', default=0)
    created = models.DateTimeField('创建时间', default=timezone.now)
           
    class Meta:
        db_table = 'thirdapp_failed_log'

    def __unicode__(self):
        return self.content   
    

class ThirdAppDetail(models.Model):
    order_no = models.CharField(max_length=50)
    sku_id = models.CharField(max_length=255,blank=True)
    sku_name = models.CharField(max_length=255,blank=True)
    sku_image = models.CharField(max_length=255,blank=True)
    price = models.CharField(max_length=50,blank=True)
    outer_iid = models.CharField(max_length=20,blank=True)
    nums = models.IntegerField(default=1)

    class Meta:
        db_table = 'thirdapp_detail'
    
    def __unicode__(self):
        return self.sku_name   


class ThirdAppOrderManager(models.Manager):
    
    def get_order_no(self):
        time_string = datetime.now().strftime('%Y%m%d%H%M%S')
        step_int = 0
        while(True):
            step_int += 1
            step_string = '0'*(4-len(str(step_int)))
            order_no = int("%s%s%d" % (time_string,step_string,step_int,))
            try:
                self.get(order_no=order_no)
            except ObjectDoesNotExist:
                return order_no
    
    
    def batch_import(self,*args,**kwargs):
        """
            批量导入
            ---------------
            order_no
            status
            buyer_nick
            buyer_message
            buyer_memo
            total_fee
            payment
            seller_memo
            receiver_name
            receiver_province
            receiver_city
            receiver_town
            receiver_address
            receiver_mobile
            receiver_phone
            channel_id
        """
        deadline = kwargs.get('deadline')
        status = kwargs.get('status')
        orders = kwargs.get('orders')
        seller_id = args[0]
        account_uid = kwargs.get('account_uid')
        account_username = kwargs.get('account_username')
        channel_id = kwargs.get('channel_id',0)
        results = []
        
        from goods.models import SKU
        for o in orders:
            outer_order_no = o.get('outer_order_no')
            province_name = o.get('province_name')
            city_name = o.get('city_name')
            area_name = o.get('area_name')
            username = '%s(网名)' % o.get('username')
            created = o.get('created')
            consignee_name = o.get('consignee_name')
            consignee_phone = o.get('consignee_phone','')
            consignee_address = o.get('consignee_address')
            service_note = o.get('service_note',"") #存放忌讳花信息
            customer_note = o.get('customer_note',"") #客户备注
            card_message = o.get('card_message',"") #忌讳的花
            
            sku_no = o.get('sku_no')
            if not sku_no:
                sku = SKU.objects.query_by_name(o.get('sku_name'))
                sku_no = sku and sku.code or None
                if not sku_no:
                    results.append("%s,"%(o.get('sku_name')))
                    continue
            
            sku_num = o.get('sku_num',1)
            price = int(o.get('price',0))
            shipping_fee = int(o.get('shipping_fee',0))
            discount_price = int(o.get('discount_price',0))
            
            
                
            #查询SKU
            from goods.models import SKU    
            sInstance = SKU.objects.query_by_code(sku_no)
            if not sInstance:
                results.append("%s,"%(sku_no))
                continue
            with transaction.atomic():
                order = ThirdAppOrder()
                
                order.order_no = outer_order_no and outer_order_no or self.get_order_no()
                order.status = 'WAIT_GOODS_SEND'
                order.buyer_nick = username
                order.card_note = card_message
                order.taboo_note = service_note
                order.buyer_memo = customer_note
                order.total_fee = price + shipping_fee
                order.shipping_fee = shipping_fee
                order.discount_price = discount_price
                order.payment = price + shipping_fee - discount_price
                order.seller_memo = service_note
                order.receiver_name = consignee_name
                order.receiver_province = province_name
                order.receiver_city = city_name
                order.receiver_town = area_name
                order.receiver_address = consignee_address
                order.receiver_mobile = consignee_phone
                order.receiver_phone = consignee_phone
                order.channel_id = channel_id
                order.deadline = deadline
                
                order.seller_id = seller_id
                order.date_type = 0
                order.account_uid = account_uid
                order.account_username = account_username
                order.save()
                
                oSku = ThirdAppDetail()
                oSku.order_no = order.order_no
                oSku.sku_id = sInstance.id
                oSku.sku_name = sInstance.name
                oSku.sku_image = sInstance.image
                oSku.outer_iid = sInstance.code
                oSku.price = sInstance.price
                oSku.nums = sku_num       
                oSku.save()
    
        return set(results)

class ThirdAppOrder(models.Model):
    """
        订单信息
        -----------------
        - 订单状态：
            待付款 0
            待发货 1
            已发货 2
            已完成 10
            退款中 20
            已关闭 30
        
        - 来源渠道：
            内部 0
            微信 1
            淘宝 2
            天猫 3
            京东 4
            网店管家 5
        
    """
    
    ORDER_STATUS_UNPAID   = 0
    ORDER_STATUS_SHIPPING = 1
    ORDER_STATUS_SHIPPED  = 2
    ORDER_STATUS_FINISHED = 10
    ORDER_STATUS_REFUND   = 20
    ORDER_STATUS_CLOSED   = 30
    
    ORDER_SOURCE_INTERNAL = 0
    ORDER_SOURCE_WECHAT   = 1
    ORDER_SOURCE_TAOBAO   = 2
    ORDER_SOURCE_TMALL    = 3
    ORDER_SOURCE_JD       = 4
    ORDER_SOURCE_WDGJ     = 5
    ORDER_SOURCE_YOUZAN   = 6
    ORDER_SOURCE_OFFLINE  = 10
    
    ORDER_DATE_TYPE_FULLDAY   = 0
    ORDER_DATE_TYPE_MORNING   = 1
    ORDER_DATE_TYPE_MIDNOON   = 2
    ORDER_DATE_TYPE_AFTERNOON = 3
    ORDER_DATE_TYPE_NIGHT     = 4
    ORDER_DATE_TYPE_TIMING    = 5
    
    source_list = (
        (ORDER_SOURCE_INTERNAL,'内部'),
        (ORDER_SOURCE_WECHAT,'微信'),
        (ORDER_SOURCE_TAOBAO,'淘宝'),
        (ORDER_SOURCE_TMALL,'天猫'),
        (ORDER_SOURCE_JD,'京东'),
        (ORDER_SOURCE_WDGJ,'网店管家'),
        (ORDER_SOURCE_YOUZAN,'有赞'),
        (ORDER_SOURCE_OFFLINE,'线下'),
    )

    AUDIT_STATUS_WAIT = 0
    AUDIT_STATUS_PASS = 1
    AUDIT_STATUS_REFU = 2
    
    STATUS_WAIT_SEND = 1
    order_no = models.CharField(max_length=50,blank=True)
    status = models.CharField(max_length=50)
    buyer_nick = models.CharField(max_length=50)
    buyer_message = models.TextField(blank=True,default='')
    buyer_memo = models.TextField(blank=True,default='')
    taboo_note = models.TextField(blank=True,default='')
    card_note = models.TextField(blank=True)
    total_fee = models.DecimalField(max_digits=10, decimal_places=2,default=0)
    payment = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    seller_memo = models.TextField(blank=True)
    receiver_name = models.CharField(max_length=50,blank=True)
    receiver_province = models.CharField(max_length=200,blank=True)
    receiver_city = models.CharField(max_length=200,blank=True)
    receiver_town = models.CharField(max_length=200,blank=True)
    receiver_address = models.CharField(max_length=200,blank=True)
    receiver_mobile = models.CharField(max_length=30,blank=True)
    receiver_phone = models.CharField(max_length=30,blank=True)
    seller_id = models.BigIntegerField()
    channel_id = models.SmallIntegerField(default=ORDER_SOURCE_INTERNAL)
    audit_status = models.SmallIntegerField(default = AUDIT_STATUS_WAIT)
    add_time = models.DateTimeField(default = timezone.now)
    deadline = models.DateTimeField(default = timezone.now)
    date_type = models.SmallIntegerField(default=ORDER_DATE_TYPE_FULLDAY)
    
    account_uid = models.IntegerField(default = 0)
    account_username = models.CharField(max_length=60,blank=True)
    objects = ThirdAppOrderManager()

    def set_detail(self,**kwargs):
        """
            更新商品
        """
        skus = kwargs.get('skus',[])
        
        ThirdAppDetail.objects.filter(order_no=self.order_no).delete()
        for sku in skus:

            oSku = ThirdAppDetail()
            oSku.order_no = self.order_no
            oSku.sku_id = sku.get('sku_id','')
            oSku.sku_name = sku.get('sku_name','')
            oSku.sku_image = sku.get('sku_image','')
            oSku.outer_iid = sku.get('outer_iid','')
            oSku.price = sku.get('price','')
            oSku.nums = sku.get('nums','')
            oSku.save()
       
        return True

    def get_detail(self):
        order_details = ThirdAppDetail.objects.filter(order_no = self.order_no)
        return order_details

    #审核通过
    def passed(self,ids):
        from .merge import merge_into_sys_order
        
        if ids and isinstance(ids,list):
            for i in ids:
                merge_into_sys_order(i)
        return True
    
    #拒绝通过
    def refused(self,ids):
        if ids and isinstance(ids,list):
            ThirdAppOrder.objects.filter(id__in=ids).update(audit_status=ThirdAppOrder.AUDIT_STATUS_REFU)
            
        return True
    
    
    class Meta:
        db_table = 'thirdapp_order'
    
    def __unicode__(self):
        return self.order_no   
  