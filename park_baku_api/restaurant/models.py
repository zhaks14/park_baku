from django.db import models
from django.contrib.auth.models import User

class Customer(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    customer_id = models.CharField(max_length=10, unique=True)
    phone = models.CharField(max_length=20, blank=True)
    total_spent = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    orders_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    bonus_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    def __str__(self):
        return f"{self.customer_id} - {self.user.username}"


class Order(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='orders')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def save(self, *args, **kwargs):
        # Automatically update customer stats when order is saved
        super().save(*args, **kwargs)
        
        # Update customer's total spent and order count
        self.customer.total_spent += self.amount
        self.customer.orders_count += 1
        self.customer.bonus_balance += self.calculate_bonus()
        self.customer.save()

    def calculate_bonus(self):
        spent = self.customer.total_spent
        if spent >= 3_000_000:
            percent = 15
        elif spent >= 1_000_000:
            percent = 10
        elif spent >= 500_000:
            percent = 5
        else:
            percent = 0
        return self.amount * percent / 100
    
    def __str__(self):
        return f"{self.customer.customer_id} - ${self.amount} - {self.created_at.strftime('%Y-%m-%d')}" 
    

