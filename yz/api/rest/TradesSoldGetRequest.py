'''
Created by auto_sdk on 2016.11.03
'''
from yz.api.base import RestApi
class TradesSoldGetRequest(RestApi):

	def getapiname(self):
		return 'kdt.trades.sold.get'
