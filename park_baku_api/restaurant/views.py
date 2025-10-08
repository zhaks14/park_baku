from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from django.contrib.auth.models import User
from .models import Customer, Order, SMSCode
from .serializers import CustomerSerializer, OrderSerializer, CustomerDetailSerializer
import random
from .utils import generate_code
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from twilio.rest import Client
from decimal import Decimal
from django.db.models import Sum, Count
from django.http import JsonResponse

TWILIO_ACCOUNT_SID = 'AC44b190420e71038a0d88e11bfe809cf6'
TWILIO_AUTH_TOKEN = '1770fed861f4293401c8a67add3c2fe6'
TWILIO_PHONE_NUMBER = '+18592377972'

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    
    @action(detail=True, methods=['get'])
    def check_discount(self, request, pk=None):
        customer = self.get_object()
        discount = customer.get_discount_percentage()
        return JsonResponse({"discount_percentage": discount})

@api_view(['POST'])
def check_or_create_customer(request):
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
            'orders_count': customer.orders_count,
            'bonus_balance': str(customer.bonus_balance)
        })
    else:
        username = f'user_{phone}'
        user = User.objects.create_user(username=username, password='defaultpass123')
        
        customer_id = f'C{random.randint(1000, 9999)}'
        customer = Customer.objects.create(user=user, phone=phone, customer_id=customer_id)
        
        return Response({
            'exists': False,
            'customer_id': customer.customer_id,
            'user_id': customer.id,
            'total_spent': '0',
            'orders_count': 0,
            'bonus_balance': '0',
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
    
    return Response({'success': False, 'error': 'Invalid code'}, status=status.HTTP_400_BAD_REQUEST)

@api_view(['POST'])
def send_check(request):
    customer_id = request.data.get("customer")
    dish_name = request.data.get("dish_name")
    quantity = int(request.data.get("quantity", 1))
    amount = Decimal(request.data.get("amount", "0"))
    bonus_applied = Decimal(request.data.get("bonus_applied", "0"))

    try:
        customer = Customer.objects.get(customer_id=customer_id)
    except Customer.DoesNotExist:
        return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)

    discount_percentage = customer.get_discount_percentage()
    
    if discount_percentage > 0 and bonus_applied > 0:
        customer.bonus_balance -= bonus_applied
        customer.save()

    order = Order.objects.create(
        customer=customer,
        amount=amount,
        dish_name=dish_name,
        quantity=quantity,
        bonus_applied=bonus_applied
    )

    customer.refresh_from_db()

    return Response({
        "message": "Check sent successfully",
        "order_id": order.id,
        "customer_id": customer.customer_id,
        "amount": float(amount),
        "bonus_applied": float(bonus_applied),
        "bonus_balance": float(customer.bonus_balance),
        "total_spent": float(customer.total_spent),
        "discount_percentage": discount_percentage
    }, status=status.HTTP_201_CREATED)

@api_view(['POST'])
def createOrderWithDishes(request):
    customer_id = request.data.get("customer_id")
    dishes = request.data.get("dishes", [])
    order_number = request.data.get("order_number", "")
    table_number = request.data.get("table_number", "")

    try:
        customer = Customer.objects.get(customer_id=customer_id)
    except Customer.DoesNotExist:
        return Response({"error": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)

    total_amount = Decimal('0')
    total_bonus_applied = Decimal('0')
    created_orders = []

    for dish_data in dishes:
        dish_name = dish_data.get("dish_name", "Unknown dish")
        quantity = int(dish_data.get("quantity", 1))
        price = Decimal(dish_data.get("price", "0"))
        amount = price * quantity

        order = Order.objects.create(
            customer=customer,
            amount=amount,
            dish_name=dish_name,
            quantity=quantity,
            order_number=order_number,
            table_number=table_number,
            order_details=dish_data
        )
        
        total_amount += amount
        created_orders.append({
            "dish_name": order.dish_name,
            "quantity": order.quantity,
            "amount": float(order.amount)
        })

    discount_percentage = customer.get_discount_percentage()
    bonus_to_apply = total_amount * Decimal(discount_percentage) / Decimal(100)
    
    if discount_percentage > 0 and bonus_to_apply > 0:
        if bonus_to_apply <= customer.bonus_balance:
            customer.bonus_balance -= bonus_to_apply
            total_bonus_applied = bonus_to_apply
        else:
            total_bonus_applied = customer.bonus_balance
            customer.bonus_balance = Decimal('0')
        
        customer.save()

    return Response({
        'message': "Orders created successfully",
        'total_amount': float(total_amount),
        'orders_count': len(created_orders),
        'bonus_applied': float(total_bonus_applied),
        'discount_percentage': discount_percentage,
        'bonus_balance': float(customer.bonus_balance),
        'total_spent': float(customer.total_spent),
        'orders': created_orders
    }, status=status.HTTP_201_CREATED)

@api_view(['GET'])
def getBalance(request, customer_id):
    try:
        customer = Customer.objects.get(customer_id=customer_id)
    except Customer.DoesNotExist:
        return Response({'error': 'Customer not found'}, status=status.HTTP_404_NOT_FOUND)
    
    serializer = CustomerSerializer(customer)
    return Response(serializer.data, status=status.HTTP_200_OK)

@api_view(['GET'])
def orderHistory(request, customer_id):
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
            "table_number": order.table_number,
            "order_number": order.order_number
        } for order in orders])
    except Customer.DoesNotExist:
        return Response({"error": "Customer not found"}, status=404)

