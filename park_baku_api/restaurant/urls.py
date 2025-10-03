from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CustomerViewSet,check_or_create_customer, verify_code,createOrder,getBalance,orderHistory,sendCode,verifyCode,popularDishes,createOrderWithDishes,check_customer,customer_profile,redeem_bonus,add_bonus,iiko_order_webhook,validate_customer_for_cashier
from .iiko_views import check_iiko_connection, iiko_order_webhook_updated,debug_iiko_connection,test_cashier_integration,iiko_order_webhook_demo

router = DefaultRouter()
router.register(r'customers', CustomerViewSet)


urlpatterns = [
    path('', include(router.urls)),
    path('check-customer/', check_or_create_customer, name='check_customer'),
    path('verify-code-legacy/', verify_code, name='verify_code'),
    path('orders/',createOrder, name="create_order"),
    path('orders/with-dishes/', createOrderWithDishes, name="create_order_with_dishes"),
    path("customers/<str:customer_id>/balance/",getBalance, name="get_balance"),
    path("customers/<str:customer_id>/orders/", orderHistory, name="order_history"),
    path('send-code/',sendCode, name='send-code'),
    path('verify-code/',verifyCode, name='verify-code'),
    path("popular-dishes/", popularDishes, name="popular_dishes"),
    path('check-customer/<str:customer_id>/', check_customer, name='check_customer'),
    path('customer-profile/<str:customer_id>/', customer_profile, name='customer_profile'),
    path('redeem-bonus/<str:customer_id>/', redeem_bonus, name='redeem_bonus'),
    path('add-bonus/<str:customer_id>/', add_bonus, name='add_bonus'),
    path("iiko-webhook/order/", iiko_order_webhook, name="iiko_order_webhook"),
    path("iiko-webhook/order/", iiko_order_webhook_updated, name="iiko_order_webhook"),
    # path("cashier/validate-customer/", validate_customer_for_cashier, name="validate_customer_cashier"),
    # path("iiko-webhook/order/", iiko_order_webhook, name="iiko_order_webhook"),
    # path("cashier/validate-customer/", validate_customer_for_cashier, name="validate_customer_cashier"),
    # path("iiko/check-connection/", check_iiko_connection, name="check_iiko_connection"),
    # path("iiko/debug-connection/", debug_iiko_connection, name="debug_iiko_connection"),
    path("iiko-webhook/order/", iiko_order_webhook_demo, name="iiko_order_webhook"),  # Временно демо-версия
    path("iiko-webhook/real/", iiko_order_webhook, name="iiko_order_webhook_real"),  # Для настоящего iiko
    path("cashier/validate-customer/", validate_customer_for_cashier, name="validate_customer_cashier"),
    path("cashier/test-integration/", test_cashier_integration, name="test_cashier_integration"),
    path("iiko/check-connection/", check_iiko_connection, name="check_iiko_connection"),
    path("iiko/debug-connection/", debug_iiko_connection, name="debug_iiko_connection"),
]