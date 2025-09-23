from rest_framework import viewsets
from rest_framework.decorators import action, api_view  # ДОБАВЬ api_view
from rest_framework.response import Response
from rest_framework import status  # ДОБАВЬ status
from django.contrib.auth.models import User  # ДОБАВЬ User
from .models import Customer, Order
from .serializers import CustomerSerializer
import random  # ДОБАВЬ random


class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    
    @action(detail=True, methods=['get'])
    def check_discount(self, request, pk=None):
        customer = self.get_object()
        # Логика скидок: 10% после 100 манат
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


# ДОБАВЬ ВСЁ ЧТО НИЖЕ:

@api_view(['POST'])
def check_or_create_customer(request):
    phone = request.data.get('phone', '')
    
    if not phone:
        return Response({'error': 'Phone number required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Убираем +994 если есть
    phone = phone.replace('+994', '').strip()
    
    # Ищем существующего клиента
    customer = Customer.objects.filter(phone=phone).first()
    
    if customer:
        # Клиент существует
        return Response({
            'exists': True,
            'customer_id': customer.customer_id,
            'user_id': customer.id,
            'total_spent': str(customer.total_spent),
            'orders_count': customer.orders_count
        })
    else:
        # Создаём нового клиента
        username = f'user_{phone}'
        user = User.objects.create_user(
            username=username,
            password='defaultpass123'  # Временный пароль
        )
        
        customer_id = f'C{random.randint(1000, 9999)}'
        customer = Customer.objects.create(
            user=user,
            customer_id=customer_id,
            phone=phone,
            total_spent=0,
            orders_count=0
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
    
    # Для теста принимаем код 1234
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