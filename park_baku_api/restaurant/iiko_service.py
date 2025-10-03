import requests
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import logging
from django.conf import settings
IIKO_API_LOGIN="811a90a0-778c-4314-870b-bc9b39bc6621"
IIKO_API_LOGIN_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJBcGlMb2dpbklkIjoiNGZmMmZhN2QtMjUzNC00MTJjLWI1MWUtYWFkMTNiZmViZGY2IiwibmJmIjoxNzU5NDk0NjQ0LCJleHAiOjE3NTk0OTgyNDQsImlhdCI6MTc1OTQ5NDY0NCwiaXNzIjoiaWlrbyIsImF1ZCI6ImNsaWVudHMifQ.udD933wOKIKv1pgcMOc1WLiae_xNWic5oSAR3MPvbI0"
IIKO_ORG_ID="a2486bd5-0ee4-4d7c-81a0-106ddc0fddf1"
IIKO_WEBHOOK_SECRET="c7b7c1a0-4e12-4b93-bf82-19a5d4c5c2fa"

logger = logging.getLogger(__name__)

class IikoCloudAPI:
    """
    Сервис для интеграции с iiko Cloud API (Transport API)
    """

    def __init__(self, api_key: str = IIKO_API_LOGIN):
        self.api_key = api_key
        self.base_url = "https://api-ru.iiko.services/api/1"
        self.token = None
        self.token_expires = None
        self.organization_id = None
        
    def get_access_token(self) -> str:
        """Получение токена доступа"""
        if self.token and self.token_expires and datetime.now() < self.token_expires:
            return self.token
            
        url = f"{self.base_url}/access_token"
        headers = {
            "Content-Type": "application/json"
        }
        data = {
            "apiLogin": self.api_key
        }
        
        try:
            logger.info(f"Requesting iiko token with API login: {self.api_key[:20]}...")
            response = requests.post(url, json=data, headers=headers, timeout=30)
            
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response headers: {dict(response.headers)}")
            
            if response.status_code == 401:
                logger.error("iiko API: 401 Unauthorized - Invalid API login")
                raise Exception("Invalid API login (401 Unauthorized)")
                
            response.raise_for_status()
            
            result = response.json()
            self.token = result.get('token')
            
            if not self.token:
                logger.error("No token in iiko response")
                raise Exception("No token in response")
                
            # Токен действует 1 час
            self.token_expires = datetime.now() + timedelta(hours=1)
            
            logger.info("iiko access token obtained successfully")
            return self.token
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get iiko access token: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response text: {e.response.text}")
            raise    

    def get_organizations(self) -> List[Dict]:
        """Получение списка организаций"""
        token = self.get_access_token()
        
        url = f"{self.base_url}/api/1/organizations"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        data = {
            "returnAdditionalInfo": False,
            "includeDisabled": False
        }
        
        try:
            response = requests.post(url, json=data, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            organizations = result.get('organizations', [])
            
            if organizations:
                # Сохраняем ID первой организации
                self.organization_id = organizations[0]['id']
                logger.info(f"Found {len(organizations)} organizations")
            
            return organizations
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get organizations: {e}")
            raise
    
    def get_customer_by_phone(self, phone: str) -> Optional[Dict]:
        """Поиск клиента по номеру телефона"""
        token = self.get_access_token()
        
        if not self.organization_id:
            self.get_organizations()
        
        url = f"{self.base_url}/api/1/loyalty/iiko/customers/get_customer_by_phone"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        data = {
            "organizationId": self.organization_id,
            "phone": phone,
            "type": "phone"
        }
        
        try:
            response = requests.post(url, json=data, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get customer by phone: {e}")
            return None
    
    def create_or_update_customer(self, phone: str, name: str = None, customer_id: str = None) -> Dict:
        """Создание или обновление клиента в iiko"""
        token = self.get_access_token()
        
        if not self.organization_id:
            self.get_organizations()
        
        url = f"{self.base_url}/api/1/loyalty/iiko/customers/create_or_update"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        data = {
            "organizationId": self.organization_id,
            "customer": {
                "phone": phone,
                "name": name or f"Customer {phone}",
            }
        }
        
        # Если есть ID клиента в нашей системе, добавляем как референсный ID
        if customer_id:
            data["customer"]["referrerCode"] = customer_id
        
        try:
            response = requests.post(url, json=data, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            logger.info(f"Customer created/updated: {phone}")
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create/update customer: {e}")
            raise
    
    def get_customer_balance(self, customer_iiko_id: str) -> Dict:
        """Получение баланса и информации о клиенте"""
        token = self.get_access_token()
        
        if not self.organization_id:
            self.get_organizations()
        
        url = f"{self.base_url}/api/1/loyalty/iiko/customers/{customer_iiko_id}/info"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        data = {
            "organizationId": self.organization_id
        }
        
        try:
            response = requests.post(url, json=data, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get customer balance: {e}")
            return {}
        
    def get_order_by_id(self, organization_id: str, order_id: str) -> Dict:
        """
        Получение информации о заказе по ID из iiko
        """
        token = self.get_access_token()
        
        url = f"{self.base_url}/api/1/order"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        data = {
            "organizationId": organization_id,
            "orderIds": [order_id]
        }
        
        try:
            response = requests.post(url, json=data, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            return result
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get order by ID: {e}")
            raise


class IikoWebhookProcessor:
    """
    Обработчик вебхуков от iiko
    """
    
    @staticmethod
    def validate_webhook_signature(request_body: bytes, signature: str, secret: str) -> bool:
        """Проверка подписи вебхука"""
        expected_signature = hashlib.sha256(
            f"{request_body.decode('utf-8')}{secret}".encode()
        ).hexdigest()
        
        return expected_signature == signature
    
    @staticmethod
    def process_order_webhook(data: Dict) -> Dict:
        """
        Обработка вебхука о новом заказе
        Возвращает структурированные данные заказа
        """
        order_info = {
            'order_id': data.get('orderId'),
            'customer_phone': None,
            'customer_id': None,
            'amount': 0,
            'items': [],
            'payment_type': None,
            'created_at': data.get('createdAt'),
        }
        
        # Извлекаем информацию о клиенте
        if 'customer' in data:
            customer = data['customer']
            order_info['customer_phone'] = customer.get('phone')
            order_info['customer_id'] = customer.get('id')
            
        # Извлекаем сумму заказа
        if 'sum' in data:
            order_info['amount'] = float(data['sum'])
        elif 'orderSum' in data:
            order_info['amount'] = float(data['orderSum'])
            
        # Извлекаем позиции заказа
        if 'items' in data:
            for item in data['items']:
                order_info['items'].append({
                    'name': item.get('name'),
                    'amount': item.get('amount'),
                    'sum': item.get('sum')
                })
        
        # Тип оплаты
        if 'payments' in data and data['payments']:
            order_info['payment_type'] = data['payments'][0].get('paymentTypeKind')
        
        return order_info
    
    @staticmethod
    def process_payment_webhook(data: Dict) -> Dict:
        """
        Обработка вебхука об оплате
        """
        payment_info = {
            'order_id': data.get('orderId'),
            'payment_id': data.get('paymentId'),
            'customer_id': data.get('customerId'),
            'amount': float(data.get('sum', 0)),
            'payment_type': data.get('paymentType'),
            'is_processed': data.get('isProcessed', False),
            'created_at': data.get('date')
        }
        
        return payment_info


def get_order_by_id(organization_id: str, order_id: str) -> Dict:
    """
    Получение информации о заказе по ID из iiko
    """
    # Предполагается, что API ключ хранится в настройках Django
    api_key = getattr(settings, 'IIKO_API_KEY', 'your_default_api_key_here')
    api = IikoCloudAPI(api_key)
    return api.get_order_by_id(organization_id, order_id)