# iiko_views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
import json
import logging
import hashlib
import json
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from .models import Customer, Order
from decimal import Decimal
from .models import Customer, Order
from .iiko_service import IikoCloudAPI, IikoWebhookProcessor

IIKO_API_LOGIN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJBcGlMb2dpbklkIjoiNGZmMmZhN2QtMjUzNC00MTJjLWI1MWUtYWFkMTNiZmViZGY2IiwibmJmIjoxNzU5NDk0NjQ0LCJleHAiOjE3NTk0OTgyNDQsImlhdCI6MTc1OTQ5NDY0NCwiaXNzIjoiaWlrbyIsImF1ZCI6ImNsaWVudHMifQ.udD933wOKIKv1pgcMOc1WLiae_xNWic5oSAR3MPvbI0"
IIKO_ORG_ID="a2486bd5-0ee4-4d7c-81a0-106ddc0fddf1"
IIKO_WEBHOOK_SECRET="c7b7c1a0-4e12-4b93-bf82-19a5d4c5c2fa"

logger = logging.getLogger(__name__)

# Инициализация iiko API (добавьте API ключ в settings.py)
iiko_api = IikoCloudAPI(api_key=IIKO_API_LOGIN)


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def iiko_order_webhook(request):
    """
    Вебхук для обработки новых заказов из iiko
    Когда на кассе создается заказ с ID клиента, этот вебхук обновляет баланс
    """
    try:
        # Проверяем подпись, если настроен секретный ключ
        if hasattr(settings, 'IIKO_WEBHOOK_SECRET'):
            signature = request.headers.get('X-Signature', '')
            if not IikoWebhookProcessor.validate_webhook_signature(
                request.body, 
                signature, 
                settings.IIKO_WEBHOOK_SECRET
            ):
                logger.warning("Invalid webhook signature")
                return Response({'error': 'Invalid signature'}, status=status.HTTP_403_FORBIDDEN)
        
        # Парсим данные вебхука
        data = request.data
        logger.info(f"Received iiko webhook: {json.dumps(data, indent=2)}")
        
        # Обрабатываем данные заказа
        order_info = IikoWebhookProcessor.process_order_webhook(data)
        
        # Ищем клиента по customer_id или телефону
        customer = None
        
        # Сначала пробуем найти по customer_id (который может быть передан с кассы)
        if order_info.get('customer_id'):
            # customer_id от iiko может быть как наш customer_id, так и их ID
            # Сначала ищем по нашему customer_id
            customer = Customer.objects.filter(
                customer_id=order_info['customer_id']
            ).first()
            
            # Если не нашли, ищем по iiko_customer_id (если добавите это поле)
            if not customer:
                customer = Customer.objects.filter(
                    iiko_customer_id=order_info['customer_id']
                ).first()
        
        # Если не нашли по ID, ищем по телефону
        if not customer and order_info.get('customer_phone'):
            phone = order_info['customer_phone'].replace('+994', '').strip()
            customer = Customer.objects.filter(phone=phone).first()
        
        # Если клиент найден, создаем заказ
        if customer:
            with transaction.atomic():
                # Создаем заказ
                order = Order.objects.create(
                    customer=customer,
                    amount=order_info['amount'],
                    notes=f"iiko Order ID: {order_info['order_id']}"
                )
                
                # Модель автоматически обновит total_spent и orders_count
                
                logger.info(f"Order created for customer {customer.customer_id}: {order_info['amount']}")
                
                return Response({
                    'success': True,
                    'customer_id': customer.customer_id,
                    'order_id': order.id,
                    'new_total': str(customer.total_spent)
                })
        else:
            logger.warning(f"Customer not found for order: {order_info}")
            return Response({
                'success': False,
                'error': 'Customer not found'
            }, status=status.HTTP_404_NOT_FOUND)
            
    except Exception as e:
        logger.error(f"Error processing iiko webhook: {e}", exc_info=True)
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def iiko_payment_webhook(request):
    """
    Вебхук для обработки платежей из iiko
    """
    try:
        data = request.data
        logger.info(f"Received payment webhook: {json.dumps(data, indent=2)}")
        
        payment_info = IikoWebhookProcessor.process_payment_webhook(data)
        
        # Ищем клиента
        customer = Customer.objects.filter(
            customer_id=payment_info.get('customer_id')
        ).first()
        
        if customer and payment_info['is_processed']:
            # Создаем заказ на основе платежа
            with transaction.atomic():
                order = Order.objects.create(
                    customer=customer,
                    amount=payment_info['amount'],
                    notes=f"Payment ID: {payment_info['payment_id']}"
                )
                
                return Response({
                    'success': True,
                    'payment_processed': True,
                    'customer_id': customer.customer_id,
                    'new_total': str(customer.total_spent)
                })
        
        return Response({'success': True, 'payment_processed': False})
        
    except Exception as e:
        logger.error(f"Error processing payment webhook: {e}", exc_info=True)
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def sync_customer_with_iiko(request):
    """
    Синхронизация клиента с iiko
    Создает клиента в iiko и связывает ID
    """
    customer_id = request.data.get('customer_id')
    
    if not customer_id:
        return Response({'error': 'customer_id required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        customer = Customer.objects.get(customer_id=customer_id)
        
        # Создаем/обновляем клиента в iiko
        result = iiko_api.create_or_update_customer(
            phone=customer.phone,
            name=customer.user.get_full_name() or customer.user.username,
            customer_id=customer.customer_id
        )
        
        # Сохраняем iiko ID если его вернули
        if 'id' in result:
            # Добавьте поле iiko_customer_id в модель Customer
            customer.iiko_customer_id = result['id']
            customer.save()
        
        return Response({
            'success': True,
            'customer_id': customer.customer_id,
            'iiko_id': result.get('id'),
            'message': 'Customer synced with iiko'
        })
        
    except Customer.DoesNotExist:
        return Response({'error': 'Customer not found'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error syncing customer with iiko: {e}", exc_info=True)
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def debug_iiko_connection(request):
    """
    Детальная диагностика подключения к iiko
    """
    debug_info = {
        'api_login_exists': bool(IIKO_API_LOGIN),
        'api_login_length': len(IIKO_API_LOGIN) if IIKO_API_LOGIN else 0,
        'api_login_sample': IIKO_API_LOGIN[:20] + '...' if IIKO_API_LOGIN else None,
        'base_url': 'https://api-ru.iiko.services/api/1'
    }
    
    # Пробуем получить токен
    try:
        # Тестовый запрос напрямую
        url = "https://api-ru.iiko.services/api/1/access_token"
        test_data = {"apiLogin": IIKO_API_LOGIN}
        test_headers = {"Content-Type": "application/json"}
        
        import requests
        test_response = requests.post(url, json=test_data, headers=test_headers, timeout=10)
        
        debug_info.update({
            'test_request_url': url,
            'test_request_data': test_data,
            'test_response_status': test_response.status_code,
            'test_response_headers': dict(test_response.headers),
            'test_response_body': test_response.text[:500] if test_response.text else 'Empty response'
        })
        
        # Если получили токен, пробуем получить организации
        if test_response.status_code == 200:
            result = test_response.json()
            token = result.get('token')
            if token:
                debug_info['token_obtained'] = True
                debug_info['token_sample'] = token[:20] + '...'
                
    except Exception as e:
        debug_info['test_error'] = str(e)
    
    return Response(debug_info)

# @api_view(['GET'])
# def check_iiko_connection(request):
#     """
#     Проверка подключения к iiko API
#     """
#     try:
#         # Получаем токен
#         token = iiko_api.get_access_token()
        
#         # Получаем организации
#         organizations = iiko_api.get_organizations()
        
#         return Response({
#             'success': True,
#             'connected': True,
#             'token_obtained': bool(token),
#             'organizations_count': len(organizations),
#             'organizations': [
#                 {
#                     'id': org['id'],
#                     'name': org.get('name', 'Unknown')
#                 } for org in organizations
#             ]
#         })
        
#     except Exception as e:
#         logger.error(f"iiko connection check failed: {e}")
#         return Response({
#             'success': False,
#             'connected': False,
#             'error': str(e)
#         }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def validate_signature(request):
    """Проверка подписи вебхука от iiko"""
    signature = request.headers.get("x-iiko-signature")
    if not signature:
        return False

    secret = IIKO_WEBHOOK_SECRET
    if not secret:
        return False

    raw_body = request.body.decode("utf-8")
    expected_signature = hashlib.sha256(f"{raw_body}{secret}".encode()).hexdigest()
    return expected_signature == signature

@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def iiko_order_webhook(request):
    """
    Основной вебхук для iiko WebKassa
    """
    logger.info("Received iiko webhook request")
    
    # Проверяем подпись
    if not validate_signature(request):
        logger.warning("Invalid webhook signature")
        return Response({"error": "Invalid signature"}, status=status.HTTP_403_FORBIDDEN)

    data = request.data
    logger.info(f"Webhook data: {json.dumps(data, indent=2)}")
    
    try:
        # Извлекаем данные заказа из iiko
        order_id = data.get("orderId")
        organization_id = data.get("organizationId")
        total_sum = Decimal(str(data.get("sum", "0")))
        created_at = data.get("createdAt")
        items = data.get("items", [])
        
        # Ищем customer_id в данных iiko
        customer_id = None
        
        # Вариант 1: в объекте customer
        customer_data = data.get("customer", {})
        if customer_data:
            customer_id = customer_data.get("id")
            if not customer_id:
                customer_id = customer_data.get("code")
        
        # Вариант 2: в комментарии
        if not customer_id:
            comment = data.get("comment", "")
            import re
            match = re.search(r'[Cc]\d{4}', comment)
            if match:
                customer_id = match.group(0).upper()
        
        # Вариант 3: в номере телефона
        if not customer_id and customer_data.get("phone"):
            phone = customer_data["phone"].replace('+', '').replace(' ', '')
            try:
                customer = Customer.objects.filter(phone__contains=phone[-9:]).first()
                if customer:
                    customer_id = customer.customer_id
            except:
                pass

        if not customer_id:
            logger.warning(f"No customer ID found in iiko webhook data")
            return Response({
                "success": False,
                "error": "Customer ID not found in order data"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Ищем клиента в нашей системе
        try:
            customer = Customer.objects.get(customer_id=customer_id)
            logger.info(f"Found customer: {customer.customer_id}")
        except Customer.DoesNotExist:
            logger.warning(f"Customer not found: {customer_id}")
            return Response({
                "success": False, 
                "error": f"Customer {customer_id} not found"
            }, status=status.HTTP_404_NOT_FOUND)

        # Создаем заказы для каждого блюда
        created_orders = []
        total_amount = Decimal("0")
        
        for item in items:
            name = item.get("name", "Unknown dish")
            qty = int(item.get("amount", 1))
            item_sum = Decimal(str(item.get("sum", 0)))
            
            # Рассчитываем цену за единицу
            price = item_sum / qty if qty > 0 else item_sum
            
            # Создаем заказ
            order = Order.objects.create(
                customer=customer,
                external_id=order_id,
                iiko_organization_id=organization_id,
                dish_name=name,
                quantity=qty,
                amount=item_sum,
                notes=f"iiko Order: {order_id}",
                is_synced=True
            )
            
            created_orders.append({
                "dish_name": name,
                "quantity": qty,
                "amount": float(order.amount),
                "bonus_earned": float(order.calculate_bonus())
            })
            
            total_amount += order.amount
        
        # Обновляем данные клиента
        customer.refresh_from_db()
        
        logger.info(f"Successfully created {len(created_orders)} orders for customer {customer_id}")
        
        return Response({
            "success": True,
            "order_id": order_id,
            "customer_id": customer.customer_id,
            "customer_phone": customer.phone,
            "total_amount": float(total_amount),
            "bonus_balance": float(customer.bonus_balance),
            "total_spent": float(customer.total_spent),
            "orders_count": customer.orders_count,
            "current_discount": customer.get_discount_percentage(),
            "orders": created_orders
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"Error processing iiko webhook: {str(e)}", exc_info=True)
        return Response({
            "success": False,
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
def check_iiko_connection(request):
    """
    Проверка подключения к iiko API
    """
    try:
        # Получаем токен
        token = iiko_api.get_access_token()
        
        # Получаем организации
        organizations = iiko_api.get_organizations()
        
        return Response({
            'success': True,
            'connected': True,
            'token_obtained': bool(token),
            'organizations_count': len(organizations),
            'organizations': [
                {
                    'id': org['id'],
                    'name': org.get('name', 'Unknown')
                } for org in organizations
            ]
        })
        
    except Exception as e:
        logger.error(f"iiko connection check failed: {e}", exc_info=True)
        return Response({
            'success': False,
            'connected': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def process_cash_register_input(request):
    """
    Обработка ввода ID клиента на кассе
    Этот endpoint может быть вызван из iiko плагина или кассового приложения
    """
    customer_id = request.data.get('customer_id')
    order_amount = request.data.get('amount', 0)
    order_id = request.data.get('order_id')
    
    if not customer_id:
        return Response({'error': 'customer_id required'}, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Ищем клиента по customer_id
        customer = Customer.objects.get(customer_id=customer_id)
        
        # Если передана сумма, создаем заказ
        if order_amount > 0:
            with transaction.atomic():
                order = Order.objects.create(
                    customer=customer,
                    amount=order_amount,
                    notes=f"Cash Register Order: {order_id or 'N/A'}"
                )
                
                # Рассчитываем скидку
                discount = 0
                if customer.total_spent >= 100:
                    discount = 10
                elif customer.total_spent >= 50:
                    discount = 5
                
                return Response({
                    'success': True,
                    'customer': {
                        'id': customer.customer_id,
                        'name': customer.user.username,
                        'phone': customer.phone,
                        'total_spent': str(customer.total_spent),
                        'orders_count': customer.orders_count,
                        'discount_percentage': discount
                    },
                    'order': {
                        'id': order.id,
                        'amount': str(order.amount)
                    }
                })
        else:
            # Просто возвращаем информацию о клиенте
            discount = 0
            if customer.total_spent >= 100:
                discount = 10
            elif customer.total_spent >= 50:
                discount = 5
                
            return Response({
                'success': True,
                'customer': {
                    'id': customer.customer_id,
                    'name': customer.user.username,
                    'phone': customer.phone,
                    'total_spent': str(customer.total_spent),
                    'orders_count': customer.orders_count,
                    'discount_percentage': discount
                }
            })
            
    except Customer.DoesNotExist:
        return Response({
            'success': False,
            'error': 'Customer not found'
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error processing cash register input: {e}", exc_info=True)
        return Response({
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

def validate_signature(request):
    """Проверка подписи вебхука от iiko"""
    signature = request.headers.get("x-iiko-signature")
    if not signature:
        return False

    secret = getattr(settings, "IIKO_WEBHOOK_SECRET", None)
    if not secret:
        return False

    raw_body = request.body.decode("utf-8")
    expected_signature = hashlib.sha256(f"{raw_body}{secret}".encode()).hexdigest()
    return expected_signature == signature


@csrf_exempt
@api_view(["POST"])
def iiko_order_webhook(request):
    """
    Вебхук от iiko WebKassa
    Пример payload:
    {
        "orderId": "b95f1a0b-9c67-48f1-84c0-9d14c1234567",
        "organizationId": "a2486bd5-0ee4-4d7c-81a0-106ddc0fddf1",
        "customer": {
            "id": "C1234",
            "phone": "+77770001122"
        },
        "items": [
            {"name": "Пицца Маргарита", "amount": 2, "sum": 3000},
            {"name": "Кола", "amount": 1, "sum": 500}
        ],
        "sum": 3500,
        "createdAt": "2025-10-03T12:30:00Z"
    }
    """

    # Проверяем подпись
    if not validate_signature(request):
        return Response({"error": "Invalid signature"}, status=status.HTTP_403_FORBIDDEN)

    data = request.data
    customer_data = data.get("customer", {})
    customer_id = customer_data.get("id")

    if not customer_id:
        return Response({"error": "Customer ID required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        customer = Customer.objects.get(customer_id=customer_id)
    except Customer.DoesNotExist:
        return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)

    order_id = data.get("orderId")
    total_sum = Decimal(str(data.get("sum", "0")))
    created_at = data.get("createdAt")
    items = data.get("items", [])

    created_orders = []
    for item in items:
        name = item.get("name", "Unknown")
        qty = int(item.get("amount", 1))
        price = Decimal(str(item.get("sum", 0))) / qty if qty else 0

        order = Order.objects.create(
            customer=customer,
            external_id=order_id,
            dish_name=name,
            quantity=qty,
            amount=Decimal(str(price)) * qty,
            created_at=created_at,
        )
        created_orders.append({
            "dish_name": name,
            "quantity": qty,
            "amount": float(order.amount)
        })

    return Response({
        "success": True,
        "order_id": order_id,
        "customer_id": customer.customer_id,
        "total_amount": float(total_sum),
        "bonus_balance": float(customer.bonus_balance),
        "orders": created_orders
    }, status=status.HTTP_201_CREATED)

@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def iiko_order_webhook_updated(request):
    """
    Улучшенный вебхук для iiko WebKassa
    Обрабатывает сценарий: кассир спрашивает "Есть бонусное приложение?", 
    клиент диктует ID (C1234), заказ привязывается к клиенту
    """
    logger.info("Received iiko webhook request")
    
    # Проверяем подпись
    if not validate_signature(request):
        logger.warning("Invalid webhook signature")
        return Response({"error": "Invalid signature"}, status=status.HTTP_403_FORBIDDEN)

    data = request.data
    logger.info(f"Webhook data: {json.dumps(data, indent=2)}")
    
    try:
        # Извлекаем данные заказа из iiko
        order_id = data.get("orderId")
        organization_id = data.get("organizationId")
        total_sum = Decimal(str(data.get("sum", "0")))
        created_at = data.get("createdAt")
        items = data.get("items", [])
        
        # Ищем customer_id в данных iiko
        # iiko может передавать его в разных местах, проверяем все варианты
        customer_id = None
        
        # Вариант 1: в объекте customer
        customer_data = data.get("customer", {})
        if customer_data:
            customer_id = customer_data.get("id")
            if not customer_id:
                customer_id = customer_data.get("code")  # иногда в code
        
        # Вариант 2: в комментарии или дополнительных полях
        if not customer_id:
            comment = data.get("comment", "")
            # Ищем паттерн C1234 в комментарии
            import re
            match = re.search(r'[Cc]\d{4}', comment)
            if match:
                customer_id = match.group(0).upper()
        
        # Вариант 3: в номере телефона (если клиент ввел телефон вместо ID)
        if not customer_id and customer_data.get("phone"):
            phone = customer_data["phone"].replace('+', '').replace(' ', '')
            try:
                customer = Customer.objects.filter(phone__contains=phone[-9:]).first()
                if customer:
                    customer_id = customer.customer_id
            except:
                pass

        if not customer_id:
            logger.warning(f"No customer ID found in iiko webhook data")
            return Response({
                "success": False,
                "error": "Customer ID not found in order data"
            }, status=status.HTTP_400_BAD_REQUEST)

        # Ищем клиента в нашей системе
        try:
            customer = Customer.objects.get(customer_id=customer_id)
            logger.info(f"Found customer: {customer.customer_id}")
        except Customer.DoesNotExist:
            logger.warning(f"Customer not found: {customer_id}")
            return Response({
                "success": False, 
                "error": f"Customer {customer_id} not found"
            }, status=status.HTTP_404_NOT_FOUND)

        # Создаем заказы для каждого блюда
        created_orders = []
        total_amount = Decimal("0")
        
        for item in items:
            name = item.get("name", "Unknown dish")
            qty = int(item.get("amount", 1))
            item_sum = Decimal(str(item.get("sum", 0)))
            
            # Рассчитываем цену за единицу
            price = item_sum / qty if qty > 0 else item_sum
            
            # Создаем заказ
            order = Order.objects.create(
                customer=customer,
                external_id=order_id,
                iiko_organization_id=organization_id,
                dish_name=name,
                quantity=qty,
                amount=item_sum,
                notes=f"iiko Order: {order_id}",
                is_synced=True
            )
            
            created_orders.append({
                "dish_name": name,
                "quantity": qty,
                "amount": float(order.amount),
                "bonus_earned": float(order.calculate_bonus())
            })
            
            total_amount += order.amount
        
        # Обновляем данные клиента
        customer.refresh_from_db()
        
        logger.info(f"Successfully created {len(created_orders)} orders for customer {customer_id}")
        
        return Response({
            "success": True,
            "order_id": order_id,
            "customer_id": customer.customer_id,
            "customer_phone": customer.phone,
            "total_amount": float(total_amount),
            "bonus_balance": float(customer.bonus_balance),
            "total_spent": float(customer.total_spent),
            "orders_count": customer.orders_count,
            "current_discount": customer.get_discount_percentage(),
            "orders": created_orders
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error(f"Error processing iiko webhook: {str(e)}", exc_info=True)
        return Response({
            "success": False,
            "error": str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(['GET'])
def test_iiko_integration(request):
    """
    Тест интеграции с iiko
    """
    try:
        # Проверяем подключение
        api = IikoCloudAPI(IIKO_API_LOGIN)
        token = api.get_access_token()
        organizations = api.get_organizations()
        
        return Response({
            'status': 'success',
            'token_obtained': bool(token),
            'organizations': len(organizations),
            'webhook_secret_configured': bool(settings.IIKO_WEBHOOK_SECRET)
        })
    except Exception as e:
        return Response({
            'status': 'error',
            'error': str(e)
        }, status=500)
    
# iiko_views.py - ДОБАВЬ эти функции
@api_view(['GET'])
def check_iiko_connection(request):
    """
    Проверка подключения к iiko API с демо-режимом
    """
    # Временный демо-режим пока не настроен настоящий API ключ
    DEMO_MODE = True
    
    if DEMO_MODE:
        return Response({
            'success': True,
            'connected': True,
            'mode': 'demo',
            'message': 'Демо-режим: Интеграция с iiko готова к настройке',
            'instructions': [
                '1. Зайди в iiko Office: https://cloud.iiko.ru/',
                '2. Настройки → Интеграции → API ключи',
                '3. Создай API ключ и обнови IIKO_API_LOGIN в iiko_service.py',
                '4. Вебхук для настройки: https://militantly-unjeopardised-jene.ngrok-free.dev/api/iiko-webhook/order/'
            ]
        })
    
    try:
        # Получаем токен
        token = iiko_api.get_access_token()
        
        # Получаем организации
        organizations = iiko_api.get_organizations()
        
        return Response({
            'success': True,
            'connected': True,
            'token_obtained': bool(token),
            'organizations_count': len(organizations),
            'organizations': [
                {
                    'id': org['id'],
                    'name': org.get('name', 'Unknown')
                } for org in organizations
            ]
        })
        
    except Exception as e:
        logger.error(f"iiko connection check failed: {e}")
        return Response({
            'success': False,
            'connected': False,
            'error': str(e),
            'message': 'Получи API ключ из iiko Office и обнови настройки'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@csrf_exempt
@api_view(["POST"])
@permission_classes([AllowAny])
def iiko_order_webhook_demo(request):
    """
    Демо-вебхук для тестирования без настоящего iiko API
    Принимает тестовые данные и имитирует работу с iiko
    """
    logger.info("Received DEMO iiko webhook request")
    
    data = request.data
    logger.info(f"Demo webhook data: {json.dumps(data, indent=2)}")
    
    # Принимаем данные в любом формате для тестирования
    customer_id = data.get('customer_id') or data.get('customer', {}).get('id')
    
    if not customer_id:
        return Response({
            "success": False,
            "error": "Customer ID required",
            "demo_mode": True,
            "received_data": data
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        # Ищем клиента в нашей системе
        customer = Customer.objects.get(customer_id=customer_id)
        
        # Создаем демо-заказ
        order = Order.objects.create(
            customer=customer,
            amount=Decimal('2500.00'),  # Демо-сумма
            dish_name="Демо-заказ из iiko",
            quantity=1,
            notes="Демо-заказ: Режим тестирования интеграции",
            is_synced=True
        )
        
        # Обновляем данные клиента
        customer.refresh_from_db()
        
        return Response({
            "success": True,
            "demo_mode": True,
            "message": "Демо-заказ успешно создан!",
            "customer_id": customer.customer_id,
            "order_id": order.id,
            "total_spent": float(customer.total_spent),
            "bonus_balance": float(customer.bonus_balance),
            "orders_count": customer.orders_count,
            "current_discount": customer.get_discount_percentage(),
            "instructions": "Для реальной интеграции получи API ключ из iiko Office"
        }, status=status.HTTP_201_CREATED)
        
    except Customer.DoesNotExist:
        return Response({
            "success": False,
            "error": f"Customer {customer_id} not found",
            "demo_mode": True
        }, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"Error processing demo webhook: {str(e)}")
        return Response({
            "success": False,
            "error": str(e),
            "demo_mode": True
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
def test_cashier_integration(request):
    """
    Тестовый endpoint для проверки интеграции с кассой
    Имитирует ввод ID клиента на кассе
    """
    customer_id = request.data.get('customer_id', 'C1234').upper()
    
    try:
        customer = Customer.objects.get(customer_id=customer_id)
        
        return Response({
            'success': True,
            'customer': {
                'id': customer.customer_id,
                'phone': customer.phone,
                'total_spent': float(customer.total_spent),
                'orders_count': customer.orders_count,
                'bonus_balance': float(customer.bonus_balance),
                'discount_percentage': customer.get_discount_percentage()
            },
            'scenario': [
                '1. Кассир: "У вас есть наше бонусное приложение?"',
                '2. Клиент: "Да, мой ID: ' + customer_id + '"',
                '3. Кассир вводит ID в iiko',
                '4. Заказ автоматически появится в истории заказов клиента'
            ],
            'webhook_url': 'https://militantly-unjeopardised-jene.ngrok-free.dev/api/iiko-webhook/order/'
        })
        
    except Customer.DoesNotExist:
        return Response({
            'success': False,
            'error': f'Клиент с ID {customer_id} не найден',
            'demo_customers': list(Customer.objects.values_list('customer_id', flat=True)[:5])
        })