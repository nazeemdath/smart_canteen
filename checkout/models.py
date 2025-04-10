from django.db import models
from authentication.models import CustomUser
from django.core.mail import send_mail
from django.conf import settings

class Order(models.Model):
    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Paid", "Paid"),
        ("Processing", "Processing"),
        ("Delivered", "Delivered"),
        ("ready", "Ready for Pickup"),
        ("Cancelled", "Cancelled"),
    ]

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    order_total = models.DecimalField(max_digits=10, decimal_places=2)
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True)
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.id} - {self.user.username} - {self.status}"

    def save(self, *args, **kwargs):
        if self.status == "Processing":
            send_mail(
                "Your Order is Being Prepared",
                "Your order is now being prepared. You'll be notified when it's ready for pickup.",
                settings.EMAIL_HOST_USER,
                [self.user.email],
                fail_silently=True,
            )

        elif self.status == "Delivered":
            send_mail(
                "Order Ready for Pickup!",
                "Your order is ready for pickup at the counter!",
                settings.EMAIL_HOST_USER,
                [self.user.email],
                fail_silently=True,
            )

        super().save(*args, **kwargs)  

class Feedback(models.Model):
    order = models.OneToOneField(
        'Order', on_delete=models.CASCADE, null=True, blank=True
    )  # ✅ Allow feedback without an order
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(
        choices=[(i, i) for i in range(1, 6)]
    )  # ✅ Using PositiveSmallIntegerField (saves space)
    comment = models.TextField(blank=True, null=True)  # ✅ Comment is optional
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Feedback"
        verbose_name_plural = "Feedbacks"  # ✅ Corrects the admin display

    def __str__(self):
        return f"Feedback from {self.user.username} for Order {self.order.id if self.order else 'N/A'}"

