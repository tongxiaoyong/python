# -*- coding: utf-8 -*-
from rest_framework import serializers
from .models import ThirdAppToken,ThirdAppOrder,ThirdAppDetail

class ThirdAppTokenSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = ThirdAppToken
        
class ThirdAppOrderSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = ThirdAppOrder

class ThirdAppDetailSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = ThirdAppDetail