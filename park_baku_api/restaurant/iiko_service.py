# # iiko_service.py - ПОЛНОСТЬЮ ИСПРАВЛЕННАЯ ВЕРСИЯ
# import requests
# import hashlib
# from datetime import datetime, timedelta
# from typing import Optional, Dict, List
# import logging
# from django.conf import settings
# from decimal import Decimal

# logger = logging.getLogger(__name__)


# API_KEY="9014bf1230364c329d25186c13b44775"
# IIKO_API_LOGIN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJBcGlMb2dpbklkIjoiNGZmMmZhN2QtMjUzNC00MTJjLWI1MWUtYWFkMTNiZmViZGY2IiwibmJmIjoxNzU5NjY2MDYxLCJleHAiOjE3NTk2Njk2NjEsImlhdCI6MTc1OTY2NjA2MSwiaXNzIjoiaWlrbyIsImF1ZCI6ImNsaWVudHMifQ.kbQNynXkKedTYU_wtBje-Zhoq_Ieam215gtHqZaV09k"
# IIKO_ORG_ID = "a2486bd5-0ee4-4d7c-81a0-106ddc0fddf1"
# IIKO_WEBHOOK_SECRET = "c7b7c1a0-4e12-4b93-bf82-19a5d4c5c2fa"

# class IikoCloudAPI:
#     """
#     Сервис для интеграции с iiko Cloud API (Transport API)
#     Документация: https://api-ru.iiko.services/
#     """

#     def __init__(self, api_key: str = API_KEY):
#         self.api_key = api_key or API_KEY
#         self.base_url = "https://api-ru.iiko.services/api/1"
#         self.token = IIKO_API_LOGIN or None
#         self.token_expires = None
#         self.organization_id = IIKO_ORG_ID or None
        
#     def get_access_token(self) -> str:
#         """Получение токена доступа"""
#         if self.token and self.token_expires and datetime.now() < self.token_expires:
#             return self.token
            
#         url = f"{self.base_url}/access_token"
#         headers = {"Content-Type": "application/json"}
#         data = {"apiLogin": API_KEY}
        
#         try:
#             logger.info(f"Requesting iiko token...")
#             response = requests.post(url, json=data, headers=headers, timeout=30)
            
#             if response.status_code == 401:
#                 logger.error("iiko API: 401 Unauthorized - Invalid API login")
#                 raise Exception("Invalid API login (401 Unauthorized)")
                
#             response.raise_for_status()
            
#             result = response.json()
#             self.token = result.get('token')
            
#             if not self.token:
#                 logger.error("No token in iiko response")
#                 raise Exception("No token in response")
                
#             # Токен действует 1 час
#             self.token_expires = datetime.now() + timedelta(hours=1)
            
#             logger.info("✅ iiko access token obtained successfully")
#             return self.token
            
#         except requests.exceptions.RequestException as e:
#             logger.error(f"❌ Failed to get iiko access token: {e}")
#             if hasattr(e, 'response') and e.response is not None:
#                 logger.error(f"Response text: {e.response.text}")
#             raise    

#     def get_organizations(self) -> List[Dict]:
#         """Получение списка организаций"""
#         token = self.get_access_token()
        
#         # ✅ ИСПРАВЛЕНО: убран дублирующий /api/1
#         url = f"{self.base_url}/organizations"
#         headers = {
#             "Authorization": f"Bearer {token}",
#             "Content-Type": "application/json"
#         }
        
#         try:
#             # Для organizations используем POST с пустым телом
#             response = requests.post(url, json={}, headers=headers, timeout=30)
#             response.raise_for_status()
            
#             result = response.json()
#             organizations = result.get('organizations', [])
            
#             if organizations and not self.organization_id:
#                 self.organization_id = organizations[0]['id']
#                 logger.info(f"✅ Found {len(organizations)} organizations")
            
#             return organizations
            
#         except requests.exceptions.RequestException as e:
#             logger.error(f"❌ Failed to get organizations: {e}")
#             if hasattr(e, 'response') and e.response is not None:
#                 logger.error(f"Response: {e.response.text}")
#             raise

