from django.db import models
from checkout.models import Feedback  # Import inside method to avoid circular import
from django.apps import apps
from django.conf import settings
from datetime import timedelta
from django.utils.timezone import now
from datetime import timedelta, date
from authentication.models import CustomUser

class Product(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)  # New stock field
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    calories = models.PositiveIntegerField(default=0)  # 👈 New field
    


    # def average_rating(self):
        

    #     # Get all cart items related to this product
    #     CartItem = apps.get_model('cart', 'CartItem')  # ✅ Lazy Import
    #     cart_items = CartItem.objects.filter(product_id=self)

    #     # Get all feedback related to orders that include these cart items
    #     feedbacks = Feedback.objects.filter(order__cartitem__in=cart_items)  # ✅ Fixed Query

    #     if feedbacks.exists():
    #         return round(feedbacks.aggregate(models.Avg("rating"))["rating__avg"], 1)
    #     return 0  # Default rating if no feedback is present

    def __str__(self):
        return self.name


class MealSubscriptionPlan(models.Model):
    PLAN_CHOICES = [
        ('weekly', 'Weekly Plan'),
        ('monthly', 'Monthly Plan'),
        ('quarterly', 'Quarterly Plan'),
    ]

    name = models.CharField(max_length=20, choices=PLAN_CHOICES, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_days = models.IntegerField()  # e.g., 7 for weekly, 30 for monthly
    meals_per_day = models.IntegerField(default=2)  # 2 meals per day default
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.get_name_display()} - ₹{self.price}"

class UserSubscription(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('failed', 'Failed'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    plan = models.ForeignKey(MealSubscriptionPlan, on_delete=models.CASCADE)
    start_date = models.DateField(auto_now_add=True)
    end_date = models.DateField()
    payment_status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    razorpay_order_id = models.CharField(max_length=255, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=255, blank=True, null=True)
    razorpay_signature = models.CharField(max_length=255, blank=True, null=True)
    remaining_meals = models.IntegerField(default=0)  # Track remaining meals
    active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        """ Auto-calculate end date and meal balance when a subscription is created """
        if not self.id:  # Only on first creation
            self.end_date = date.today() + timedelta(days=self.plan.duration_days)
            self.remaining_meals = self.plan.meals_per_day * self.plan.duration_days  # Calculate meals

        super().save(*args, **kwargs)

    def __str__(self):                                                                              
        return f"{self.user.username} - {self.plan.name} ({self.remaining_meals} meals left)"
    
    def is_valid(self):
        """Check if the subscription is active."""
        return self.active and self.start_date <= date.today() <= self.end_date
    
class SubscriptionMeal(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    date_available = models.DateField()
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.product.name} - {self.date_available}"
    
class ClaimedMeal(models.Model):
    user_subscription = models.ForeignKey(UserSubscription, on_delete=models.CASCADE)
    meal = models.ForeignKey(SubscriptionMeal, on_delete=models.CASCADE)
    claimed_on = models.DateTimeField(auto_now_add=True)


class WebPushSubscription(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    endpoint = models.TextField()
    p256dh = models.CharField(max_length=255)
    auth = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Subscription for {self.user.username}"
    


# models.py
class Banner(models.Model):
    title = models.CharField(max_length=200)
    image = models.ImageField(upload_to="banners/")
    link = models.URLField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title



