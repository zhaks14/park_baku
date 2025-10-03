from itertools import count
from rest_framework import viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from .models import Customer,Order,SMSCode
from .serializers import CustomerSerializer,OrderSerializer,CustomerDetailSerializer
import random
from .utils import generate_code
from django.utils import timezone
from datetime import timedelta
from random import randint
from django.conf import settings
from twilio.rest import Client
from decimal import Decimal
from django.db.models import Sum,Count
from django.http import JsonResponse
from .iiko_service import get_order_by_id

TWILIO_ACCOUNT_SID = 'AC44b190420e71038a0d88e11bfe809cf6'
TWILIO_AUTH_TOKEN = '1770fed861f4293401c8a67add3c2fe6'
TWILIO_PHONE_NUMBER = '+18592377972'

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    
    @action(detail=True, methods=['get'])
    def check_discount(request, customer_id):
        customer = Customer.objects.get(id=customer_id)
        discount = customer.get_discount_percentage()
        return JsonResponse({"discount_percentage": discount})
    
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

@api_view(['POST','GET'])
def createOrder(request):
    if request.method == 'POST':
        customer_id = request.data.get("customer_id")
        amount = Decimal(request.data.get("amount", "0"))
        dish_name = request.data.get("dish_name", "Unknown dish")
        quantity = int(request.data.get("quantity", 1))

        try:
            customer = Customer.objects.get(customer_id=customer_id)
        except Customer.DoesNotExist:
            return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)

        order = Order.objects.create(
            customer=customer,
            amount=amount,
            dish_name=dish_name,
            quantity=quantity
        )

        return Response({
            "message": "Order created",
            "order_id": order.id,
            "dish_name": order.dish_name,
            "quantity": order.quantity,
            "discount_applied": float(order.bonus_applied),
            "bonus_earned": float(order.calculate_bonus()),
            "bonus_balance": float(customer.bonus_balance),
            "total_spent": float(customer.total_spent),
            "orders_count": customer.orders_count,
        }, status=status.HTTP_201_CREATED)

    elif request.method == 'GET':
        # получение всех существующих заказов
        orders = Order.objects.all().order_by("-created_at")
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
    

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
            "created_at": order.created_at,
            "dish_name": order.dish_name,
            "quantity": order.quantity,
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
        return Response(
            {'success': False, 'message': f"Twilio error: {str(e)}"},
            status=status.HTTP_400_BAD_REQUEST
        )

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

@api_view(['GET'])
def popularDishes(request):
    """
    Возвращает список самых популярных блюд среди всех заказов
    """
    popular_dishes = (
        Order.objects
        .values('dish_name') 
        .annotate(
            total_orders=Count('id'),
            total_quantity=Sum('quantity'),
            total_revenue=Sum('amount')
        )
        .order_by('-total_quantity')[:10]
    )

    result = []
    for rank, dish in enumerate(popular_dishes, start=1):
        result.append({
            "rank": rank,
            "name": dish["dish_name"],
            "total_orders": dish["total_orders"],
            "total_quantity": dish["total_quantity"],
            "total_revenue": float(dish["total_revenue"])
        })

    return Response(result)

@api_view(['POST'])
def createOrderWithDishes(request):
    """
    Создает заказ с несколькими блюдами
    """
    customer_id = request.data.get("customer_id")
    dishes = request.data.get("dishes",[])
    
    try:
        customer = Customer.objects.get(customer_id=customer_id)
    except Customer.DoesNotExist:
        return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)
    
    total_amount = Decimal('0')
    created_orders = []

    for dish_data in dishes:
        dish_name = dish_data.get("dish_name", "Unknown dish")
        quantity = int(dish_data.get("quantity", 1))
        price = Decimal(dish_data.get("price", "0"))
        
        order = Order.objects.create(
            customer=customer,
            amount=price * quantity,
            dish_name=dish_name,
            quantity=quantity
        )
        
        total_amount += order.amount
        created_orders.append({
            "dish_name": order.dish_name,
            "quantity": order.quantity,
            "amount": float(order.amount)
        })
    
    return Response({
        'message': "Orders created successfully",
        'total_amount': float(total_amount),
        'orders_count': len(created_orders),
        'orders': created_orders,
        'bonus_balance': float(customer.bonus_balance),
        'total_spent': float(customer.total_spent)
    }, status=status.HTTP_201_CREATED)