#     def get_terminal_groups(self) -> List[Dict]:
#         """Получение списка групп терминалов"""
#         token = self.get_access_token()
        
#         if not self.organization_id:
#             self.get_organizations()
        
#         url = f"{self.base_url}/terminal_groups"
#         headers = {
#             "Authorization": f"Bearer {token}",
#             "Content-Type": "application/json"
#         }
#         data = {"organizationIds": [self.organization_id]}
        
#         try:
#             response = requests.post(url, json=data, headers=headers, timeout=30)
            
#             logger.info(f"Terminals response status: {response.status_code}")
#             logger.info(f"Terminals response: {response.text[:500]}")
            
#             response.raise_for_status()
            
#             result = response.json()

#             terminal_groups = result.get('terminalGroups',[])
#             valid_terminals = []
#             for terminal in terminal_groups:
#                 if 'id' in terminal: 
#                     valid_terminals.append({
#                         'id': terminal['id'], 
#                         'name': terminal.get('name', 'Unknown')
#                     })
#             return valid_terminals
#         except Exception as e:
#             logger.warning(f"Ошибка обработки терминалов: {e}")
#             return []
            
#         except requests.exceptions.RequestException as e:
#             logger.error(f"❌ Failed to get terminal groups: {e}")
#             if hasattr(e, 'response') and e.response is not None:
#                 logger.error(f"Response: {e.response.text}")
#             raise

#     def get_deliveries_by_date(
#         self, 
#         date_from: datetime = None,
#         date_to: datetime = None,
#         statuses: Optional[List[str]] = None
#     ) -> List[Dict]:
#         """
#         Получить заказы доставки за период
#         ЭТО ТО, ЧТО ВАМ НУЖНО ДЛЯ ПОЛУЧЕНИЯ АКТУАЛЬНЫХ ЗАКАЗОВ!
#         """
#         token = self.get_access_token()
        
#         if not self.organization_id:
#             self.get_organizations()
        
#         # Дефолтные даты
#         if not date_to:
#             date_to = datetime.now()
#         if not date_from:
#             date_from = date_to - timedelta(hours=4)
        
#         url = f"{self.base_url}/deliveries/by_delivery_date_and_status"
#         headers = {
#             "Authorization": f"Bearer {token}",
#             "Content-Type": "application/json"
#         }
        
#         # Формируем данные запроса
#         # ВАЖНО: iiko требует ISO 8601 формат с 'T': "YYYY-MM-DDTHH:MM:SS"
#         data = {
#             "organizationIds": [self.organization_id],
#             "deliveryDateFrom": date_from.strftime("%Y-%m-%dT%H:%M:%S"),
#             "deliveryDateTo": date_to.strftime("%Y-%m-%dT%H:%M:%S")
#         }
        
#         # Добавляем статусы ТОЛЬКО если они переданы
#         if statuses is not None:
#             data["statuses"] = statuses
        
#         logger.info(f"Request data: {data}")
        
#         try:
#             logger.info(f"🔍 Fetching orders from {date_from} to {date_to}")
#             logger.info(f"Request URL: {url}")
#             logger.info(f"Request data: {data}")
            
#             response = requests.post(url, json=data, headers=headers, timeout=30)
            
#             # Логируем ответ ДО raise_for_status
#             logger.info(f"Response status: {response.status_code}")
#             logger.info(f"Response body: {response.text[:1000]}")
            
#             if response.status_code != 200:
#                 error_detail = response.text
#                 logger.error(f"❌ iiko API error: {error_detail}")
#                 raise Exception(f"iiko API returned {response.status_code}: {error_detail}")
            
#             result = response.json()
#             orders = result.get('orders', [])
#             logger.info(f"✅ Found {len(orders)} delivery orders")
#             return orders
            
#         except requests.exceptions.RequestException as e:
#             logger.error(f"❌ Failed to get delivery orders: {e}")
#             if hasattr(e, 'response') and e.response is not None:
#                 logger.error(f"Response: {e.response.text}")
#             raise

#     def get_delivery_by_id(self, order_ids: List[str]) -> List[Dict]:
#         """Получить заказы доставки по ID"""
#         token = self.get_access_token()
        
#         if not self.organization_id:
#             self.get_organizations()
        
