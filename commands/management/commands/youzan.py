# -*- coding: utf-8 -*-
from django.core.management.base import BaseCommand
import json
from optparse import make_option
import os
from thirdapp.youzan import days_ago
from thirdapp.youzan import sync_incre_order_youzan
from thirdapp.youzan import sync_order_youzan
from thirdapp.youzan import yz

THIRD_LOG_PATH = os.getcwd() + os.path.sep + 'thirdapp' + os.path.sep + 'logs' + os.path.sep
    
class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('datetype', nargs='*')
        parser.add_argument('--datetype',
                            action='store_true',
                            dest='datetype',
                            default=True,
                            help=' DateType instead of get method')
     
    def handle(self, * args, ** options):
        datetype = options.get("datetype")
        if not datetype or datetype[0] == "create":
            print("create")
            self.sync_youzan_by_createtime()
        else:
            print("update")
            self.sync_youzan_by_updatetime()

    def sync_youzan_by_createtime(self):
        shop_id = 'youzan_node_create'      
        #最后一次抓单时间点
        time_node = self.get_time_node(shop_id)    
        if not time_node:
            result = sync_order_youzan(yz)
        else:
            result = sync_order_youzan(yz, None, time_node.get("start_modified"), time_node.get("end_modified"))

        if result.get("is_succ", False):
            #更新最后一次抓单时间点
            self.set_time_node(shop_id, result) 

    def sync_youzan_by_updatetime(self):
        shop_id = 'youzan_node_update'      
        #最后一次抓单时间点
        time_node = self.get_time_node(shop_id)    
        if not time_node:
            result = sync_incre_order_youzan(yz)
        else:
            result = sync_incre_order_youzan(yz, None, time_node.get("start_modified"), time_node.get("end_modified"))

        if result.get("is_succ", False):
            #更新最后一次抓单时间点
            self.set_time_node(shop_id, result) 

    def get_time_node(self, shop_id):
        try:
            file_name = THIRD_LOG_PATH + "%s.date" % (shop_id)
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


    def set_time_node(self, shop_id, node_json):
        try:
            file_name = THIRD_LOG_PATH + "%s.date" % (shop_id)
            if os.path.exists(file_name):
                df = open(file_name, "w")
            else:
                df = open(file_name, "w") 

            df.write(json.dumps(node_json))
            df.close()
        except:
            return False
        return True