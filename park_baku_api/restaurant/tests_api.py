import requests
from django.conf import settings

API_KEY = settings.API_KEY
BASE_URL = "http://127.0.0.1:8000/api"

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

resp = requests.post(f"{BASE_URL}/check-customer/", headers=headers, json={
    "phone": "+77051234567"
})
print("Создание клиента ", resp.json())
resp = requests.post(f"{BASE_URL}/orders/", headers=headers, json={
    "customer_id": "C1234",
    "amount": 600000
})
print("Создание заказа ", resp.json())

resp = requests.get(f"{BASE_URL}/customers/1/", headers=headers)
print("Данные клиента ", resp.json())
