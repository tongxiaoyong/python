# -*- coding: utf-8 -*-
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import list_route,detail_route
from rest_framework import filters
from cpapi.common.pagination import StandardResultsSetPagination
from rest_framework import generics, mixins
from .serializers import ThirdAppTokenSerializer,ThirdAppOrderSerializer,ThirdAppDetailSerializer
from .custfilter import ThirdOrderFilter    
from .models import ThirdAppOrder,ThirdAppDetail,ThirdAppToken
from base.models import Region, User
import django_filters

from cpapi.common import get_huaji_logger
logger = get_huaji_logger()

from thirdapp import top,sync_order_taobao,days_ago


def create_thirdapp_order(*args,**kwargs):
    """
        创建订单公共函数
    """
    data = kwargs.get('data')
    skus = kwargs.get('skus')
    
    serializer = ThirdAppOrderSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    
    orderInfo = serializer.save()
    orderInfo.set_detail(skus=skus)
    
    return serializer.data

class ThirdAppViewSet(mixins.CreateModelMixin,mixins.UpdateModelMixin,
                   mixins.DestroyModelMixin,
                   mixins.ListModelMixin,viewsets.GenericViewSet):
    """
    第三方应用
    """
    serializer_class = ThirdAppTokenSerializer
    queryset = ThirdAppToken.objects.all()
    
    filter_backends = (filters.DjangoFilterBackend,filters.OrderingFilter,)
    pagination_class = StandardResultsSetPagination
    
    @detail_route(methods=['GET',])
    def sync_order(self,request,pk=None,*args,**kwargs):
        """
            同步渠道订单接口
            ---
            parameters_strategy: replace
            parameters:
                - name: days
                  description: 近几天
                  required: true
                  type: integer
                  paramType: form  
        """
        
        days = request.data.get("days",3)
        if not pk:
            return Response({'msg':'同步的花店ID必须传'},status=status.HTTP_400_BAD_REQUEST)
        
        try:
            thirdshop = ThirdAppToken.objects.get(id=pk)
        except ThirdAppToken.DoesNotExist:
            return Response({'msg':'找不到花店'},status=status.HTTP_400_BAD_REQUEST)
        
        start_modified = days_ago(int(days))
        end_modified = days_ago(0)
        sync_order_taobao(top, thirdshop.access_token,start_modified,end_modified)
        return Response({'msg':'success'})
    
    
