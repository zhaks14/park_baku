# iiko_webhook_setup.py
import requests
from django.conf import settings
from .iiko_service import IikoCloudAPI

IIKO_API_LOGIN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJBcGlMb2dpbklkIjoiNGZmMmZhN2QtMjUzNC00MTJjLWI1MWUtYWFkMTNiZmViZGY2IiwibmJmIjoxNzU5NDk0NjQ0LCJleHAiOjE3NTk0OTgyNDQsImlhdCI6MTc1OTQ5NDY0NCwiaXNzIjoiaWlrbyIsImF1ZCI6ImNsaWVudHMifQ.udD933wOKIKv1pgcMOc1WLiae_xNWic5oSAR3MPvbI0"
IIKO_ORG_ID="a2486bd5-0ee4-4d7c-81a0-106ddc0fddf1"
IIKO_WEBHOOK_SECRET="c7b7c1a0-4e12-4b93-bf82-19a5d4c5c2fa"

def setup_iiko_webhook():
    """
    Настройка вебхука в iiko для отправки заказов
    """
    api = IikoCloudAPI(IIKO_API_LOGIN)
    token = api.get_access_token()
    
    webhook_url = "https://militantly-unjeopardised-jene.ngrok-free.dev/api/iiko-webhook/order/"
    
    # URL для настройки вебхуков в iiko (проверь в документации)
    setup_url = f"{api.base_url}/api/1/webhooks"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    data = {
        "url": webhook_url,
        "eventType": "order_created",  # или другой тип события
        "organizationId": IIKO_ORG_ID
    }
    
    response = requests.post(setup_url, json=data, headers=headers)
    return response.json()