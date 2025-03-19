from django.db import models
from main.models import Product  # Assuming you have a menu app
from authentication.models import CustomUser
from django.contrib.auth import get_user_model

User = get_user_model() 

class Coupon(models.Model):
    code = models.CharField(max_length=20, unique=True)
    discount_percentage = models.PositiveIntegerField()
    valid_for = models.CharField(
        max_length=10,
        choices=[('student', 'Student'), ('faculty', 'Faculty')],
        default='student'
    )
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.code} - {self.discount_percentage}% for {self.valid_for}"

class CartItem(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    product_id = models.ForeignKey(Product, on_delete=models.CASCADE)  # ✅ Link to Product model
    name = models.CharField(max_length=255)
    price = models.FloatField()
    quantity = models.IntegerField(default=1)
    image_url = models.URLField(blank=True, null=True)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)  # ✅ Now it works!
    @property
    def total_price(self):
        return self.price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.name}"
