from .models import ThirdAppDetail,ThirdAppOrder
from rest_framework import filters
import django_filters

class ThirdOrderFilter(filters.FilterSet):
    
    min_deadline = django_filters.DateFilter(name='deadline', lookup_type='gte')
    max_deadline = django_filters.DateFilter(name='deadline', lookup_type='lte')
    
    good_name = django_filters.MethodFilter()

    def filter_good_name(self, queryset, value):
        if value:
            detais = ThirdAppDetail.objects.filter(good_name__contains=value)
            order_nos = [u.order_no for d in detais]
            if not order_nos :
                order_nos = []
            return queryset.filter(order_no__in=order_nos)
        return queryset
    
  
    class Meta:
        model = ThirdAppOrder
        fields = ['min_deadline','max_deadline','audit_status','good_name','taboo_note','card_note','order_no']

