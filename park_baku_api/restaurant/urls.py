# urls.py - ЧИСТАЯ ВЕРСИЯ БЕЗ ДУБЛИКАТОВ

from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Основные views
from .views import (
    CustomerViewSet,
    check_or_create_customer,
    verify_code,
    createOrder,
    getBalance,
    orderHistory,
    sendCode,
    verifyCode,
    popularDishes,
    createOrderWithDishes,
    check_customer,
    customer_profile,
    redeem_bonus,
    add_bonus,
    validate_customer_for_cashier
)

# iiko views (основной файл с вебхуками и тестами)
from .iiko_views import (
    check_iiko_connection,
    iiko_order_webhook_updated,
    debug_iiko_connection,
    test_cashier_integration,
    iiko_order_webhook_demo,
    # ✅ ЭТИ 3 ФУНКЦИИ ДОЛЖНЫ БЫТЬ В iiko_views.py
    get_iiko_active_orders,      # Получение активных заказов
    get_iiko_order_details,       # Детали заказа
    test_iiko_connection_full,     # Полный тест
    get_closed_orders_olap,
    get_all_orders_combined,
    sync_closed_orders_to_db
)

# Cashier views (интерфейс для кассиров)
# from .cashier_views import (
#     cashier_interface,
#     cashier_add_order,
#     cashier_check_customer
# )

# ✅ ОПЦИОНАЛЬНО: если создали отдельные файлы для debug
# Раскомментируйте если создали эти файлы:
# from .debug_views import debug_iiko_orders_request, check_token_validity
# from .simple_iiko_test import simple_iiko_test

router = DefaultRouter()
router.register(r'customers', CustomerViewSet)

urlpatterns = [
    path('', include(router.urls)),
    
    # ============================================
    # КЛИЕНТЫ (Customers)
    # ============================================
    path('check-customer/', check_or_create_customer, name='check_customer'),
    path('check-customer/<str:customer_id>/', check_customer, name='check_customer_by_id'),
    path('customer-profile/<str:customer_id>/', customer_profile, name='customer_profile'),
    path('customers/<str:customer_id>/balance/', getBalance, name='get_balance'),
    path('customers/<str:customer_id>/orders/', orderHistory, name='order_history'),
    path('redeem-bonus/<str:customer_id>/', redeem_bonus, name='redeem_bonus'),
    path('add-bonus/<str:customer_id>/', add_bonus, name='add_bonus'),
    
    # ============================================
    # АУТЕНТИФИКАЦИЯ
    # ============================================
    path('send-code/', sendCode, name='send_code'),
    path('verify-code/', verifyCode, name='verify_code'),
    path('verify-code-legacy/', verify_code, name='verify_code_legacy'),
    
    # ============================================
    # ЗАКАЗЫ (Orders)
    # ============================================
    path('orders/', createOrder, name='create_order'),
    path('orders/with-dishes/', createOrderWithDishes, name='create_order_with_dishes'),
    path('popular-dishes/', popularDishes, name='popular_dishes'),
    
    # ============================================
    # iiko API - ПОЛУЧЕНИЕ ЗАКАЗОВ (основное)
    # ============================================
    
    # ✅ ГЛАВНЫЙ ENDPOINT: Получить активные заказы доставки с кассы
    path('iiko/orders/active/', get_iiko_active_orders, name='iiko_active_orders'),
    
    # ✅ НОВОЕ: Получить закрытые заказы (включая столики) через OLAP
    path('iiko/orders/closed/', get_closed_orders_olap, name='iiko_closed_orders'),
    
    # ✅ НОВОЕ: Получить ВСЕ заказы (активные доставки + закрытые + локальные)
    path('iiko/orders/all/', get_all_orders_combined, name='iiko_all_orders'),
    
    # ✅ НОВОЕ: Синхронизировать закрытые заказы в БД
    path('iiko/sync-closed-orders/', sync_closed_orders_to_db, name='sync_closed_orders'),
    
    # Получить детали конкретного заказа
    path('iiko/orders/<str:order_id>/', get_iiko_order_details, name='iiko_order_details'),
    
    # ============================================
    # iiko API - ТЕСТЫ И ДИАГНОСТИКА
    # ============================================
    
    # Полный тест соединения (проверяет всё: токен, организации, терминалы, заказы)
    path('iiko/test-connection/', test_iiko_connection_full, name='test_iiko_full'),
    
    # Простая проверка соединения
    path('iiko/check-connection/', check_iiko_connection, name='check_iiko_connection'),
    
    # Детальная диагностика
    path('iiko/debug-connection/', debug_iiko_connection, name='debug_iiko_debug'),
    
    # ✅ Раскомментируйте если создали debug_views.py:
    # path('iiko/debug-orders/', debug_iiko_orders_request, name='debug_orders'),
    # path('iiko/check-token/', check_token_validity, name='check_token'),
    
    # ✅ Раскомментируйте если создали simple_iiko_test.py:
    # path('iiko/simple-test/', simple_iiko_test, name='simple_iiko_test'),
    
    # ============================================
    # iiko WEBHOOKS
    # ============================================
    
    # Демо-вебхук (для тестирования без настоящего iiko)
    path('iiko-webhook/order/', iiko_order_webhook_demo, name='iiko_order_webhook_demo'),
    
    # Настоящий вебхук (для production)
    path('iiko-webhook/real/', iiko_order_webhook_updated, name='iiko_order_webhook_real'),
    
    # ============================================
    # КАССИР (Cashier)
    # ============================================
    
    # Веб-интерфейс для кассира (откройте в браузере)
    # path('cashier/', cashier_interface, name='cashier_interface'),
    
    # API для добавления заказа с кассы
    # path('cashier/add-order/', cashier_add_order, name='cashier_add_order'),
    
    # Быстрая проверка клиента
    # path('cashier/check/<str:customer_id>/', cashier_check_customer, name='cashier_check_customer'),
    
    # Валидация клиента для кассира (старый endpoint)
    path('cashier/validate-customer/', validate_customer_for_cashier, name='validate_customer_cashier'),
    
    # Тест интеграции кассира
    path('cashier/test-integration/', test_cashier_integration, name='test_cashier_integration'),
]