@api_view(['GET'])
def check_customer(request, customer_id):
    try:
        customer = Customer.objects.get(customer_id=customer_id)
        serializer = CustomerSerializer(customer)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Customer.DoesNotExist:
        return Response({'error': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def customer_profile(request, customer_id):
    try:
        customer = Customer.objects.get(customer_id=customer_id)
        serializer = CustomerDetailSerializer(customer)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Customer.DoesNotExist:
        return Response({'error': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
def redeem_bonus(request, customer_id):
    try:
        customer = Customer.objects.get(customer_id=customer_id)
        amount = request.data.get('amount')

        if amount == "all":
            customer.bonus_balance = 0
            customer.save()
            return Response({'success': True, 'message': 'Все бонусы списаны'}, status=status.HTTP_200_OK)
        else:
            amount = int(amount)
            if amount > customer.bonus_balance:
                return Response({"success": False, "error": "Недостаточно бонусов"}, status=400)
            redeemed = amount
            customer.bonus_balance -= amount
        try:
            amount = int(amount)
        except:
            return Response({'error': 'Неверное значение бонусов'}, status=status.HTTP_400_BAD_REQUEST)

        if amount <= 0 or amount > customer.bonus_balance:
            return Response({'error': 'Недостаточно бонусов'}, status=status.HTTP_400_BAD_REQUEST)

        customer.bonus_balance -= amount
        customer.save()
        return Response({'success': True, 'message': f'Списано {amount} бонусов'}, status=status.HTTP_200_OK)

    except Customer.DoesNotExist:
        return Response({'error': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)
    
@api_view(['POST'])
def add_bonus(request, customer_id):
    """
    Пополнение бонусного баланса клиента
    """
    try:
        customer = Customer.objects.get(customer_id=customer_id)
        amount = request.data.get('amount')

        try:
            amount = int(amount)
        except:
            return Response({'error': 'Неверное значение бонусов'}, status=status.HTTP_400_BAD_REQUEST)

        if amount <= 0:
            return Response({'error': 'Сумма должна быть положительной'}, status=status.HTTP_400_BAD_REQUEST)

        customer.bonus_balance += amount
        customer.save()

        return Response({
            'success': True,
            'message': f'Пополнено {amount} бонусов',
            'bonus_balance': float(customer.bonus_balance)
        }, status=status.HTTP_200_OK)

    except Customer.DoesNotExist:
        return Response({'error': 'Пользователь не найден'}, status=status.HTTP_404_NOT_FOUND)
    
@api_view(['POST'])
def iiko_order_webhook(request):
    """
    Принимает заказ из iiko WebKassa и сохраняет его в систему бонусов.
    Ожидает:
    {
      "customer_id": "C1234",
      "dishes": [
        {"dish_name": "Пицца Маргарита", "quantity": 2, "price": "1500"},
        {"dish_name": "Кола", "quantity": 1, "price": "500"}
      ]
    }
    """
    customer_id = request.data.get("customer_id")
    dishes = request.data.get("dishes", [])

    try:
        customer = Customer.objects.get(customer_id=customer_id)
    except Customer.DoesNotExist:
        return Response({"error": "Customer not found"}, status=404)

    total_amount = Decimal("0")
    created_orders = []

    for dish in dishes:

        name = dish.get("dish_name", "Unknown dish")
        qty = int(dish.get("quantity", 1))
        price = Decimal(dish.get("price", "0"))

        order = Order.objects.create(
            customer=customer,
            dish_name=name,
            quantity=qty,
            amount=price * qty
        )
        created_orders.append({
            "dish_name": name,
            "quantity": qty,
            "amount": float(order.amount)
        })
        total_amount += order.amount

    return Response({
        "success": True,
        "customer_id": customer.customer_id,
        "orders": created_orders,
        "total_amount": float(total_amount),
        "bonus_balance": float(customer.bonus_balance),
        "total_spent": float(customer.total_spent)
    })

@api_view(["POST"])
def import_order(request):
    """
    Привязать заказ из iiko к клиенту
    request: { "customer_id": 1, "organizationId": "ORG_ID", "orderId": "UUID" }
    """
    customer_id = request.data.get("customer_id")
    org_id = request.data.get("organizationId")
    order_id = request.data.get("orderId")

    customer = Customer.objects.get(id=customer_id)
    order_data = get_order_by_id(org_id, order_id)

    iiko_order = order_data["orders"][0]
    dish_names = [item["product"]["name"] for item in iiko_order["items"]]

    order = Order.objects.create(
        customer=customer,
        external_id=order_id,
        items=", ".join(dish_names),
        total_price=iiko_order["sum"],
        created_at=iiko_order["createdAt"],
    )

    return Response(OrderSerializer(order).data)

@api_view(['POST'])
def validate_customer_for_cashier(request):
    """
    Endpoint для кассиров - проверяет валидность customer_id
    и возвращает информацию о скидке
    """
    customer_id = request.data.get('customer_id', '').upper().strip()
    
    if not customer_id:
        return Response({'error': 'Customer ID required'}, status=400)
    
    try:
        customer = Customer.objects.get(customer_id=customer_id)
        
        return Response({
            'valid': True,
            'customer_id': customer.customer_id,
            'customer_name': customer.user.username,
            'phone': customer.phone,
            'discount_percentage': customer.get_discount_percentage(),
            'total_spent': float(customer.total_spent),
            'orders_count': customer.orders_count,
            'bonus_balance': float(customer.bonus_balance)
        })
        
    except Customer.DoesNotExist:
        return Response({
            'valid': False,
            'error': f'Клиент с ID {customer_id} не найден'
        }, status=404)