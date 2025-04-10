from django.contrib import admin
from .models import Product
from .models import MealSubscriptionPlan, UserSubscription,SubscriptionMeal,ClaimedMeal


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'stock')  # Display stock in list view
    list_editable = ('stock',)  # Allows stock editing from the list view
    search_fields = ('name',)  # Enables search by name
    list_filter = ('created_at',)  # Adds a filter for creation date


admin.site.register(MealSubscriptionPlan)
admin.site.register(UserSubscription)
admin.site.register(SubscriptionMeal)
admin.site.register(ClaimedMeal)

