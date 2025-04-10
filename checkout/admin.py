from django.contrib import admin
from .models import Order
from .models import Feedback


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "order_total", "status", "created_at")
    list_filter = ("status",)



@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ("order", "user", "rating", "created_at")  # Columns to display
    search_fields = ("user__username", "order__id")  # Searchable fields
    list_filter = ("rating", "created_at")  # Filters