# ============================================
# 📚 ДОКУМЕНТАЦИЯ ПО ИСПОЛЬЗОВАНИЮ
# ============================================
"""
✅ ОСНОВНЫЕ ENDPOINTS ДЛЯ РАБОТЫ С ЗАКАЗАМИ:

1. Получить все активные заказы (за последние 24 часа):
   GET http://localhost:8000/api/iiko/orders/active/
   
2. Получить заказы за последние 12 часов:
   GET http://localhost:8000/api/iiko/orders/active/?hours=12
   
3. Получить заказы в статусе "В пути":
   GET http://localhost:8000/api/iiko/orders/active/?status=OnWay
   
4. Получить детали конкретного заказа:
   GET http://localhost:8000/api/iiko/orders/{ORDER_ID}/

---

✅ ТЕСТИРОВАНИЕ И ДИАГНОСТИКА:

5. Полный тест соединения с iiko (рекомендуется запустить первым):
   GET http://localhost:8000/api/iiko/test-connection/
   
   Проверяет:
   - Получение токена
   - Получение организаций
   - Получение терминалов
   - Получение заказов

6. Простая проверка соединения:
   GET http://localhost:8000/api/iiko/check-connection/

7. Детальная диагностика:
   GET http://localhost:8000/api/iiko/debug-connection/

---

✅ РАБОТА С КЛИЕНТАМИ:

8. Проверить/создать клиента по телефону:
   POST http://localhost:8000/api/check-customer/
   Body: {"phone": "501234567"}

9. Получить баланс клиента:
   GET http://localhost:8000/api/customers/C1234/balance/

10. История заказов клиента:
    GET http://localhost:8000/api/customers/C1234/orders/

11. Валидация клиента для кассира:
    POST http://localhost:8000/api/cashier/validate-customer/
    Body: {"customer_id": "C1234"}

---

✅ WEBHOOKS:

12. Демо-вебхук (для тестирования):
    POST http://localhost:8000/api/iiko-webhook/order/
    Body: {"customer_id": "C1234", "dishes": [...]}

13. Настоящий вебхук от iiko (настроить в iiko Office):
    POST http://localhost:8000/api/iiko-webhook/real/
    Headers: X-Signature: {hash}

---

🔧 ПРИМЕРЫ ИСПОЛЬЗОВАНИЯ В КОДЕ:

# Python/Django:
from myapp.iiko_service import get_active_orders

# Получить заказы за последние 12 часов
orders = get_active_orders(hours=12)
for order in orders:
    print(f"Order #{order['number']}: {order['sum']} тенге")

# JavaScript/Frontend:
fetch('http://localhost:8000/api/iiko/orders/active/')
  .then(res => res.json())
  .then(data => {
    console.log(`Found ${data.count} orders`);
    data.orders.forEach(order => {
      console.log(`Order #${order.number}: ${order.sum}`);
    });
  });
"""