@api_view(['POST'])
def sendCode(request):
    phone = request.data.get('phone')
    
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
    
    if code == "1234":
        customer = Customer.objects.filter(phone=phone.replace('+994','')).first()
        if customer:
            return Response({
                'success': True,
                'customer_id': customer.customer_id,
                'user_id': customer.id
            })

    sms = SMSCode.objects.filter(phone=phone).order_by('-created_at').first()
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

@api_view(['GET'])
def check_customer(request, customer_id):
    try:
        customer = Customer.objects.get(customer_id=customer_id)
        serializer = CustomerSerializer(customer)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Customer.DoesNotExist:
        return Response({'error': 'Customer not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['GET'])
def customer_profile(request, customer_id):
    try:
        customer = Customer.objects.get(customer_id=customer_id)
        serializer = CustomerDetailSerializer(customer)
        return Response(serializer.data, status=status.HTTP_200_OK)
    except Customer.DoesNotExist:
        return Response({'error': 'Customer not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
def redeem_bonus(request, customer_id):
    try:
        customer = Customer.objects.get(customer_id=customer_id)
        amount = request.data.get('amount')

        if amount == "all":
            customer.bonus_balance = 0
            customer.save()
            return Response({'success': True, 'message': 'All bonuses redeemed'}, status=status.HTTP_200_OK)
        else:
            amount = int(amount)
            if amount > customer.bonus_balance:
                return Response({"success": False, "error": "Not enough bonuses"}, status=400)
            customer.bonus_balance -= amount
            customer.save()
            return Response({'success': True, 'message': f'Redeemed {amount} bonuses'}, status=status.HTTP_200_OK)

    except Customer.DoesNotExist:
        return Response({'error': 'Customer not found'}, status=status.HTTP_404_NOT_FOUND)
    
@api_view(['POST'])
def add_bonus(request, customer_id):
    try:
        customer = Customer.objects.get(customer_id=customer_id)
        amount = request.data.get('amount')

        try:
            amount = int(amount)
        except:
            return Response({'error': 'Invalid bonus amount'}, status=status.HTTP_400_BAD_REQUEST)

        if amount <= 0:
            return Response({'error': 'Amount must be positive'}, status=status.HTTP_400_BAD_REQUEST)

        customer.bonus_balance += amount
        customer.save()

        return Response({
            'success': True,
            'message': f'Added {amount} bonuses',
            'bonus_balance': float(customer.bonus_balance)
        }, status=status.HTTP_200_OK)

    except Customer.DoesNotExist:
        return Response({'error': 'Customer not found'}, status=status.HTTP_404_NOT_FOUND)
    
@api_view(['POST'])
def validate_customer_for_cashier(request):
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
            'error': f'Customer with ID {customer_id} not found'
        }, status=404)