#         url = f"{self.base_url}/deliveries/by_id"
#         headers = {
#             "Authorization": f"Bearer {token}",
#             "Content-Type": "application/json"
#         }
#         data = {
#             "organizationIds": [self.organization_id],
#             "orderIds": order_ids
#         }
        
#         try:
#             response = requests.post(url, json=data, headers=headers, timeout=30)
#             response.raise_for_status()
            
#             result = response.json()
#             orders = result.get('orders', [])
#             logger.info(f"✅ Found {len(orders)} orders by ID")
#             return orders
            
#         except requests.exceptions.RequestException as e:
#             logger.error(f"❌ Failed to get orders by ID: {e}")
#             raise

#     def get_order_by_id(self, order_id: str) -> Dict:
#         """
#         Получение информации о конкретном заказе по ID
#         ✅ ИСПРАВЛЕНО: используется правильный endpoint
#         """
#         orders = self.get_delivery_by_id([order_id])
#         if orders:
#             return orders[0]
#         else:
#             logger.warning(f"Order {order_id} not found")
#             return {}


# class IikoWebhookProcessor:
#     """Обработчик вебхуков от iiko"""
    
#     @staticmethod
#     def validate_webhook_signature(request_body: bytes, signature: str) -> bool:
#         """Проверка подписи вебхука"""
#         expected_signature = hashlib.sha256(
#             f"{request_body.decode('utf-8')}{IIKO_WEBHOOK_SECRET}".encode()
#         ).hexdigest()
        
#         is_valid = expected_signature == signature
#         if not is_valid:
#             logger.warning("⚠️ Invalid webhook signature")
        
#         return is_valid
    
#     @staticmethod
#     def process_order_webhook(data: Dict) -> Dict:
#         """Обработка вебхука о новом заказе"""
#         order_info = {
#             'order_id': data.get('orderId') or data.get('id'),
#             'customer_phone': None,
#             'customer_id': None,
#             'amount': Decimal('0'),
#             'items': [],
#             'payment_type': None,
#             'created_at': data.get('createdAt') or data.get('whenCreated'),
#             'status': data.get('status'),
#         }
        
#         # Клиент
#         if 'customer' in data:
#             customer = data['customer']
#             order_info['customer_phone'] = customer.get('phone')
#             order_info['customer_id'] = customer.get('id')
            
#         # Сумма заказа
#         if 'sum' in data:
#             order_info['amount'] = Decimal(str(data['sum']))
#         elif 'orderSum' in data:
#             order_info['amount'] = Decimal(str(data['orderSum']))
#         elif 'fullSum' in data:
#             order_info['amount'] = Decimal(str(data['fullSum']))
            
#         # Позиции заказа
#         if 'items' in data:
#             for item in data['items']:
#                 order_info['items'].append({
#                     'product_id': item.get('productId'),
#                     'name': item.get('name') or item.get('product', {}).get('name'),
#                     'amount': item.get('amount', 1),
#                     'sum': Decimal(str(item.get('sum', 0)))
#                 })
        
#         # Тип оплаты
#         if 'payments' in data and data['payments']:
#             order_info['payment_type'] = data['payments'][0].get('paymentTypeKind')
        
#         return order_info


# # ✅ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# def get_iiko_client() -> IikoCloudAPI:
#     """Получить инициализированный клиент iiko API"""
#     return IikoCloudAPI()


# def get_active_orders(hours: int = 24) -> List[Dict]:
#     """
#     ✅ ГЛАВНАЯ ФУНКЦИЯ: Получить активные заказы за последние N часов
#     """
#     client = get_iiko_client()
#     date_from = datetime.now() - timedelta(hours=hours)
#     return client.get_deliveries_by_date(date_from=date_from)


# def get_order_by_id(organization_id: str, order_id: str) -> Dict:
#     """Получение информации о заказе по ID"""
#     client = get_iiko_client()
#     # organization_id игнорируется, т.к. уже установлен в IIKO_ORG_ID
#     return client.get_order_by_id(order_id)

# iiko_service.py - ПОЛНОСТЬЮ ИСПРАВЛЕННАЯ ВЕРСИЯ
import requests
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import logging
from django.conf import settings
from decimal import Decimal

