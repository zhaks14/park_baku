from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CustomerViewSet, check_or_create_customer, verify_code

router = DefaultRouter()
router.register(r'customers', CustomerViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('check-customer/', check_or_create_customer, name='check_customer'),
    path('verify-code/', verify_code, name='verify_code'),
]