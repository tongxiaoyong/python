# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand

from thirdapp import top,sync_incre_order_taobao,days_ago
import os
import json

THIRD_LOG_PATH = os.getcwd()+os.path.sep+'thirdapp'+os.path.sep+'logs'+os.path.sep
    
class Command(BaseCommand):
    def handle(self, *args, **options):
        from thirdapp.models import ThirdAppToken
        
        shops = ThirdAppToken.objects.all()
        for shop in shops:
            if not shop.access_token:
                continue
                
            #最后一次抓单时间点
            time_node = self.get_time_node(shop.shop_id)    
            if not time_node:
                result = sync_incre_order_taobao(top,shop.access_token)
            else:
                result = sync_incre_order_taobao(top,shop.access_token,time_node.get("start_modified"),time_node.get("end_modified"))
            
            if result.get("is_succ",False):
                #更新最后一次抓单时间点
                self.set_time_node(shop.shop_id,result)       


    def get_time_node(self,shop_id):
        try:
            file_name = THIRD_LOG_PATH +"%s.date"%(shop_id)
            if os.path.exists(file_name):
                df = open(file_name)
                c = df.read()
                df.close()
                if c:
                    nodes = json.loads(c)
                    nodes["start_modified"] = nodes.get("end_modified")
                    nodes["end_modified"] = days_ago(0)
                    return nodes
        except:
            return None
        
        return None


    def set_time_node(self,shop_id,node_json):
        try:
            file_name = THIRD_LOG_PATH +"%s.date"%(shop_id)
            if os.path.exists(file_name):
                df = open(file_name,"w")
            else:
                df = open(file_name,"w") 

            df.write(json.dumps(node_json))
            df.close()
        except:
            return False
        return True