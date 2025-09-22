from django.contrib import admin

# Register your models here.
from .models import Customer, Order

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['customer_id', 'user', 'phone', 'total_spent', 'orders_count']
    search_fields = ['customer_id', 'user__username', 'phone']
    readonly_fields = ['total_spent', 'orders_count']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['customer', 'amount', 'created_at']
    list_filter = ['created_at']
    search_fields = ['customer__customer_id', 'customer__user__username']
    date_hierarchy = 'created_at'