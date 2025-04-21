from django.contrib import admin
from .models import Order
from .models import Feedback
from django.db.models import Sum
from .utils import send_push_notification

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "order_total", "status", "created_at", "token_number")
    list_filter = ("status", "created_at")
    readonly_fields = ("total_sales",)

    def total_sales(self, obj=None):
        total = Order.objects.filter(status="paid").aggregate(Sum("order_total"))["order_total__sum"]
        return f"₹{total if total else 0}"
    total_sales.short_description = "Total Sales"

    def save_model(self, request, obj, form, change):
        if change:
            previous = Order.objects.get(pk=obj.pk)
            super().save_model(request, obj, form, change)
            if previous.status != obj.status and obj.status == "Ready for Pickup":
                send_push_notification(
                    user=obj.user,
                    title="Order Ready!",
                    body=f"Hi {obj.user.username}, your order #{obj.id} is ready for pickup!"
                )
        else:
            super().save_model(request, obj, form, change)

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("order", "user", "rating", "created_at")  # Columns to display
    search_fields = ("user__username", "order__id")  # Searchable fields
    list_filter = ("rating", "created_at")  # Filters
