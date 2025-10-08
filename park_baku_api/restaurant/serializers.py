from rest_framework import serializers
from .models import Customer, Order

class CustomerSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = Customer
        fields = ['id', 'customer_id', 'username', 'phone', 'total_spent', 'orders_count', 'bonus_balance']

class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ["id", "customer", "dish_name", "quantity", "amount", "bonus_applied", "created_at", "order_details", "table_number", "order_number"]

class CustomerDetailSerializer(serializers.ModelSerializer):
    orders = OrderSerializer(many=True, read_only=True)

    class Meta:
        model = Customer
        fields = ['customer_id', 'phone', 'bonus_balance', 'total_spent', 'orders']