# -*- coding: utf-8 -*-
import http.client as httplib
import urllib
import time
import hashlib
import json
import yz
import itertools
import mimetypes
import datetime
'''
定义一些系统变量
'''

SYSTEM_GENERATE_VERSION = "youzan-sdk-python-20161129"

P_APPKEY = "app_key"
P_API = "method"
P_SESSION = "session"
P_ACCESS_TOKEN = "access_token"
P_VERSION = "v"
P_FORMAT = "format"
P_TIMESTAMP = "timestamp"
P_SIGN = "sign"
P_SIGN_METHOD = "sign_method"
P_PARTNER_ID = "partner_id"

P_CODE = 'code'
P_SUB_CODE = 'sub_code'
P_MSG = 'msg'
P_SUB_MSG = 'sub_msg'


N_REST = '/router/rest'

def sign(secret, parameters):
    #===========================================================================
    # '''签名方法
    # @param secret: 签名需要的密钥
    # @param parameters: 支持字典和string两种
    # '''
    #===========================================================================
    # 如果parameters 是字典类的话
    if hasattr(parameters, "items"):
        keys = parameters.keys()
        keys = sorted(keys)
        parameters = "%s%s%s" % (secret,
            str().join('%s%s' % (key, parameters[key]) for key in keys),
            secret)
        m2 = hashlib.md5()
        m2.update(parameters.encode('utf-8'))
        return m2.hexdigest().upper()
    
    return ''

def mixStr(pstr):
#    if(isinstance(pstr, str)):
#        return pstr
#    elif(isinstance(pstr, unicode)):
#        return pstr.encode('utf-8')
#    else:
    return str(pstr)
    
class FileItem(object):
    def __init__(self,filename=None,content=None):
        self.filename = filename
        self.content = content

class MultiPartForm(object):
    """Accumulate the data to be used when posting a form."""

    def __init__(self):
        self.form_fields = []
        self.files = []
        self.boundary = "PYTHON_SDK_BOUNDARY"
        return
    
    def get_content_type(self):
        return 'multipart/form-data; boundary=%s' % self.boundary

    def add_field(self, name, value):
        """Add a simple field to the form data."""
        self.form_fields.append((name, str(value)))
        return

    def add_file(self, fieldname, filename, fileHandle, mimetype=None):
        """Add a file to be uploaded."""
        body = fileHandle.read()
        if mimetype is None:
            mimetype = mimetypes.guess_type(filename)[0] or 'application/octet-stream'
        self.files.append((mixStr(fieldname), mixStr(filename), mixStr(mimetype), mixStr(body)))
        return
    
    def __str__(self):
        """Return a string representing the form data, including attached files."""
        # Build a list of lists, each containing "lines" of the
        # request.  Each part is separated by a boundary string.
        # Once the list is built, return a string where each
        # line is separated by '\r\n'.  
        parts = []
        part_boundary = '--' + self.boundary
        
        # Add the form fields
        parts.extend(
            [ part_boundary,
              'Content-Disposition: form-data; name="%s"' % name,
              'Content-Type: text/plain; charset=UTF-8',
              '',
              value,
            ]
            for name, value in self.form_fields
            )
        
        # Add the files to upload
        parts.extend(
            [ part_boundary,
              'Content-Disposition: file; name="%s"; filename="%s"' % \
                 (field_name, filename),
              'Content-Type: %s' % content_type,
              'Content-Transfer-Encoding: binary',
              '',
              body,
            ]
            for field_name, filename, content_type, body in self.files
            )
        
        # Flatten the list and add closing boundary marker,
        # then return CR+LF separated data
        flattened = list(itertools.chain(*parts))
        flattened.append('--' + self.boundary + '--')
        flattened.append('')
        return '\r\n'.join(flattened)

class TopException(Exception):
    #===========================================================================
    # 业务异常类
    #===========================================================================
    def __init__(self):
        self.errorcode = None
        self.message = None
        self.subcode = None
        self.submsg = None
        self.application_host = None
        self.service_host = None
    
    def __str__(self, *args, **kwargs):
        sb = "errorcode=" + mixStr(self.errorcode) +\
            " message=" + mixStr(self.message) +\
            " subcode=" + mixStr(self.subcode) +\
            " submsg=" + mixStr(self.submsg) +\
            " application_host=" + mixStr(self.application_host) +\
            " service_host=" + mixStr(self.service_host)
        return sb
       