class ThirdOrderViewSet(mixins.CreateModelMixin,mixins.UpdateModelMixin,
                   mixins.DestroyModelMixin,
                   mixins.ListModelMixin,viewsets.GenericViewSet):
    """
    第三方应用
    """
    serializer_class = ThirdAppOrderSerializer
    queryset = ThirdAppOrder.objects.all()
    
    filter_backends = (filters.DjangoFilterBackend,filters.OrderingFilter,filters.SearchFilter,)
    pagination_class = StandardResultsSetPagination
    filter_class = ThirdOrderFilter
    ordering_fields = ('id','add_time',)
    search_fields = ('^receiver_name','^receiver_address','^receiver_mobile','^receiver_phone','seller_memo')
    
    def _details(self,order_nos):
        details = {}
        if order_nos:
            result = ThirdAppDetail.objects.filter(order_no__in=order_nos)
            data = ThirdAppDetailSerializer(result,many=True).data
            for r in data:
                try:
                    details[r.get("order_no")].append(r)
                except:
                    details[r.get("order_no")] = []
                    details[r.get("order_no")].append(r)
        return details
    
    def _extend_details(self,data):
        order_nos = [d['order_no'] for d in data]
        extend_details = self._details(order_nos)
        
        #待付款、服务中、已完成、交易取消
        for d in data:    
            extend_data = extend_details.get(d['order_no'])
            if extend_data:
                d['sku_list'] = extend_data
            else:
                d['sku_list'] = []
        
        return data
            
    def list(self,request):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            data = self._extend_details(serializer.data)
            return self.get_paginated_response(data)

        serializer = self.get_serializer(queryset, many=True)
        data = self._extend_details(serializer.data)
        return Response(data)
        
    def create(self,request):
        """
            第三方订单创建接口
            ---
        """   
        
        skus_json = request.data.get('skus',"[]")
        
        if not skus_json:
            return Response({'msg':'没有选择下单的SKU'},status=status.HTTP_400_BAD_REQUEST)
        
        skus = json.loads(skus_json)
        
        with transaction.atomic():
            try:
                data = request.data.copy()
                
                serializer_data = create_thirdapp_order(data=data,skus=skus)
                
            except ValueError as e:
                return Response({'msg':str(e)},status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                return Response({'msg':str(e)},status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer_data, status=status.HTTP_201_CREATED)
    

    @list_route(methods=['POST',])
    def passed(self,request,*args,**kwargs):
        """
            订单审核接口
            ---
            parameters_strategy: replace
            parameters:
                - name: ids
                  description: 订单表ID值，多个用逗号分
                  required: true
                  type: integer
                  paramType: form  
        """
        ids = request.data.get("ids",None)
        if not ids:
            return Response({'msg':'列表ids必须传'},status=status.HTTP_400_BAD_REQUEST)
        
        thirdorder = ThirdAppOrder()
        thirdorder.passed(ids.split(','))
        return Response({'msg':'success'})

    @list_route(methods=['POST',])    
    def set_deadline(self,request):
        """
            设置配送时间
            ---
            parameters_strategy: replace
            parameters:
                - name: ids
                  description: 订单表ID值，多个用逗号分
                  required: true
                  type: integer
                  paramType: form  
                - name: deadline
                  description: 配送时间
                  required: true
                  type: integer
                  paramType: form  
        """
        ids = request.data.get("ids")
        if not ids:
            return Response({'msg':'IDS必须传'},status=status.HTTP_400_BAD_REQUEST)
        
        deadline = request.data.get("deadline")
        ThirdAppOrder.objects.filter(id__in=ids.split(',')).update(deadline=deadline)
        return Response({'msg':'success'})
        

    @list_route(methods=['POST',])
    def refused(self,request,*args,**kwargs):
        """
            订单审核接口
            ---
            parameters_strategy: replace
            parameters:
                - name: ids
                  description: 订单表ID值，多个用逗号分
                  required: true
                  type: integer
                  paramType: form  
        """
        
        ids = request.data.get("ids",None)
        if not ids:
            return Response({'msg':'列表ids必须传'},status=status.HTTP_400_BAD_REQUEST)
        
        thirdorder = ThirdAppOrder()
        thirdorder.refused(ids.split(','))
        return Response({'msg':'success'})
    
    @list_route(methods=['POST',])
    def batch(self,request,*args,**kwargs):
        """
            批量导入订单
            ---
            parameters_strategy: replace
            parameters:
                - name: deadline
                  description: 首次配送日期
                  required: true
                  type: string
                  paramType: form
                - name: account_uid
                  description: 付款用户的uid
                  required: false
                  type: integer
                  paramType: form
                - name: orders
                  description: 订单列表json格式
                  required: false
                  type: string
                  paramType: form
                - name: channel_id
                  description: 订单来源
                  required: false
                  type: string
                  paramType: form
        """
        orders = request.data.get('orders',None)
        
        if not orders:
            return Response({'msg':'没有提交订单数据'},status=status.HTTP_400_BAD_REQUEST)
        
        deadline = request.data.get('deadline',None)
        if not deadline:
            return Response({'msg':'没有提交首次配送的日期'},status=status.HTTP_400_BAD_REQUEST)
        
        import json
        orders = json.loads(orders)
        
        account_uid = request.data.get('account_uid',None)
        channel_id = request.data.get('channel_id',0)
        account_username = ''
        if account_uid:
            try:
                account = User.objects.get(id=account_uid)
                account_username = account.username
            except User.DoesNotExist:
                pass
        try:
            user_id = request.user.id
            results = ThirdAppOrder.objects.batch_import(user_id,orders=orders,deadline=deadline,account_uid=account_uid,account_username=account_username,status=ThirdAppOrder.ORDER_STATUS_UNPAID,channel_id=channel_id)  
        except ValueError as e:
            return Response({'msg':str(e)},status=status.HTTP_400_BAD_REQUEST)
        
        return Response({'results':results})