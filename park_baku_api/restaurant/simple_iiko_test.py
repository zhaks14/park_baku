# simple_iiko_test.py - создайте этот файл в вашем приложении

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
def simple_iiko_test(request):
    """
    Самый простой тест - пошагово проверяет всё
    """
    result = {
        'step1_token': None,
        'step2_organizations': None,
        'step3_orders_request': None,
        'step4_orders_response': None,
    }
    
    try:
        # ===== ШАГ 1: Получение токена =====
        print("\n=== STEP 1: Getting token ===")
        token_url = "https://api-ru.iiko.services/api/1/access_token"
        token_resp = requests.post(
            token_url,
            json={"apiLogin": IIKO_API_LOGIN},
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        print(f"Token response status: {token_resp.status_code}")
        print(f"Token response body: {token_resp.text}")
        
        if token_resp.status_code != 200:
            result['step1_token'] = {
                'status': 'FAILED',
                'code': token_resp.status_code,
                'response': token_resp.text
            }
            return Response(result, status=500)
        
        token_data = token_resp.json()
        token = token_data.get('token')
        
        result['step1_token'] = {
            'status': 'SUCCESS',
            'token_preview': token[:30] + '...' if token else None
        }
        
        print(f"Token obtained: {token[:30]}...")
        
        # ===== ШАГ 2: Получение организаций =====
        print("\n=== STEP 2: Getting organizations ===")
        org_url = "https://api-ru.iiko.services/api/1/organizations"
        org_resp = requests.post(
            org_url,
            json={},
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            timeout=30
        )
        
        print(f"Organizations response status: {org_resp.status_code}")
        print(f"Organizations response body: {org_resp.text[:500]}")
        
        if org_resp.status_code != 200:
            result['step2_organizations'] = {
                'status': 'FAILED',
                'code': org_resp.status_code,
                'response': org_resp.text
            }
            return Response(result, status=500)
        
        org_data = org_resp.json()
        orgs = org_data.get('organizations', [])
        
        result['step2_organizations'] = {
            'status': 'SUCCESS',
            'count': len(orgs),
            'organizations': [
                {'id': o['id'], 'name': o.get('name', 'Unknown')}
                for o in orgs
            ]
        }
        
        print(f"Found {len(orgs)} organizations")
        
        # ===== ШАГ 3: Формирование запроса заказов =====
        print("\n=== STEP 3: Preparing orders request ===")
        
        date_to = datetime.now()
        date_from = date_to - timedelta(hours=168)  # 7 дней назад (больше шанс найти заказы)
        
        orders_url = "https://api-ru.iiko.services/api/1/deliveries/by_delivery_date_and_status"
        
        # Попробуем разные варианты запроса
        request_variants = [
            {
                'name': 'Вариант 1: Все статусы',
                'data': {
                    "organizationIds": [IIKO_ORG_ID],
                    "deliveryDateFrom": date_from.strftime("%Y-%m-%d %H:%M:%S"),
                    "deliveryDateTo": date_to.strftime("%Y-%m-%d %H:%M:%S"),
                    "statuses": ["Unconfirmed", "WaitCooking", "ReadyForCooking", 
                                "CookingStarted", "CookingCompleted", "Waiting", 
                                "OnWay", "Delivered", "Closed", "Cancelled"]
                }
            },
            {
                'name': 'Вариант 2: Без фильтра статусов',
                'data': {
                    "organizationIds": [IIKO_ORG_ID],
                    "deliveryDateFrom": date_from.strftime("%Y-%m-%d %H:%M:%S"),
                    "deliveryDateTo": date_to.strftime("%Y-%m-%d %H:%M:%S")
                }
            }
        ]
        
        result['step3_orders_request'] = []
        
        for variant in request_variants:
            print(f"\n--- Trying: {variant['name']} ---")
            print(f"Request data: {variant['data']}")
            
            orders_resp = requests.post(
                orders_url,
                json=variant['data'],
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                timeout=30
            )
            
            print(f"Response status: {orders_resp.status_code}")
            print(f"Response body: {orders_resp.text[:1000]}")
            
            variant_result = {
                'variant': variant['name'],
                'status_code': orders_resp.status_code,
                'request_data': variant['data'],
                'response_preview': orders_resp.text[:500]
            }
            
            if orders_resp.status_code == 200:
                orders_data = orders_resp.json()
                orders = orders_data.get('orders', [])
                variant_result['success'] = True
                variant_result['orders_count'] = len(orders)
                variant_result['orders_sample'] = orders[:2]  # Первые 2 заказа
                
                result['step4_orders_response'] = {
                    'status': 'SUCCESS',
                    'variant_used': variant['name'],
                    'orders_count': len(orders),
                    'orders': orders[:3]
                }
                
                print(f"✅ SUCCESS! Found {len(orders)} orders")
                break
            else:
                variant_result['success'] = False
                variant_result['error'] = orders_resp.text
                print(f"❌ FAILED with {orders_resp.status_code}")
            
            result['step3_orders_request'].append(variant_result)
        
        return Response(result)
        
    except Exception as e:
        print(f"\n❌ EXCEPTION: {str(e)}")
        import traceback
        traceback.print_exc()
        
        return Response({
            'error': str(e),
            'traceback': traceback.format_exc(),
            'partial_results': result
        }, status=500)


# Добавьте в urls.py:
# path('iiko/simple-test/', simple_iiko_test, name='simple_iiko_test'),