class RequestException(Exception):
    #===========================================================================
    # 请求连接异常类
    #===========================================================================
    pass

class RestApi(object):
    #===========================================================================
    # Rest api的基类
    #===========================================================================
    
    def __init__(self, domain='open.koudaitong.com', port = 80):
        #=======================================================================
        # 初始化基类
        # Args @param domain: 请求的域名或者ip
        #      @param port: 请求的端口
        #=======================================================================
        self.__domain = domain
        self.__port = port
        self.__httpmethod = "POST"
        if(yz.getDefaultAppInfo()):
            self.__app_key = yz.getDefaultAppInfo().appkey
            self.__secret = yz.getDefaultAppInfo().secret
        
    def get_request_header(self):
        return {
                 'Content-type': 'application/x-www-form-urlencoded;charset=UTF-8',
                 "Cache-Control": "no-cache",
                 "Connection": "Keep-Alive",
        }
        
    def set_app_info(self, appinfo):
        #=======================================================================
        # 设置请求的app信息
        # @param appinfo: import top
        #                 appinfo top.appinfo(appkey,secret)
        #=======================================================================
        self.__app_key = appinfo.appkey
        self.__secret = appinfo.secret
        
    def getapiname(self):
        return ""
    
    def getMultipartParas(self):
        return [];

    def getTranslateParas(self):
        return {};
    
    def _check_requst(self):
        pass
    
    def getResponse(self, authrize=None, timeout=30):
        #=======================================================================
        # 获取response结果
        #=======================================================================
        connection = httplib.HTTPConnection(self.__domain, self.__port)
        sys_parameters = {
            "app_id" : self.__app_key,
            "sign_method": "md5",
            "v" : '2.0',
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            P_API: self.getapiname(),
            "format" : "json",
        }
        if authrize is not None:
            sys_parameters[P_SESSION] = authrize
        application_parameter = self.getApplicationParameters()
        parameters = dict(sys_parameters, **application_parameter)
        parameters[P_SIGN] = sign(self.__secret, parameters)
        header = self.get_request_header();
        parameters = urllib.parse.urlencode(parameters)
        connection.request(self.__httpmethod, "/api/entry", parameters, headers=header)
        response = connection.getresponse();
        if response.status is not 200:
            raise RequestException('invalid http status ' + str(response.status) + ',detail body:' + response.read().decode('utf-8'))
        result = response.read()
        try:
            response_str = result.decode('utf-8')
            jsonobj = json.loads(response_str)
        except:
            print("error")
            
        if "error_response" in jsonobj:
            error = TopException()
            if P_CODE in jsonobj["error_response"] :
                error.errorcode = jsonobj["error_response"][P_CODE]
            if P_MSG in jsonobj["error_response"] :
                error.message = jsonobj["error_response"][P_MSG]
            if P_SUB_CODE in jsonobj["error_response"] :
                error.subcode = jsonobj["error_response"][P_SUB_CODE]
            if P_SUB_MSG in jsonobj["error_response"] :
                error.submsg = jsonobj["error_response"][P_SUB_MSG]
            error.application_host = response.getheader("Application-Host", "")
            error.service_host = response.getheader("Location-Host", "")
            raise error
        return jsonobj
    
    
    def getApplicationParameters(self):
        application_parameter = {}
        for key, value in self.__dict__.items():
            if not key.startswith("__") and not key in self.getMultipartParas() and not key.startswith("_RestApi__") and value is not None :
                if(key.startswith("_")):
                    application_parameter[key[1:]] = value
                else:
                    application_parameter[key] = value
        #查询翻译字典来规避一些关键字属性
        translate_parameter = self.getTranslateParas()
        for key, value in application_parameter.items():
            if key in translate_parameter:
                application_parameter[translate_parameter[key]] = application_parameter[key]
                del application_parameter[key]
        return application_parameter
