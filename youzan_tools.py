# -*- coding: utf-8 -*-
import datetime
import os
import sys
import time
sys.path.append(os.getcwd() + os.path.sep + 'thirdapp')
from cpapi.common import get_huaji_logger
logger = get_huaji_logger()

def register_by_wechat_id(**wargs):
    from base.api import register_user
    from base.models import User
    from django.db.models import Q
    user_id = wargs.get("user_id")
    wechat_id = wargs.get('wechat_id','')
    username = "yz_%s" % (user_id)

    user = User.objects.filter(Q(username=username) | Q(wechat_id=wechat_id))
    if not user:
        serializer = register_user({
                                   "username": username,
                                   "password": "123456",
                                   "wechat_id": wechat_id
                                   });
        return serializer.data.get("id", 1)
    return user[0].id
    

def sync_member():
    from thirdapp.youzan import yz
    objs = yz.api.UsersWeixFollowsGetRequest()
    objs.fields = "weixin_openid,user_id"
    objs.after_fans_id = 0
    objs.page_size = 10
    while True:
        try:
            r = objs.getResponse()
            response = r.get("response")
            users = response.get('users',[])

            for user in users:
                weixin_openid = user.get("weixin_openid")
                user_id = user.get("user_id")
                if weixin_openid and user_id:
                    register_by_wechat_id(user_id=user_id,wechat_id=weixin_openid)
            if not response.get("has_next"):
                break

            objs.after_fans_id = response.get("last_fans_id")

                
        except Exception as err:
#            write_log(err_from=1,content="%s"%(err))
            print(err)   
    
        

