from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal

class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    customer_id = models.CharField(max_length=10, unique=True)
    phone = models.CharField(max_length=20, blank=True)
    total_spent = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    orders_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    bonus_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    iiko_customer_id = models.CharField(max_length=255, blank=True, null=True)
    is_synced_with_iiko = models.BooleanField(default=False)

    def get_discount_percentage(self):
        if self.total_spent >= 30000:
            return 15
        elif self.total_spent >= 10000:
            return 10
        elif self.total_spent >= 5000:
            return 5
        return 0
    def __str__(self):
        return f'{self.customer_id} - {self.user.username}'


class Order(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='orders')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    bonus_applied = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    dish_name = models.CharField(max_length=255,default="Unknown dish")
    quantity = models.PositiveIntegerField(default=1)
    external_id = models.CharField(max_length=255, blank=True, null=True)  # ID заказа в iiko
    iiko_organization_id = models.CharField(max_length=255, blank=True, null=True)
    is_synced = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        discount = self.customer.get_discount_percentage()
        if discount > 0:
            self.amount = self.amount * (Decimal(100) - Decimal(discount)) / Decimal(100)

        super().save(*args, **kwargs)

        # обновление статистики клиента
        self.customer.total_spent += self.amount
        self.customer.orders_count = self.customer.orders.count()
        self.customer.bonus_balance += self.calculate_bonus()
        self.customer.save()

    def calculate_bonus(self):
        discount = self.customer.get_discount_percentage()
        return (self.amount * Decimal(discount) / Decimal(100)).quantize(Decimal("0.01"))
    
    def __str__(self):
        return f"{self.customer.customer_id} - ${self.amount} - {self.created_at.strftime('%Y-%m-%d')}" 
    

class SMSCode(models.Model):
    phone = models.CharField(max_length=20)
    code = models.CharField(max_length=4)
    created_at = models.DateTimeField(auto_now_add=True)