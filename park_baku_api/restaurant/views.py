from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Customer, Order
from .serializers import CustomerSerializer

class CustomerViewSet(viewsets.ModelViewSet):
    queryset = Customer.objects.all()
    serializer_class = CustomerSerializer
    
    @action(detail=True, methods=['get'])
    def check_discount(self, request, pk=None):
        customer = self.get_object()
        # Логика скидок: 10% после 100 тенге
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