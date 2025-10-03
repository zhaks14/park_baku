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

from .models import Customer, Order
from .iiko_service import IikoCloudAPI, IikoWebhookProcessor

logger = logging.getLogger(__name__)

# Инициализация iiko API (добавьте API ключ в settings.py)
iiko_api = IikoCloudAPI(api_key=settings.IIKO_API_KEY)


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