from rest_framework import viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from .models import Customer,Order,SMSCode
from .serializers import CustomerSerializer,OrderSerializer
import random
from .utils import generate_code
from django.utils import timezone
from datetime import timedelta
from random import randint
from django.conf import settings
from twilio.rest import Client
from decimal import Decimal

TWILIO_ACCOUNT_SID = 'AC44b190420e71038a0d88e11bfe809cf6'
TWILIO_AUTH_TOKEN = '1770fed861f4293401c8a67add3c2fe6'
TWILIO_PHONE_NUMBER = '+18592377972'

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    
    @action(detail=True, methods=['get'])
    def check_discount(self, request, pk=None):
        # ну это короче мини-калькулятор скидки
        customer = self.get_object()
        discount = 0
        if customer.total_spent >= 100:
            discount = 10
        elif customer.total_spent >= 50:
            discount = 5
            
        return Response({
            'customer_id': customer.customer_id,
            'total_spent': float(customer.total_spent),
            'discount_percentage': discount
        })
    
    def orders(self,request,pk=None):
        customer = self.get_object()
        orders = customer.orders.all()
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)

@api_view(['POST'])
def check_or_create_customer(request):
    # тут мы делаем типо если чел с таким номером есть то вернём инфу, если нет создаём нового
    phone = request.data.get('phone','')
    
    if not phone:
        return Response({'error': 'Phone number required'}, status=status.HTTP_400_BAD_REQUEST)
    
    phone = phone.replace('+994', '').strip()
    customer = Customer.objects.filter(phone=phone).first()
    
    if customer:
        return Response({
            'exists': True,
            'customer_id': customer.customer_id,
            'user_id': customer.id,
            'total_spent': str(customer.total_spent),
            'orders_count': customer.orders_count
        })
    else:
        username = f'user_{phone}'
        user = User.objects.create_user(
            username=username,
            password='defaultpass123'
        )
        
        customer_id = f'C{random.randint(1000, 9999)}'
        customer = Customer.objects.create(
            user=user,
            phone=phone,
            customer_id=customer_id
        )
        
        return Response({
            'exists': False,
            'customer_id': customer.customer_id,
            'user_id': customer.id,
            'total_spent': '0',
            'orders_count': 0,
            'message': 'New customer created'
        })


@api_view(['POST'])
def verify_code(request):
    phone = request.data.get('phone', '')
    code = request.data.get('code', '')
    
    if code == '1234':
        phone = phone.replace('+994', '').strip()
        customer = Customer.objects.filter(phone=phone).first()
        
        if customer:
            return Response({
                'success': True,
                'customer_id': customer.customer_id,
                'user_id': customer.id
            })
    
    return Response({'success': False,'error' : 'Invalid code'},status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def createOrder(request):
    """
    Принимает customer_id и сумму заказа, создаёт заказ и начисляет бонусы.
    """
    customer_id = request.data.get("customer_id")
    amount = Decimal(request.data.get("amount", "0"))

    try:
        customer = Customer.objects.get(customer_id=customer_id)
    except Customer.DoesNotExist:
        return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)
    
    order = Order.objects.create(customer=customer, amount=amount)
    bonus_percent = 0

    if 500000 <= amount < 1000000:
        bonus_percent = 5
    elif 1000000 <= amount < 3000000:
        bonus_percent = 10
    elif amount >= 3000000:
        bonus_percent = 15

    bonus_added = amount * Decimal(bonus_percent) / Decimal(100)
    customer.bonus_balance += bonus_added
    customer.total_spent += amount
    customer.orders_count += 1
    customer.save()

    return Response({
        'message':"Order created",
        'order_id': order.id,
        'bonus_added': bonus_added,
        'total_spent': customer.total_spent,
        'orders_count': customer.orders_count,
        'bonus_balance': customer.bonus_balance,
    },status=status.HTTP_201_CREATED)
@api_view(['GET'])
def getBalance(request, customer_id):
    # этот эндпоинт по сути чисто чтоб чекнуть баланс чела, сколько потратил и бонусов накопил
    """
    Возвращает баланс клиента: общие траты, бонусы, количество заказов.
    """
    try:
        customer = Customer.objects.get(customer_id=customer_id)
    except Customer.DoesNotExist:
        return Response({'error':'Customer not found'}, status=status.HTTP_404_NOT_FOUND)
    serializer = CustomerSerializer(customer)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
def orderHistory(request,customer_id):
    try:
        customer = Customer.objects.get(customer_id=customer_id)
        orders = customer.orders.all().order_by("-created_at")
        return Response([{
            "id": order.id,
            "amount": order.amount,
            "bonus_applied": order.bonus_applied,
            "created_at": order.created_at
        } for order in orders])
    except Customer.DoesNotExist:
        return Response({"error": "Customer not found"}, status=404)

@api_view(['POST'])
def sendCode(request):
    phone = request.data.get('phone')
    print("PHONE:", phone)
    print("SID:", TWILIO_ACCOUNT_SID)
    if not phone.startswith('+'):
        phone = f'+{phone}'
    if not phone:
        return Response({'error': 'Phone is required'}, status=400)

    code = generate_code()
    SMSCode.objects.create(phone=phone, code=code)

    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    try:
        message = client.messages.create(
            body=f"Ваш код подтверждения: {code}",
            from_=TWILIO_PHONE_NUMBER,
            to=phone
        )
    except Exception as e:
        return Response({'success': False, 'message': f"Ошибка отправки SMS: {e}"}, status=500)

    return Response({'success': True, 'message': 'Code sent'})

@api_view(['POST'])
def verifyCode(request):
    phone = request.data.get('phone')
    code = request.data.get('code')
    sms = SMSCode.objects.filter(phone=phone).order_by('-created_at').first()
    if code == "1234": # dla testa
        customer = Customer.objects.filter(phone=phone.replace('+994','')).first()
        if customer:
            return Response({
                'success': True,
                'customer_id': customer.customer_id,
                'user_id': customer.id
            })

    if not sms:
        return Response({'success': False, 'message': 'Code not found'}, status=400)
    if timezone.now() - sms.created_at > timedelta(minutes=5):
        return Response({'success': False, 'message': 'Code expired'}, status=400)
    if sms.code != code:
        return Response({'success': False, 'message': 'Invalid code'}, status=400)
    
    customer = Customer.objects.filter(phone=phone.replace('+994', '')).first()

    if customer:
        return Response({
            'success': True,
            'customer_id': customer.customer_id,
            'user_id': customer.id
        })

    return Response({'success': False, 'message': 'Customer not found'}, status=400)