# Добавьте этот view для детальной диагностики

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from datetime import datetime, timedelta
import requests
import logging

logger = logging.getLogger(__name__)

IIKO_API_LOGIN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJBcGlMb2dpbklkIjoiNGZmMmZhN2QtMjUzNC00MTJjLWI1MWUtYWFkMTNiZmViZGY2IiwibmJmIjoxNzU5NDk0NjQ0LCJleHAiOjE3NTk0OTgyNDQsImlhdCI6MTc1OTQ5NDY0NCwiaXNzIjoiaWlrbyIsImF1ZCI6ImNsaWVudHMifQ.udD933wOKIKv1pgcMOc1WLiae_xNWic5oSAR3MPvbI0"
IIKO_ORG_ID = "a2486bd5-0ee4-4d7c-81a0-106ddc0fddf1"


@api_view(['GET'])
@permission_classes([AllowAny])
def debug_iiko_orders_request(request):
    """
    Детальная диагностика запроса получения заказов
    Показывает весь процесс пошагово
    """
    debug_log = []
    
    try:
        # Шаг 1: Получение токена
        debug_log.append("STEP 1: Getting access token...")
        token_url = "https://api-ru.iiko.services/api/1/access_token"
        token_response = requests.post(
            token_url,
            json={"apiLogin": IIKO_API_LOGIN},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        debug_log.append(f"Token response status: {token_response.status_code}")
        
        if token_response.status_code != 200:
            return Response({
                'error': 'Failed to get token',
                'status_code': token_response.status_code,
                'response': token_response.text,
                'debug_log': debug_log
            }, status=500)
        
        token_data = token_response.json()
        token = token_data.get('token')
        debug_log.append(f"Token obtained: {token[:20]}...")
        
        # Шаг 2: Формирование запроса заказов
        debug_log.append("\nSTEP 2: Preparing orders request...")
        
        date_to = datetime.now()
        date_from = date_to - timedelta(hours=24)
        
        orders_url = "https://api-ru.iiko.services/api/1/deliveries/by_delivery_date_and_status"
        
        # ВАЖНО: Правильный формат данных
        request_data = {
            "organizationIds": [IIKO_ORG_ID],
            "deliveryDateFrom": date_from.strftime("%Y-%m-%d %H:%M:%S"),
            "deliveryDateTo": date_to.strftime("%Y-%m-%d %H:%M:%S"),
            "statuses": [
                "Unconfirmed",
                "WaitCooking", 
                "ReadyForCooking",
                "CookingStarted",
                "CookingCompleted",
                "Waiting",
                "OnWay"
            ]
        }
        
        debug_log.append(f"Request URL: {orders_url}")
        debug_log.append(f"Request data: {request_data}")
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        debug_log.append(f"Request headers: {headers}")
        
        # Шаг 3: Выполнение запроса
        debug_log.append("\nSTEP 3: Sending request to iiko...")
        
        orders_response = requests.post(
            orders_url,
            json=request_data,
            headers=headers,
            timeout=30
        )
        
        debug_log.append(f"Orders response status: {orders_response.status_code}")
        debug_log.append(f"Orders response headers: {dict(orders_response.headers)}")
        
        # Шаг 4: Обработка ответа
        if orders_response.status_code != 200:
            debug_log.append(f"\nERROR Response text: {orders_response.text}")
            
            return Response({
                'error': f'Failed to get orders: {orders_response.status_code}',
                'status_code': orders_response.status_code,
                'response_text': orders_response.text,
                'request_data': request_data,
                'debug_log': debug_log
            }, status=500)
        
        orders_data = orders_response.json()
        orders = orders_data.get('orders', [])
        
        debug_log.append(f"\nSUCCESS: Found {len(orders)} orders")
        
        return Response({
            'success': True,
            'orders_count': len(orders),
            'orders': orders[:3],  # Первые 3 заказа для примера
            'debug_log': debug_log,
            'full_response_keys': list(orders_data.keys())
        })
        
    except Exception as e:
        debug_log.append(f"\nEXCEPTION: {str(e)}")
        logger.error(f"Debug error: {e}", exc_info=True)
        
        return Response({
            'error': str(e),
            'debug_log': debug_log
        }, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def check_token_validity(request):
    """
    Проверка валидности токена
    """
    try:
        import jwt
        from datetime import datetime
        
        # Декодируем токен БЕЗ проверки подписи (только смотрим содержимое)
        decoded = jwt.decode(IIKO_API_LOGIN, options={"verify_signature": False})
        
        exp_timestamp = decoded.get('exp')
        exp_datetime = datetime.fromtimestamp(exp_timestamp)
        now = datetime.now()
        
        is_expired = now > exp_datetime
        time_left = exp_datetime - now if not is_expired else None
        
        return Response({
            'token_info': decoded,
            'expiration': exp_datetime.isoformat(),
            'current_time': now.isoformat(),
            'is_expired': is_expired,
            'time_left': str(time_left) if time_left else 'EXPIRED',
            'message': 'TOKEN EXPIRED! Get new one from iiko Office' if is_expired else 'Token is valid'
        })
        
    except Exception as e:
        return Response({
            'error': str(e),
            'message': 'Failed to decode token'
        }, status=500)


# Добавьте в urls.py:
# path('iiko/debug-orders/', debug_iiko_orders_request, name='debug_orders'),
# path('iiko/check-token/', check_token_validity, name='check_token'),