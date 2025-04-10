from django.db import models
from main.models import Product  
from authentication.models import CustomUser
from django.contrib.auth import get_user_model
from checkout.models import Order
from decimal import Decimal

User = get_user_model() 

class Coupon(models.Model):
    code = models.CharField(max_length=20, unique=True)
    discount_percentage = models.PositiveIntegerField()
    valid_from = models.DateTimeField(blank=True,null=True)
    valid_to = models.DateTimeField(blank=True,null=True)
    valid_for = models.CharField(
        max_length=10,
        choices=[('student', 'Student'), ('faculty', 'Faculty')],
        default='student'
    )
    active = models.BooleanField(default=True)
    products = models.ManyToManyField(Product, blank=True, help_text="Select products for this coupon")
    

    def __str__(self):
        return f"{self.code} - {self.discount_percentage}% for {self.valid_for}"

class CartItem(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, null=True, blank=True)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True, blank=True, related_name="cart_items")
    product_id = models.ForeignKey(Product, on_delete=models.CASCADE)  
    name = models.CharField(max_length=255)
    price = models.FloatField()
    quantity = models.IntegerField(default=1)
    image_url = models.URLField(blank=True, null=True)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, editable=False, blank=True, null=True)
    discounted_price = models.DecimalField(max_digits=10, decimal_places=2, editable=False, blank=True, null=True)

    def save(self, *args, **kwargs):
        self.subtotal = Decimal(self.price) * Decimal(self.quantity)  # ✅ Ensure Decimal

        if self.coupon:
            discount_percentage = Decimal(self.coupon.discount_percentage) / 100  # ✅ Convert to Decimal
            discount_amount = self.subtotal * discount_percentage  # ✅ Now both are Decimal
            self.discounted_price = max(self.subtotal - discount_amount, Decimal(0))
        else:
            self.discounted_price = self.subtotal

        super().save(*args, **kwargs)

    @property
    def total_price(self):
        return self.price * self.quantity

    def __str__(self):
        return f"{self.quantity} x {self.name}"
