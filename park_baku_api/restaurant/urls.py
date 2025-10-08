from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CustomerViewSet, check_or_create_customer, verify_code, getBalance,
    orderHistory, sendCode, verifyCode, popularDishes, createOrderWithDishes,
    check_customer, customer_profile, redeem_bonus, add_bonus,
    validate_customer_for_cashier, send_check
)

router = DefaultRouter()
router.register(r'customers', CustomerViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('check-customer/', check_or_create_customer, name='check_customer'),
    path('check-customer/<str:customer_id>/', check_customer, name='check_customer_by_id'),
    path('customer-profile/<str:customer_id>/', customer_profile, name='customer_profile'),
    path('customers/<str:customer_id>/balance/', getBalance, name='get_balance'),
    path('customers/<str:customer_id>/orders/', orderHistory, name='order_history'),
    path('redeem-bonus/<str:customer_id>/', redeem_bonus, name='redeem_bonus'),
    path('add-bonus/<str:customer_id>/', add_bonus, name='add_bonus'),
    path('send-code/', sendCode, name='send_code'),
    path('verify-code/', verifyCode, name='verify_code'),
    path('verify-code-legacy/', verify_code, name='verify_code_legacy'),
    path('orders/with-dishes/', createOrderWithDishes, name='create_order_with_dishes'),
    path('popular-dishes/', popularDishes, name='popular_dishes'),
    path('cashier/validate-customer/', validate_customer_for_cashier, name='validate_customer_cashier'),
    path('send-check/', send_check, name='send_check'),
]