logger = logging.getLogger(__name__)

# Ваши реальные credentials
API_TOKEN = "9014bf1230364c329d25186c13b44775"
IIKO_API_LOGIN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJBcGlMb2dpbklkIjoiNGZmMmZhN2QtMjUzNC00MTJjLWI1MWUtYWFkMTNiZmViZGY2IiwibmJmIjoxNzU5Njc1NDU3LCJleHAiOjE3NTk2NzkwNTcsImlhdCI6MTc1OTY3NTQ1NywiaXNzIjoiaWlrbyIsImF1ZCI6ImNsaWVudHMifQ.zrkpWyp5U_Z5if6598iRcNngF69cKs4l_P1El6eWxlM"
IIKO_ORG_ID = "a2486bd5-0ee4-4d7c-81a0-106ddc0fddf1"
IIKO_WEBHOOK_SECRET = "c7b7c1a0-4e12-4b93-bf82-19a5d4c5c2fa"


class IikoCloudAPI:
    """
    Сервис для интеграции с iiko Cloud API (Transport API)
    Документация: https://api-ru.iiko.services/
    """

    def __init__(self, api_key: str = API_TOKEN):
        self.api_key = api_key
        self.base_url = "https://api-ru.iiko.services/api/1"
        self.token = None
        self.token_expires = None
        self.organization_id = IIKO_ORG_ID or None
        
    def get_access_token(self) -> str:
        """Получение токена доступа"""
        if self.token and self.token_expires and datetime.now() < self.token_expires:
            return self.token
            
        url = f"{self.base_url}/access_token"
        headers = {"Content-Type": "application/json"}
        data = {"apiLogin": self.api_key}
        
        try:
            logger.info(f"Requesting iiko token...")
            response = requests.post(url, json=data, headers=headers, timeout=30)
            
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
            
            logger.info("✅ iiko access token obtained successfully")
            return self.token
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to get iiko access token: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response text: {e.response.text}")
            raise    

    def get_organizations(self) -> List[Dict]:
        """Получение списка организаций"""
        token = self.get_access_token()
        
        # ✅ ИСПРАВЛЕНО: убран дублирующий /api/1
        url = f"{self.base_url}/organizations"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        try:
            # Для organizations используем POST с пустым телом
            response = requests.post(url, json={}, headers=headers, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            organizations = result.get('organizations', [])
            
            if organizations and not self.organization_id:
                self.organization_id = organizations[0]['id']
                logger.info(f"✅ Found {len(organizations)} organizations")
            
            return organizations
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to get organizations: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise

    def get_terminal_groups(self) -> List[Dict]:
        """Получение списка групп терминалов"""
        token = self.get_access_token()
        
        if not self.organization_id:
            self.get_organizations()
        
        url = f"{self.base_url}/terminal_groups"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        data = {"organizationIds": [self.organization_id]}
        
        try:
            response = requests.post(url, json=data, headers=headers, timeout=30)
            
            logger.info(f"Terminals response status: {response.status_code}")
            logger.info(f"Terminals response: {response.text[:500]}")
            
            response.raise_for_status()
            
            result = response.json()
            
            # iiko может вернуть terminalGroups или corporateItemTerminalGroups
            terminal_groups = result.get('terminalGroups', result.get('corporateItemTerminalGroups', []))
            
            logger.info(f"✅ Found {len(terminal_groups)} terminal groups")
            return terminal_groups
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to get terminal groups: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise

    def get_deliveries_by_date(
        self, 
        date_from: datetime = None,
        date_to: datetime = None,
        statuses: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Получить заказы доставки за период
        ЭТО ТО, ЧТО ВАМ НУЖНО ДЛЯ ПОЛУЧЕНИЯ АКТУАЛЬНЫХ ЗАКАЗОВ!
        """
        token = self.get_access_token()
        
        if not self.organization_id:
            self.get_organizations()
        
        # Дефолтные даты
        if not date_to:
            date_to = datetime.now()
        if not date_from:
            date_from = date_to - timedelta(hours=24)
        
        url = f"{self.base_url}/deliveries/by_delivery_date_and_status"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        # Формируем данные запроса
        # ВАЖНО: iiko требует ISO 8601 формат с 'T': "YYYY-MM-DDTHH:MM:SS"
        data = {
            "organizationIds": [self.organization_id],
            "deliveryDateFrom": date_from.strftime("%Y-%m-%dT%H:%M:%S"),
            "deliveryDateTo": date_to.strftime("%Y-%m-%dT%H:%M:%S")
        }
        
        # Добавляем статусы ТОЛЬКО если они переданы
        if statuses is not None:
            data["statuses"] = statuses
        
        logger.info(f"Request data: {data}")
        
        try:
            logger.info(f"🔍 Fetching orders from {date_from} to {date_to}")
            logger.info(f"Request URL: {url}")
            logger.info(f"Request data: {data}")
            
            response = requests.post(url, json=data, headers=headers, timeout=30)
            
            # Логируем ответ ДО raise_for_status
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response body: {response.text[:1000]}")
            
            if response.status_code != 200:
                error_detail = response.text
                logger.error(f"❌ iiko API error: {error_detail}")
                raise Exception(f"iiko API returned {response.status_code}: {error_detail}")
            
            result = response.json()
            orders = result.get('orders', [])
            logger.info(f"✅ Found {len(orders)} delivery orders")
            return orders
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to get delivery orders: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise

    def get_delivery_by_id(self, order_ids: List[str]) -> List[Dict]:
        """Получить заказы доставки по ID"""
        token = self.get_access_token()
        
        if not self.organization_id:
            self.get_organizations()
        
        url = f"{self.base_url}/deliveries/by_id"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        data = {
            "organizationIds": [self.organization_id],
            "orderIds": order_ids
        }
        
        try:
            response = requests.post(url, json=data, headers=headers, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            orders = result.get('orders', [])
            logger.info(f"✅ Found {len(orders)} orders by ID")
            return orders
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Failed to get orders by ID: {e}")
            raise

    def get_order_by_id(self, order_id: str) -> Dict:
        """
        Получение информации о конкретном заказе по ID
        ✅ ИСПРАВЛЕНО: используется правильный endpoint
        """
        orders = self.get_delivery_by_id([order_id])
        if orders:
            return orders[0]
        else:
            logger.warning(f"Order {order_id} not found")
            return {}

    def get_olap_sales_report(
        self, 
        date_from: datetime = None, 
        date_to: datetime = None
    ) -> List[Dict]:
        """
        Получить отчёт по продажам через OLAP
        Включает ВСЕ закрытые заказы (столики, доставка, самовывоз)
        
        ВАЖНО: Возвращает только ЗАКРЫТЫЕ/ОПЛАЧЕННЫЕ заказы
        """
        token = self.get_access_token()
        
        if not self.organization_id:
            self.get_organizations()
        
        # Дефолтные даты
        if not date_to:
            date_to = datetime.now()
        if not date_from:
            date_from = date_to - timedelta(hours=24)
        
        url = f"{self.base_url}/reports/olap"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        data = {
            "reportType": "SALES",
            "buildSummary": False,
            "groupByRowFields": [
                "OrderNum",
                "OrderType",
                "OpenDate.Typed",
                "CloseDate.Typed",
                "DishName",
                "Waiter.Name"
            ],
            "aggregateFields": [
                "DishAmountInt",
                "DishSum",
                "OrdersCount"
            ],
            "filters": {
                "OpenDate.Typed": {
                    "filterType": "DateRange",
                    "from": date_from.strftime("%Y-%m-%d %H:%M:%S"),
                    "to": date_to.strftime("%Y-%m-%d %H:%M:%S"),
                    "includeLow": True,
                    "includeHigh": True
                },
                "DeletedWithWriteoff": {
                    "filterType": "IncludeValues",
                    "values": [False]
                },
                "NonCashPaymentType": {
                    "filterType": "ExcludeValues", 
                    "values": []
                }
            }
        }
        
        try:
            logger.info(f"Requesting OLAP report from {date_from} to {date_to}")
            response = requests.post(url, json=data, headers=headers, timeout=60)
            
            logger.info(f"OLAP response status: {response.status_code}")
            
            if response.status_code != 200:
                error_detail = response.text
                logger.error(f"OLAP API error: {error_detail}")
                raise Exception(f"OLAP API returned {response.status_code}: {error_detail}")
            
            result = response.json()
            
            # Обрабатываем ответ OLAP
            data_rows = result.get('data', [])
            logger.info(f"Found {len(data_rows)} OLAP records")
            
            # Группируем по заказам
            orders_dict = {}
            for row in data_rows:
                order_num = row.get('OrderNum')
                if not order_num:
                    continue
                
                if order_num not in orders_dict:
                    orders_dict[order_num] = {
                        'order_number': order_num,
                        'order_type': row.get('OrderType'),
                        'open_date': row.get('OpenDate.Typed'),
                        'close_date': row.get('CloseDate.Typed'),
                        'waiter': row.get('Waiter.Name'),
                        'items': [],
                        'total_sum': 0
                    }
                
                # Добавляем позицию
                orders_dict[order_num]['items'].append({
                    'dish_name': row.get('DishName'),
                    'quantity': row.get('DishAmountInt', 0),
                    'sum': row.get('DishSum', 0)
                })
                orders_dict[order_num]['total_sum'] += row.get('DishSum', 0)
            
            orders_list = list(orders_dict.values())
            logger.info(f"Processed into {len(orders_list)} unique orders")
            
            return orders_list
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get OLAP report: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            raise


class IikoWebhookProcessor:
    """Обработчик вебхуков от iiko"""
    
    @staticmethod
    def validate_webhook_signature(request_body: bytes, signature: str) -> bool:
        """Проверка подписи вебхука"""
        expected_signature = hashlib.sha256(
            f"{request_body.decode('utf-8')}{IIKO_WEBHOOK_SECRET}".encode()
        ).hexdigest()
        
        is_valid = expected_signature == signature
        if not is_valid:
            logger.warning("⚠️ Invalid webhook signature")
        
        return is_valid
    
    @staticmethod
    def process_order_webhook(data: Dict) -> Dict:
        """Обработка вебхука о новом заказе"""
        order_info = {
            'order_id': data.get('orderId') or data.get('id'),
            'customer_phone': None,
            'customer_id': None,
            'amount': Decimal('0'),
            'items': [],
            'payment_type': None,
            'created_at': data.get('createdAt') or data.get('whenCreated'),
            'status': data.get('status'),
        }
        
        # Клиент
        if 'customer' in data:
            customer = data['customer']
            order_info['customer_phone'] = customer.get('phone')
            order_info['customer_id'] = customer.get('id')
            
        # Сумма заказа
        if 'sum' in data:
            order_info['amount'] = Decimal(str(data['sum']))
        elif 'orderSum' in data:
            order_info['amount'] = Decimal(str(data['orderSum']))
        elif 'fullSum' in data:
            order_info['amount'] = Decimal(str(data['fullSum']))
            
        # Позиции заказа
        if 'items' in data:
            for item in data['items']:
                order_info['items'].append({
                    'product_id': item.get('productId'),
                    'name': item.get('name') or item.get('product', {}).get('name'),
                    'amount': item.get('amount', 1),
                    'sum': Decimal(str(item.get('sum', 0)))
                })
        
        # Тип оплаты
        if 'payments' in data and data['payments']:
            order_info['payment_type'] = data['payments'][0].get('paymentTypeKind')
        
        return order_info


# ✅ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
def get_iiko_client() -> IikoCloudAPI:
    """Получить инициализированный клиент iiko API"""
    return IikoCloudAPI()


def get_active_orders(hours: int = 24) -> List[Dict]:
    """
    ✅ ГЛАВНАЯ ФУНКЦИЯ: Получить активные заказы за последние N часов
    """
    client = get_iiko_client()
    date_from = datetime.now() - timedelta(hours=hours)
    return client.get_deliveries_by_date(date_from=date_from)


def get_order_by_id(organization_id: str, order_id: str) -> Dict:
    """Получение информации о заказе по ID"""
    client = get_iiko_client()
    # organization_id игнорируется, т.к. уже установлен в IIKO_ORG_ID
    return client.get_order_by_id(order_id)