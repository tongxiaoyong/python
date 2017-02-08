from rest_framework import routers
from .api import ThirdAppViewSet,ThirdOrderViewSet

router = routers.SimpleRouter()
router.register(r'third-app', ThirdAppViewSet,base_name="third-app")
router.register(r'third-order', ThirdOrderViewSet,base_name="third-order")
