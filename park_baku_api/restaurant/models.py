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
    
    
    def __str__(self):
        return f'{self.customer_id} - {self.user.username}'


class Order(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='orders')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    bonus_applied = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    class Meta:
        ordering = ['-created_at']
    
    def save(self,*args,**kwargs):
        # прикол,если заказ новый (нет id), то сразу считаем бонусы и апдейтим клиента
        if not self.pk:
            bonus = self.calculate_bonus()
            self.customer.bonus_balance += bonus
            self.customer.total_spent += self.amount
            self.customer.save()
        super().save(*args, **kwargs)

    def calculate_bonus(self):
        # тут короче чем больше тратишь, тем жирнее бонус
        if self.amount >= 3_000_000:
            return Decimal(self.amount) * Decimal('0.15')
        elif self.amount >= 1_000_000:
            return Decimal(self.amount) * Decimal('0.10')
        elif self.amount >= 500_000:
            return Decimal(self.amount) * Decimal('0.05')
        return Decimal('0')
    
    def __str__(self):
        return f"{self.customer.customer_id} - ${self.amount} - {self.created_at.strftime('%Y-%m-%d')}" 
    

class SMSCode(models.Model):
    phone = models.CharField(max_length=20)
    code = models.CharField(max_length=4)
    created_at = models.DateTimeField(auto_now_add=True)