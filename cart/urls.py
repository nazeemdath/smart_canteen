from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
from . import views

app_name = 'cart'

urlpatterns = [
    path("cart", views.cart, name="cart"),
    path('cart/cartadd/<int:product_id>/', views.cartadd, name="cartadd"),
    path('cart/delete/<int:item_id>/', views.delete, name='delete'),  # Ensure this matches the template
    path('cart/update/<int:item_id>/', views.update, name="update"),
    path('cart/apply_coupon/', views.apply_coupon, name="apply_coupon"),
]
